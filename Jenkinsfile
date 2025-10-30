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
    OPENBMC_URL   = "https://${OPENBMC_HOST}:${HTTPS_PORT}"

    // Дефолтные креды OpenBMC (как в твоём тесте)
    OPENBMC_USER  = 'root'
    OPENBMC_PASS  = '0penBmc'

    // Пути/каталоги
    QEMU_DIR   = '.qemu'
    QEMU_LOG   = 'artifacts/qemu/qemu.log'
    REPORTS    = 'reports'
  }

  stages {

    stage('Checkout') {
      steps {
        deleteDir()
        git branch: 'lab7', url: 'https://github.com/kotikvkofte/TestSoftware.git' // укажи нужную ветку
        sh 'mkdir -p ${QEMU_DIR} artifacts/qemu ${REPORTS}'
        sh 'git rev-parse --short HEAD || true'
      }
    }

    stage('Provision tools') {
      steps {
        sh '''
          set -eux
          # root или sudo (если Jenkins не под root)
          if command -v sudo >/dev/null 2>&1; then SUDO=sudo; else SUDO=""; fi

          $SUDO apt-get update -o Acquire::Retries=5
          # базовое: QEMU, Python, Selenium-стек для Chromium (в Debian trixie пакеты chromium/chromium-driver)
          $SUDO apt-get install -y --no-install-recommends \
            qemu-system-arm ipmitool curl unzip netcat-openbsd jq \
            python3 python3-pip python3-venv ca-certificates git \
            chromium chromium-driver xvfb libnss3

          # питоновское окружение для pytest
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip wheel
          pip install pytest pytest-html
        '''
      }
    }

    stage('Start QEMU (OpenBMC)') {
      steps {
        sh '''
          set -eux
          cd "${QEMU_DIR}"

          # Скачиваем ROMULUS образ (zip) один раз
          if [ ! -f romulus/obmc-phosphor-image-romulus.static.mtd ]; then
            curl -L -o romulus.zip \
              "https://jenkins.openbmc.org/job/ci-openbmc/lastSuccessfulBuild/distro=ubuntu,label=docker-builder,target=romulus/artifact/openbmc/build/tmp/deploy/images/romulus/*zip*/romulus.zip"
            rm -rf romulus
            mkdir -p romulus
            unzip -o romulus.zip -d romulus
          fi

          # Стартуем QEMU в фоне, лог — в artifacts/qemu/qemu.log
          qemu-system-arm -m 256 -M romulus-bmc -nographic \
            -drive file=romulus/obmc-phosphor-image-romulus.static.mtd,format=raw,if=mtd \
            -net nic -net user,hostfwd=:0.0.0.0:${SSH_PORT}-:22,hostfwd=:0.0.0.0:${HTTPS_PORT}-:443,hostfwd=udp:0.0.0.0:${IPMI_PORT}-:623,hostname=qemu \
            > "../${QEMU_LOG}" 2>&1 &

          echo $! > ../qemu.pid
          cd ..

          # Ждём готовности HTTPS (порт 2443 по умолчанию)
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

    stage('Run pytest (test_hand.py)') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate

          # Запустим виртуальный экран для НЕ headless-хрома в твоём тесте
          Xvfb :99 -screen 0 1920x1080x24 >/dev/null 2>&1 &
          export DISPLAY=:99

          # Переменные для твоего теста
          export OPENBMC_URL="${OPENBMC_URL}"
          export OPENBMC_USER="${OPENBMC_USER}"
          export OPENBMC_PASS="${OPENBMC_PASS}"

          # На всякий: явно подскажем путь к chromedriver
          export CHROMEDRIVER_PATH="/usr/bin/chromedriver"
          # Если вдруг в тесте понадобится бинарь chromium под именем google-chrome:
          export CHROME_BIN="/usr/bin/chromium"

          # Прогоним только нужный файл и положим простой HTML-отчёт
          pytest -q tests/test_hand.py \
            --html="${REPORTS}/pytest.html" --self-contained-html \
            --junitxml="${REPORTS}/junit.xml"
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: '${REPORTS}/junit.xml'
          archiveArtifacts artifacts: '${REPORTS}/**', onlyIfSuccessful: false
        }
      }
    }
  }

  post {
    always {
      script {
        sh '''
          set +e
          # Остановим QEMU
          if [ -f qemu.pid ]; then kill -9 "$(cat qemu.pid)" || true; fi
          pkill -f qemu-system-arm || true
        '''
      }
    }
  }
}
