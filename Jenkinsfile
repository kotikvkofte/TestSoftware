pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
  }

  environment {
    SSH_PORT   = '2222'
    HTTPS_PORT = '2443'
    IPMI_PORT  = '2623'

    OPENBMC_HOST  = '127.0.0.1'
    OPENBMC_URL   = "https://${OPENBMC_HOST}:${HTTPS_PORT}"

    OPENBMC_USER  = 'root'
    OPENBMC_PASS  = '0penBmc'

    QEMU_DIR   = '.qemu'
    QEMU_LOG   = 'artifacts/qemu/qemu.log'
    REPORTS    = 'reports'
  }

  stages {
    stage('Checkout') {
      steps {
        deleteDir()
        git branch: 'lab7', url: 'https://github.com/kotikvkofte/TestSoftware.git' // поменяй ветку при необходимости
        sh 'mkdir -p ${QEMU_DIR} artifacts/qemu ${REPORTS}'
      }
    }

    stage('Provision tools (apt + Chrome/chromedriver)') {
      steps {
        sh '''
          set -eux
          if command -v sudo >/dev/null 2>&1; then SUDO=sudo; else SUDO=""; fi

          # База (без спорных пакетов)
          $SUDO apt-get update -o Acquire::Retries=5
          $SUDO apt-get install -y --no-install-recommends \
            qemu-system-arm ipmitool curl unzip netcat-openbsd jq \
            python3 python3-pip python3-venv ca-certificates git \
            xvfb libnss3

          # === Путь А: Google Chrome + совместимый chromedriver ===
          set +e
          HAVE_CHROME=0
          $SUDO mkdir -p /usr/share/keyrings
          curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | $SUDO gpg --dearmor -o /usr/share/keyrings/google.gpg
          echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] https://dl.google.com/linux/chrome/deb/ stable main' | $SUDO tee /etc/apt/sources.list.d/google-chrome.list >/dev/null
          $SUDO apt-get update -o Acquire::Retries=5
          if $SUDO apt-get install -y --no-install-recommends google-chrome-stable; then
            HAVE_CHROME=1
          fi
          set -e

          if [ "$HAVE_CHROME" -eq 1 ]; then
            # определяем major-версию Chrome и тянем подходящий chromedriver
            CHROME_VER=$(google-chrome --version | awk '{print $3}')
            MAJOR=${CHROME_VER%%.*}
            LATEST_URL="https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${MAJOR}"
            CHDRV_VER=$(curl -fsSL "$LATEST_URL")
            curl -fsSL "https://chromedriver.storage.googleapis.com/${CHDRV_VER}/chromedriver_linux64.zip" -o /tmp/chromedriver.zip
            $SUDO unzip -o /tmp/chromedriver.zip -d /usr/local/bin
            $SUDO chmod +x /usr/local/bin/chromedriver
            export CHROME_BIN="/usr/bin/google-chrome"
          else
            echo "[WARN] Google Chrome repo install failed, fallback to Debian chromium"
            # === Путь B: Debian chromium + chromium-driver (с ретраями) ===
            set +e
            $SUDO apt-get update -o Acquire::Retries=5
            $SUDO apt-get install -y --no-install-recommends chromium chromium-driver
            RC=$?
            set -e
            if [ "$RC" -ne 0 ]; then
              echo "[ERROR] Не удалось установить ни google-chrome, ни chromium. Прерываю."
              exit 100
            fi
            export CHROME_BIN="/usr/bin/chromium"
          fi

          # Python env + pytest
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip wheel
          pip install pytest pytest-html selenium
        '''
      }
    }

    stage('Start QEMU (OpenBMC)') {
      steps {
        sh '''
          set -eux
          cd "${QEMU_DIR}"

          if [ ! -f romulus/obmc-phosphor-image-romulus.static.mtd ]; then
            curl -L -o romulus.zip \
              "https://jenkins.openbmc.org/job/ci-openbmc/lastSuccessfulBuild/distro=ubuntu,label=docker-builder,target=romulus/artifact/openbmc/build/tmp/deploy/images/romulus/*zip*/romulus.zip"
            rm -rf romulus
            mkdir -p romulus
            unzip -o romulus.zip -d romulus
          fi

          qemu-system-arm -m 256 -M romulus-bmc -nographic \
            -drive file=romulus/obmc-phosphor-image-romulus.static.mtd,format=raw,if=mtd \
            -net nic -net user,hostfwd=:0.0.0.0:${SSH_PORT}-:22,hostfwd=:0.0.0.0:${HTTPS_PORT}-:443,hostfwd=udp:0.0.0.0:${IPMI_PORT}-:623,hostname=qemu \
            > "../${QEMU_LOG}" 2>&1 &

          echo $! > ../qemu.pid
          cd ..

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
        always { archiveArtifacts artifacts: "${QEMU_LOG}", onlyIfSuccessful: false }
      }
    }

    stage('Run pytest (test_hand.py)') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate

          # Виртуальный дисплей для не-headless браузера
          Xvfb :99 -screen 0 1920x1080x24 >/dev/null 2>&1 &
          export DISPLAY=:99

          # переменные, которые читает твой тест
          export OPENBMC_URL="${OPENBMC_URL}"
          export OPENBMC_USER="${OPENBMC_USER}"
          export OPENBMC_PASS="${OPENBMC_PASS}"

          # подскажем пути браузеру/драйверу так, как ждёт твой код
          if command -v google-chrome >/dev/null 2>&1; then
            export CHROME_BIN="/usr/bin/google-chrome"
          else
            export CHROME_BIN="/usr/bin/chromium"
          fi
          if [ -x /usr/local/bin/chromedriver ]; then
            export CHROMEDRIVER_PATH="/usr/local/bin/chromedriver"
          else
            export CHROMEDRIVER_PATH="/usr/bin/chromedriver"
          fi

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
          if [ -f qemu.pid ]; then kill -9 "$(cat qemu.pid)" || true; fi
          pkill -f qemu-system-arm || true
        '''
      }
    }
  }
}
