import os
import requests
import psycopg2
from flask import Flask, render_template

app = Flask(__name__)

CONJUR_TOKEN_PATH = "/run/conjur/access-token"
CONJUR_API_URL = "https://aruntenant.secretsmgr.cyberark.cloud/api"  # ← Replace this

SECRETS = {
    "db_host": "data/vault/StarAi-Dev/Arun-Staridb/address",
    "db_user": "data/vault/StarAi-Dev/Arun-Staridb/username",
    "db_pass": "data/vault/StarAi-Dev/Arun-Staridb/password"
}

def get_conjur_token():
    with open(CONJUR_TOKEN_PATH, 'r') as f:
        return f.read()

def get_secret(secret_id):
    token = get_conjur_token()
    headers = {"Authorization": f'Token token="{token}"'}
    url = f"{CONJUR_API_URL}/secrets/conjur/variable/{secret_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.text.strip()

@app.route("/")
def index():
    # Get secrets
    host = get_secret(SECRETS["db_host"])
    user = get_secret(SECRETS["db_user"])
    password = get_secret(SECRETS["db_pass"])

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        dbname="postgres"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT service, subscribers, revenue FROM services")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    services = [{"name": r[0], "subscribers": r[1], "revenue": r[2]} for r in rows]
    return render_template("index.html", services=services)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
