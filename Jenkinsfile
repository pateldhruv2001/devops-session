pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install & Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r requirements.txt
                    pytest -q
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build --network host -t devops-session-app:jenkins-${BUILD_NUMBER} .'
            }
        }
    }
}
