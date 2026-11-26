pipeline {
    agent { label 'docker' }

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    stages {
        stage('Check configuration') {
            steps {
                script {
                    if (env.BRANCH_NAME != 'develop') {
                        error("Unsupported branch: ${env.BRANCH_NAME}")
                    }
                    if (!env.DOCKERHUB_NAMESPACE?.trim()) {
                        error('Set DOCKERHUB_NAMESPACE in Jenkins before building')
                    }
                    env.IMAGE_TAG = env.GIT_COMMIT.take(12)
                }
                sh 'docker version && git --version'
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t "docker.io/${DOCKERHUB_NAMESPACE}/moamu-ai:${IMAGE_TAG}" .'
            }
        }

        stage('Push image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKERHUB_USER', passwordVariable: 'DOCKERHUB_TOKEN')]) {
                    sh '''
                        set -eu
                        printf '%s' "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin
                        docker push "docker.io/${DOCKERHUB_NAMESPACE}/moamu-ai:${IMAGE_TAG}"
                        docker logout
                    '''
                }
            }
        }

        stage('Update development manifest') {
            when { branch 'develop' }
            steps {
                sshagent(credentials: ['moamu-deploy-ssh']) {
                    sh '''
                        set -eu
                        git clone --branch main git@github.com:team-moamu/moamu-deploy.git deploy
                        test -f deploy/environments/dev/ai/kustomization.yaml
                        cd deploy/environments/dev/ai
                        kustomize edit set image "moamu-ai=docker.io/${DOCKERHUB_NAMESPACE}/moamu-ai:${IMAGE_TAG}"
                        cd ../../..
                        kustomize build environments/dev > /dev/null
                        git add environments/dev/ai/kustomization.yaml
                        if ! git diff --cached --quiet; then
                            git -c user.name=moamu-deploy-bot -c user.email=moamu-deploy-bot@users.noreply.github.com commit -m "chore: 개발 AI 이미지 ${IMAGE_TAG} 갱신"
                            git push origin HEAD:main
                        fi
                    '''
                }
            }
        }

    }
}
