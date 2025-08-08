pipeline {
  agent {
    kubernetes {
      defaultContainer 'kaniko'
      yaml """
apiVersion: v1
kind: Pod
metadata:
  name: kaniko
spec:
  serviceAccountName: jenkins
  containers:
  - name: kubectl
    image: arunrana1214/debian-k8s-awsctl:latest
    command:
    - /bin/cat
    tty: true    
  - name: kaniko
    image: gcr.io/kaniko-project/executor:debug
    command:
    - /busybox/sh
    tty: true
    volumeMounts:
      - name: kaniko-secret
        mountPath: /kaniko/.docker
  volumes:
    - name: kaniko-secret
      secret:
        secretName: regcred
        items:
          - key: .dockerconfigjson
            path: config.json
"""
    }
  }

  environment {
    REPO_DIR = "StarAi"
  }

  options {
    ansiColor('xterm')
  }

  stages {

    stage('Clone GitHub Repo') {
      steps {
        container('kubectl') {
          withCredentials([
            conjurSecretCredential(credentialsId: 'github-username', variable: 'GIT_USER'),
            conjurSecretCredential(credentialsId: 'github-token', variable: 'GIT_TOKEN')
          ]) {
            sh '''
              echo "[INFO] Cloning GitHub repo..."
              rm -rf ${REPO_DIR}
              git clone https://${GIT_USER}:${GIT_TOKEN}@github.com/Arun-Demos/${REPO_DIR}.git
            '''
          }
        }
      }
    }

    stage('Kaniko Build & Push Image') {
      steps {
        container('kaniko') {
          dir("${env.REPO_DIR}") {
            sh '''
              echo "[INFO] Building Docker image with Kaniko..."
              /kaniko/executor --dockerfile=Dockerfile \
                               --context=. \
                               --destination=arunrana1214/starai:latest
            '''
          }
        }
      }
    }

    stage('Deploy App to Kubernetes') {
      steps {
        container('kubectl') {
          withCredentials([
            conjurSecretCredential(credentialsId: '	data-dynamic-Arun-EKS-AssumeRole', variable: 'AWS_DYNAMIC_SECRET')
          ]) {
            dir("${env.REPO_DIR}") {
              script {
                def creds = readJSON text: AWS_DYNAMIC_SECRET
                env.AWS_ACCESS_KEY_ID = creds.data.access_key_id
                env.AWS_SECRET_ACCESS_KEY = creds.data.secret_access_key
                env.AWS_SESSION_TOKEN = creds.data.session_token
              }

              sh '''
                echo "Verifying AWS identity:"
                aws sts get-caller-identity

                echo "[INFO] Deploying configmap"
                kubectl apply -f manifest/starai-configmap.yaml
                
                echo "[INFO] Deploying Application Pod"
                kubectl apply -f manifest/deployment.yaml

                echo "[INFO] Deploying Service"
                kubectl apply -f manifest/Service.yaml

                echo "[INFO] Deploying Ingress"
                kubectl apply -f manifest/Ingress.yaml
              '''
            }
          }
        }
      }
    }
  }

  post {
    always {
      container('kubectl') {
        sh '''
          echo "[INFO] Cleaning up workspace and kube artifacts..."
          rm -rf ${REPO_DIR}
          kubectl delete -f ${REPO_DIR}/myweb.yaml || true
        '''
      }
    }
  }
}
