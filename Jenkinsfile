pipeline {
  agent any

  options {
    timestamps()
    // включи строку ниже, если установлен плагин AnsiColor
    // ansiColor('xterm')
    buildDiscarder(logRotator(numToKeepStr: '15'))
    disableConcurrentBuilds()
  }

  environment {
    SSH_PORT   = '2222'
    HTTPS_PORT = '2443'
    IPMI_PORT  = '2623'
    OPENBMC_HOST = '127.0.0.1'
    OPENBMC_HTTPS = "https://${OPENBMC_HOST}:${HTTPS_PORT}"

    ART_ROOT  = 'artifacts'
    QEMU_LOG  = 'artifacts/qemu/qemu.log'
    ROBOT_OUT = 'artifacts/robot'
    WEBUI_OUT = 'artifacts/webui'
    LOAD_OUT  = 'artifacts/load'
  }

  triggers {
    // можно выключить, если используешь вебхук
    pollSCM('H/10 * * * *')
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'mkdir -p artifacts/qemu artifacts/robot artifacts/webui artifacts/load'
      }
    }

    stage('Provision tools') {
      steps {
        sh '''
          set -eux
          sudo apt-get update -o Acquire::Retries=5
          sudo apt-get install -y --no-install-recommends \
            qemu-system-arm ipmitool curl unzip netcat-openbsd jq \
            python3 python3-pip python3-venv ca-certificates git \
            xvfb chromium-driver libnss3 libgconf-2-4

          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          pip install robotframework robotframework-requests robotframework-sshlibrary robotframework-seleniumlibrary
        '''
      }
    }

    stage('Start QEMU + OpenBMC') {
      steps {
        sh '''
          set -eux
          chmod +x ci/scripts/*.sh
          # стартуем QEMU и ждём пока поднимется HTTPS порт OpenBMC
          ci/scripts/run_qemu_openbmc.sh "${HTTPS_PORT}" "${SSH_PORT}" "${IPMI_PORT}" >"${QEMU_LOG}" 2>&1 &
          echo $! > qemu.pid
          ci/scripts/wait_for_bmc.sh "${OPENBMC_HOST}" "${HTTPS_PORT}" 300
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: "${QEMU_LOG}", onlyIfSuccessful: false
        }
      }
    }

    stage('API tests (Robot: Redfish/IPMI)') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          ci/scripts/run_robot_tests.sh "${OPENBMC_HOST}" "${HTTPS_PORT}" "${ROBOT_OUT}"
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: "${ROBOT_OUT}/**", onlyIfSuccessful: false
          publishHTML(target: [
            reportDir: "${ROBOT_OUT}",
            reportFiles: 'report.html,log.html',
            reportName: 'Robot API Tests',
            keepAll: true,
            alwaysLinkToLastBuild: true
          ])
        }
      }
    }

    stage('WebUI tests (Robot + Selenium)') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          ci/scripts/run_webui_tests.sh "${OPENBMC_HOST}" "${HTTPS_PORT}" "${WEBUI_OUT}"
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: "${WEBUI_OUT}/**", onlyIfSuccessful: false
          publishHTML(target: [
            reportDir: "${WEBUI_OUT}",
            reportFiles: 'report.html,log.html',
            reportName: 'Robot WebUI Tests',
            keepAll: true,
            alwaysLinkToLastBuild: true
          ])
        }
      }
    }

    stage('Load testing') {
      steps {
        sh 'ci/scripts/run_load_test.sh "${OPENBMC_HTTPS}" "${LOAD_OUT}"'
      }
      post {
        always {
          archiveArtifacts artifacts: "${LOAD_OUT}/**", onlyIfSuccessful: false
        }
      }
    }

    stage('Collect evidence (obmcutil & ipmitool)') {
      steps {
        sh '''
          set -eux
          # 1) состояние сервисов на самом BMC
          ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
              -p "${SSH_PORT}" root@${OPENBMC_HOST} 'obmcutil state' \
              | tee artifacts/qemu/obmcutil_state.txt || true

          # 2) FRU через IPMI c хоста
          ipmitool -I lanplus -H ${OPENBMC_HOST} -p ${IPMI_PORT} -U root -P 0penBmc fru print \
              | tee artifacts/qemu/ipmi_fru_print.txt || true
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'artifacts/qemu/obmcutil_state.txt,artifacts/qemu/ipmi_fru_print.txt', onlyIfSuccessful: false
        }
      }
    }
  }

  post {
    always {
      script {
        sh '''
          set +e
          if [ -f qemu.pid ]; then kill -9 "$(cat qemu.pid)" || true; fi
          pkill -f qemu-system-arm || true
        '''
      }
    }
  }
}
