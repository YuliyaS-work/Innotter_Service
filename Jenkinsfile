pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: python
    image: python:3.13
    imagePullPolicy: IfNotPresent
    command: ['sh', '-c', 'sleep 3600']
    workingDir: /home/jenkins/agent
    securityContext:
      runAsUser: 0
    tty: true
  - name: build-tools
    image: docker:cli
    imagePullPolicy: IfNotPresent
    command: ['sh', '-c', 'sleep 3600']
    workingDir: /home/jenkins/agent
    securityContext:
      runAsUser: 0
    volumeMounts:
    - name: docker-sock
      mountPath: /var/run/docker.sock
    tty: true
  - name: kubectl
    image: bitnami/kubectl:latest
    imagePullPolicy: IfNotPresent
    command: ['sh', '-c', 'sleep 3600']
    workingDir: /home/jenkins/agent
    securityContext:
      runAsUser: 0
    tty: true
  volumes:
  - name: docker-sock
    hostPath:
      path: /var/run/docker.sock
'''
        }
    }
    stages {

        stage('Python CI (Install, Lint, Tests)') {
            steps {
                 container('python') {
                    sh '''
                        pip install uv
                        uv sync
                        uv run ruff format .
                        uv run ruff check .
                    '''

                    withEnv([
                        'DB_ENGINE=django.db.backends.mysql',
                        'MYSQL_HOST=localhost',
                        'MYSQL_PORT=3306',
                        'MYSQL_DATABASE=test',
                        'MYSQL_USER=test',
                        'MYSQL_PASSWORD=test',
                        'SECRET_KEY=secret_key',
                        'REDIS_HOST=localhost',
                        'REDIS_PORT=6379',
                        'REDIS_PASSWORD=test',
                        'AWS_ACCESS_KEY_ID=test',
                        'AWS_SECRET_ACCESS_KEY=test',
                        'AWS_REGION=eu-central-1',
                        'BUCKET_NAME=test',
                        'RABBITMQ_URL=amqp://guest:guest@localhost/'
                        'CELERY_BROKER_URL=redis://localhost',
                        'CELERY_RESULT_BACKEND=redis://localhost',
                        'CELERYD_POOL=test'
                    ]) {
                        sh '''
                            uv run coverage run -m pytest
                            uv run coverage report
                        '''
                    }
                }
            }
        }

        stage('Build Docker') {
            steps {
                container('build-tools') {
                    sh 'docker build -t yuliyaswork/innotter:latest .'
                }
            }
        }

        stage('Push Docker') {
            steps {
                container('build-tools') {
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER')]) {
                        sh '''
                            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                            docker push yuliyaswork/innotter:latest
                        '''
                    }
                }
            }
        }
        stage('Deploy to Minikube') {
            steps {
                container('kubectl') {
                    dir('infra-repo') {
                        git branch: 'feature/k8s', credentialsId: 'github-token', url: 'https://github.com/YuliyaS-work/Innotter_Infrastructure.git'

                        sh '''
                            kubectl apply -f k8s/namespace.yaml

                            kubectl apply -f k8s/shared/rabbitmq.yaml --validate=false
                            kubectl rollout status deployment rabbitmq -n app --timeout=90s
                            kubectl apply -f k8s/innotter/ --validate=false

                            kubectl rollout restart deployment innotter -n app
                            kubectl rollout status deployment innotter -n app --timeout=120s
                        '''
                    }
                }
            }
        }
    }
}