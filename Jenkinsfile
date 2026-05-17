pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: monsterstack-builder
spec:
  serviceAccountName: jenkins

  containers:
    - name: kaniko-backend
      image: gcr.io/kaniko-project/executor:v1.23.2-debug
      command:
        - sleep
      args:
        - "999999"
      tty: true
      volumeMounts:
        - name: kaniko-docker-config
          mountPath: /kaniko/.docker

    - name: kaniko-frontend
      image: gcr.io/kaniko-project/executor:v1.23.2-debug
      command:
        - sleep
      args:
        - "999999"
      tty: true
      volumeMounts:
        - name: kaniko-docker-config
          mountPath: /kaniko/.docker

    - name: kubectl
      image: alpine/kubectl:1.33.4
      command:
        - sleep
      args:
        - "999999"
      tty: true

  volumes:
    - name: kaniko-docker-config
      secret:
        secretName: kaniko-docker-config
        items:
          - key: .dockerconfigjson
            path: config.json
"""
        }
    }

    environment {
        REGISTRY = "registry-gc.duckdns.org"

        BACKEND_IMAGE = "${REGISTRY}/monster-backend"
        FRONTEND_IMAGE = "${REGISTRY}/monster-frontend"

        K8S_NAMESPACE = "prod"
        K8S_FILE = "k8s.yml"
    }

    stages {
        stage('Build and Push Backend') {
            steps {
                container('kaniko-backend') {
                    sh """
                        /kaniko/executor \
                          --context ${WORKSPACE}/backend \
                          --dockerfile ${WORKSPACE}/backend/Dockerfile \
                          --destination ${BACKEND_IMAGE}:${BUILD_NUMBER} \
                          --destination ${BACKEND_IMAGE}:latest \
                          --cleanup
                    """
                }
            }
        }

        stage('Build and Push Frontend') {
            steps {
                container('kaniko-frontend') {
                    sh """
                        /kaniko/executor \
                          --context ${WORKSPACE}/frontend \
                          --dockerfile ${WORKSPACE}/frontend/Dockerfile \
                          --destination ${FRONTEND_IMAGE}:${BUILD_NUMBER} \
                          --destination ${FRONTEND_IMAGE}:latest \
                          --cleanup
                    """
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                container('kubectl') {
                    sh """
                        echo "--- Vérification kubectl ---"
                        kubectl version --client=true

                        echo "--- Déploiement Kubernetes ---"
                        kubectl apply -f ${K8S_FILE}

                        echo "--- Mise à jour backend ---"
                        kubectl -n ${K8S_NAMESPACE} set image deployment/monster-backend \
                          monster-backend=${BACKEND_IMAGE}:${BUILD_NUMBER}

                        echo "--- Mise à jour frontend ---"
                        kubectl -n ${K8S_NAMESPACE} set image deployment/monster-frontend \
                          monster-frontend=${FRONTEND_IMAGE}:${BUILD_NUMBER}

                        echo "--- Vérification rollout backend ---"
                        kubectl -n ${K8S_NAMESPACE} rollout status deployment/monster-backend --timeout=180s

                        echo "--- Vérification rollout frontend ---"
                        kubectl -n ${K8S_NAMESPACE} rollout status deployment/monster-frontend --timeout=180s

                        echo "--- Ressources prod ---"
                        kubectl get pods -n ${K8S_NAMESPACE}
                        kubectl get svc -n ${K8S_NAMESPACE}
                        kubectl get ingress -n ${K8S_NAMESPACE}
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Déploiement terminé avec succès."
        }

        failure {
            echo "Erreur pendant le build ou le déploiement."
        }
    }
}