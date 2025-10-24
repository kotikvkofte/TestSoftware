pipeline {
  agent any
  options { timestamps(); ansiColor('xterm') }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Hello')    { steps { echo "Jenkins ${JENKINS_URL ?: ''} works ✔" } }
  }
}
