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
    - name: kaniko
      image: gcr.io/kaniko-project/executor:v1.23.2-debug
      command:
        - cat
      tty: true
      volumeMounts:
        - name: kaniko-docker-config
          mountPath: /kaniko/.docker

    - name: kubectl
      image: bitnamilegacy/kubectl:1.33.4
      command:
        - cat
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
        REPO_URL = "https://github.com/raph2611toky/monsterstack.git"
        BRANCH = "main"

        REGISTRY = "registry-gc.duckdns.org"

        BACKEND_IMAGE = "${REGISTRY}/monster-backend"
        FRONTEND_IMAGE = "${REGISTRY}/monster-frontend"

        K8S_NAMESPACE = "prod"
        K8S_FILE = "k8s.yml"
    }

    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'ref', value: '$.ref'],
                [key: 'repository', value: '$.repository.full_name']
            ],
            token: "T4zONcGflGr0FJrHIATACqznFfdnDPmS3UMsLzvI9W1OhFUk525vRyzDKn4vQVB22jWOTZB7vU5x1N6GQ001hWSK34gOlAlGkhjEf9xyu0iPgDMFXF6IdTBvWCAWfFARyYG3FQxYgiZGlNIpcSEYNpglVLYcM9BHCCnTdtorvjM35IoyXJRPMdwkRSf0BGHhBB69i4A8",
            printContributedVariables: true,
            printPostContent: false
        )
    }

    stages {
        stage('Clone Repository') {
            steps {
                git url: "${REPO_URL}", branch: "${BRANCH}"
            }
        }

        stage('Build and Push Backend') {
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \
                          --context ${WORKSPACE}/backend \
                          --dockerfile ${WORKSPACE}/backend/Dockerfile \
                          --destination ${BACKEND_IMAGE}:${BUILD_NUMBER} \
                          --destination ${BACKEND_IMAGE}:latest
                    """
                }
            }
        }

        stage('Build and Push Frontend') {
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \
                          --context ${WORKSPACE}/frontend \
                          --dockerfile ${WORKSPACE}/frontend/Dockerfile \
                          --destination ${FRONTEND_IMAGE}:${BUILD_NUMBER} \
                          --destination ${FRONTEND_IMAGE}:latest
                    """
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                container('kubectl') {
                    sh """
                        kubectl apply -f ${K8S_FILE}

                        kubectl -n ${K8S_NAMESPACE} set image deployment/monster-backend \
                          monster-backend=${BACKEND_IMAGE}:${BUILD_NUMBER}

                        kubectl -n ${K8S_NAMESPACE} set image deployment/monster-frontend \
                          monster-frontend=${FRONTEND_IMAGE}:${BUILD_NUMBER}

                        kubectl -n ${K8S_NAMESPACE} rollout status deployment/monster-backend --timeout=180s
                        kubectl -n ${K8S_NAMESPACE} rollout status deployment/monster-frontend --timeout=180s
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