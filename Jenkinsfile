pipeline {

    agent any

    stages {

        stage('Python CI (Install, Lint, Tests)') {
            agent {
                docker {
                    image 'python:3.13'
                    args '-u root'
                }
            }
            steps {
                 sh 'pip install uv'
                 sh 'uv sync'

                sh 'uv run ruff format .'
                sh 'uv run ruff check .'

                withEnv([
                    'DB_ENGINE=django.db.backends.mysql',
                    'DB_HOST=localhost',
                    'DB_PORT=3306',
                    'DB_NAME=test',
                    'DB_USER=test',
                    'DB_PASSWORD=test',
                    'SECRET_KEY=test',
                    'AWS_ACCESS_KEY_ID=test',
                    'AWS_SECRET_ACCESS_KEY=test',
                    'AWS_REGION=eu-central-1',
                    'BUCKET_NAME=test',
                    'RABBITMQ_URL=amqp://localhost',
                    'REDIS_HOST=localhost',
                    'REDIS_PORT=6379',
                    'REDIS_PASSWORD=test',
                    'CELERY_BROKER_URL=redis://localhost',
                    'CELERY_RESULT_BACKEND=redis://localhost',
                    'CELERYD_POOL=test'
                ]) {
                    sh 'uv run coverage run -m pytest'
                    sh 'uv run coverage report'
                }
            }
        }

        stage('Build Docker') {
            steps {
                sh 'docker build -t yuliyaswork/innotter:latest .'
            }
        }

        stage('Push Docker') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'docker-hub-creds', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER')]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    sh 'docker push yuliyaswork/innotter:latest'
                }
            }
        }

//         stage('Deploy to minikube') {
//             steps {
//                 sh 'kubectl apply -f ../infrastructure/k8s/innotter-deployment.yaml'
//                 sh 'kubectl rollout restart deployment innotter -n app'
//             }
//         }
    }
}