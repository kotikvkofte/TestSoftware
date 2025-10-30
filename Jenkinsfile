pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
  }

  environment {
    // Порты QEMU
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
    DEBIAN_FRONTEND = 'noninteractive'
  }

  stages {

    stage('Checkout') {
      steps {
        deleteDir()
        // укажи здесь правильную ветку
        git branch: 'lab7', url: 'https://github.com/kotikvkofte/TestSoftware.git'
        sh 'mkdir -p ${QEMU_DIR} artifacts/qemu ${REPORTS}'
      }
    }

    stage('Provision tools (Chrome + matching chromedriver)') {
      steps {
        sh '''
          set -eux
          if command -v sudo >/dev/null 2>&1; then SUDO=sudo; else SUDO=""; fi

          $SUDO apt-get update -o Acquire::Retries=5
          $SUDO apt-get install -y --no-install-recommends \
            qemu-system-arm ipmitool curl unzip netcat-openbsd jq \
            python3 python3-pip python3-venv ca-certificates git \
            xvfb libnss3

          # Google Chrome
          $SUDO mkdir -p /usr/share/keyrings
          curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | $SUDO gpg --dearmor -o /usr/share/keyrings/google.gpg
          echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] https://dl.google.com/linux/chrome/deb/ stable main' | $SUDO tee /etc/apt/sources.list.d/google-chrome.list >/dev/null
          $SUDO apt-get update -o Acquire::Retries=5
          $SUDO apt-get install -y --no-install-recommends google-chrome-stable

          # Подбор chromedriver по Chrome for Testing (новый источник)
          CHROME_VER=$(google-chrome --version | awk '{print $3}')
          MAJOR=${CHROME_VER%%.*}
          # Берём known-good-versions JSON и ищем последнюю 142.x (или текущий major)
          KGV_URL="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
          CFT_VER=$(curl -fsSL "$KGV_URL" | jq -r --arg M "$MAJOR." '.versions[] | select(.version|startswith($M)) | .version' | sort -V | tail -1)

          # Скачиваем chromedriver для Linux x64
          CFT_ZIP="https://storage.googleapis.com/chrome-for-testing-public/${CFT_VER}/linux64/chromedriver-linux64.zip"
          curl -fsSL "$CFT_ZIP" -o /tmp/chromedriver.zip
          $SUDO unzip -o /tmp/chromedriver.zip -d /tmp
          # кладём туда, где ждёт твой тест
          if [ -x /tmp/chromedriver-linux64/chromedriver ]; then
            $SUDO mv /tmp/chromedriver-linux64/chromedriver /usr/bin/chromedriver
            $SUDO chmod +x /usr/bin/chromedriver
          else
            echo "[ERROR] chromedriver not found in archive"; exit 22
          fi

          # Python env + pytest + selenium
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

          # виртуальный дисплей для не-headless браузера
          Xvfb :99 -screen 0 1920x1080x24 >/dev/null 2>&1 &
          export DISPLAY=:99

          export OPENBMC_URL="${OPENBMC_URL}"
          export OPENBMC_USER="${OPENBMC_USER}"
          export OPENBMC_PASS="${OPENBMC_PASS}"

          # пути так, как ожидает твой тест
          export CHROMEDRIVER_PATH="/usr/bin/chromedriver"
          export CHROME_BIN="/usr/bin/google-chrome"

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
