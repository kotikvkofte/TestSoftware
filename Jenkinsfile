pipeline {
  agent any
  options { timestamps(); ansiColor('xterm') }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Smoke') {
      steps {
        sh 'echo "Repo OK: $(git rev-parse --short HEAD)"'
      }
    }
  }
}
