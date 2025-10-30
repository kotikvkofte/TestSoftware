pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
  }

  environment {
    // Порты проброса QEMU→хост
    SSH_PORT   = '2222'
    HTTPS_PORT = '2443'
    IPMI_PORT  = '2623'

    OPENBMC_HOST  = '127.0.0.1'
    OPENBMC_HTTPS = "https://${OPENBMC_HOST}:${HTTPS_PORT}"

    // Каталоги артефактов/отчётов
    ART_ROOT  = 'artifacts'
    QEMU_LOG  = 'artifacts/qemu/qemu.log'
    ROBOT_OUT = 'artifacts/robot'
    WEBUI_OUT = 'artifacts/webui'
    LOAD_OUT  = 'artifacts/load'
    PYREPORTS = 'reports' // для pytest
  }

  triggers {
    // убери, если используешь webhook
    pollSCM('H/10 * * * *')
  }

  stages {

    stage('Checkout') {
      steps {
        deleteDir()
        git branch: 'lab7',
            url: 'https://github.com/kotikvkofte/TestSoftware.git'
        sh 'git rev-parse --short HEAD || true'
        sh 'mkdir -p artifacts/qemu artifacts/robot artifacts/webui artifacts/load reports .qemu'
      }
    }

    stage('Provision tools (apt+python)') {
      steps {
        sh '''
          set -eux
          # Определяем префикс sudo, если есть
          if command -v sudo >/dev/null 2>&1; then SUDO=sudo; else SUDO=""; fi

          # Базовые утилиты и зависимости
          $SUDO apt-get update -o Acquire::Retries=5
          $SUDO apt-get install -y --no-install-recommends \
              qemu-system-arm ipmitool curl unzip netcat-openbsd jq \
              python3 python3-pip python3-venv ca-certificates git \
              xvfb chromium-driver libnss3 libgconf-2-4

          # Python env для pytest/robot
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip wheel
          pip install pytest pytest-cov pytest-html
          # если есть requirements.txt в репо — поставим
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          # Robot-библиотеки (для API/GUI тестов OpenBMC, по желанию)
          pip install robotframework robotframework-requests robotframework-sshlibrary robotframework-seleniumlibrary

          # Установим маленький утилитарный нагрузочник hey
          if ! command -v hey >/dev/null 2>&1; then
            curl -L -o hey.tar.gz https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64.tar.gz
            tar -xzf hey.tar.gz hey && chmod +x hey
            $SUDO mv hey /usr/local/bin/
          fi
        '''
      }
    }

    stage('Start QEMU + OpenBMC') {
      steps {
        sh '''
          set -eux
          cd .qemu

          # Скачиваем ROMULUS образ (zip) и распаковываем при первом запуске
          if [ ! -f romulus/obmc-phosphor-image-romulus.static.mtd ]; then
            curl -L -o romulus.zip \
              "https://jenkins.openbmc.org/job/ci-openbmc/lastSuccessfulBuild/distro=ubuntu,label=docker-builder,target=romulus/artifact/openbmc/build/tmp/deploy/images/romulus/*zip*/romulus.zip"
            rm -rf romulus
            mkdir -p romulus
            unzip -o romulus.zip -d romulus
          fi

          # Проверим наличие qemu
          command -v qemu-system-arm

          # Стартуем QEMU в фоне, лог — в artifacts/qemu/qemu.log
          qemu-system-arm -m 256 -M romulus-bmc -nographic \
            -drive file=romulus/obmc-phosphor-image-romulus.static.mtd,format=raw,if=mtd \
            -net nic -net user,hostfwd=:0.0.0.0:${SSH_PORT}-:22,hostfwd=:0.0.0.0:${HTTPS_PORT}-:443,hostfwd=udp:0.0.0.0:${IPMI_PORT}-:623,hostname=qemu \
            > "../${QEMU_LOG}" 2>&1 &

          echo $! > ../qemu.pid
          cd ..

          # Ждём пока BMC поднимет HTTPS-порт
          SECS=0; TIMEOUT=300
          until nc -z ${OPENBMC_HOST} ${HTTPS_PORT}; do
            sleep 3; SECS=$((SECS+3))
            if [ $SECS -ge $TIMEOUT ]; then
              echo "[ERROR] BMC did not come up in time"; exit 1
            fi
          done
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: "${QEMU_LOG}", onlyIfSuccessful: false
        }
      }
    }

    stage('Pytest (tests from repo)') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          mkdir -p ${PYREPORTS}
          # Запуск pytest: JUnit + coverage + HTML-отчёт
          pytest -q --maxfail=1 --disable-warnings \
            --junitxml=${PYREPORTS}/junit.xml \
            --cov=. --cov-report=xml:${PYREPORTS}/coverage.xml --cov-report=term-missing \
            --html=${PYREPORTS}/pytest.html --self-contained-html
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: '${PYREPORTS}/junit.xml'
          archiveArtifacts artifacts: '${PYREPORTS}/**', onlyIfSuccessful: false
        }
      }
    }

    stage('Robot API tests (optional)') {
      when { expression { return true } } // поменяй на false, если не нужно
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          if [ ! -d openbmc-test-automation ]; then
            git clone --depth=1 https://github.com/openbmc/openbmc-test-automation.git
          fi
          cd openbmc-test-automation
          robot -v OPENBMC_HOST:${OPENBMC_HOST} -v OPENBMC_PORT:${HTTPS_PORT} \
                --outputdir "../${ROBOT_OUT}" redfish ipmi || true
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: "${ROBOT_OUT}/**", onlyIfSuccessful: false
        }
      }
    }

    stage('Robot WebUI tests (optional)') {
      when { expression { return true } } // поменяй на false, если не нужно
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          cd openbmc-test-automation
          export ROBOT_SYSLOG_FILE="../${WEBUI_OUT}/robot_syslog.txt"
          robot -v OPENBMC_HOST:${OPENBMC_HOST} -v OPENBMC_PORT:${HTTPS_PORT} \
                -v VERIFY_TLS:false \
                --outputdir "../${WEBUI_OUT}" gui || true
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: "${WEBUI_OUT}/**", onlyIfSuccessful: false
        }
      }
    }

    stage('Load testing (hey)') {
      steps {
        sh '''
          set -eux
          hey -z 30s -c 25 -m GET "${OPENBMC_HTTPS}/" > "${LOAD_OUT}/hey.txt" 2>&1 || true
          grep -E 'Requests/sec|Latency' "${LOAD_OUT}/hey.txt" | sed 's/  */ /g' > "${LOAD_OUT}/summary.txt" || true
        '''
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
          # 1) obmcutil state — на самом BMC (ssh: root / 0penBmc)
          ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
              -p "${SSH_PORT}" root@${OPENBMC_HOST} 'obmcutil state' \
              | tee artifacts/qemu/obmcutil_state.txt || true

          # 2) FRU через IPMI с хоста
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
