import os, base64, time, logging
import requests, psycopg2
from flask import Flask, render_template

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Config (override via env / ConfigMap)
CONJUR_API_BASE = os.getenv("CONJUR_API_BASE", "https://aruntenant.secretsmgr.cyberark.cloud/api")
CONJUR_ACCOUNT  = os.getenv("CONJUR_ACCOUNT", "conjur")
CONJUR_TOKEN_PATH = os.getenv("CONJUR_TOKEN_PATH", "/run/conjur/access-token")
DB_NAME = os.getenv("DB_NAME", "postgres")  # <- set to your DB name

SECRETS = {
    "db_host": "data/vault/StarAi-Dev/Arun-Staridb/address",
    "db_user": "data/vault/StarAi-Dev/Arun-Staridb/username",
    "db_pass": "data/vault/StarAi-Dev/Arun-Staridb/password",
}

def _auth_header() -> dict:
    # Wait briefly if token not written yet
    deadline = time.time() + 30
    while not os.path.exists(CONJUR_TOKEN_PATH) and time.time() < deadline:
        time.sleep(0.5)
    with open(CONJUR_TOKEN_PATH, "rb") as f:
        token_json = f.read()  # JSON string bytes
    b64 = base64.b64encode(token_json).decode("ascii")
    return {"Authorization": f'Token token="{b64}"'}

def get_secret(secret_id: str) -> str:
    url = f"{CONJUR_API_BASE}/secrets/{CONJUR_ACCOUNT}/variable/{secret_id}"
    # try once, then refresh header on 401 (token rotates fast)
    for attempt in (1, 2):
        r = requests.get(url, headers=_auth_header(), timeout=10)
        if r.status_code == 401 and attempt == 1:
            continue
        r.raise_for_status()
        return r.text.strip()

def query_services_rows(host: str, user: str, password: str):
    # Accept host with or without :port
    host_only, port = (host.split(":", 1) + ["5432"])[:2]
    conn = psycopg2.connect(
        host=host_only, port=int(port),
        dbname=DB_NAME, user=user, password=password
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT service, subscribers, revenue FROM services")
            return cur.fetchall()
    finally:
        conn.close()

@app.route("/")
def index():
    try:
        host = get_secret(SECRETS["db_host"])
        user = get_secret(SECRETS["db_user"])
        password = get_secret(SECRETS["db_pass"])
        app.logger.info(f"Connecting to DB '{DB_NAME}' at {host} as {user}")

        rows = query_services_rows(host, user, password)
        services = [{"name": r[0], "subscribers": r[1], "revenue": r[2]} for r in rows]
        return render_template("index.html", services=services)
    except Exception as e:
        app.logger.exception("Failed handling /")
        return f"Error: {e}", 500

@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
