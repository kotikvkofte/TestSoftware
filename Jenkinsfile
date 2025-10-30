pipeline {
  agent {
    docker {
      image 'python:3.11-slim'     // чистая и стабильная среда
      reuseNode true
    }
  }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
  }

  environment {
    REPORTS = 'reports'
    PIP_CACHE_DIR = '.pip-cache'   // кеш pip в рабочей директории
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'mkdir -p ${REPORTS} ${PIP_CACHE_DIR}'
      }
    }

    stage('Setup Python env') {
      steps {
        sh '''
          set -eux
          python -V
          pip install --upgrade pip wheel
          # базовые инструменты тестов
          pip install pytest pytest-cov pytest-html
          # если есть requirements.txt — установим
          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          fi
          # если есть pyproject.toml/setup.cfg/setup.py — поставим сам проект (и тестовые зависимости, если объявлены)
          if [ -f pyproject.toml ] || [ -f setup.cfg ] || [ -f setup.py ]; then
            # сначала пробуем extras "test", если объявлены
            pip install ".[test]" || pip install .
          fi
        '''
      }
    }

    stage('Run pytest') {
      steps {
        // Прогон с JUnit, coverage и HTML-отчётом
        sh '''
          set -eux
          # если каталог tests/ есть — pytest сам найдёт тесты; иначе укажи путь
          pytest \
            -q \
            --maxfail=1 \
            --disable-warnings \
            --junitxml=${REPORTS}/junit.xml \
            --cov=. \
            --cov-report=xml:${REPORTS}/coverage.xml \
            --cov-report=term-missing \
            --html=${REPORTS}/pytest.html \
            --self-contained-html
        '''
      }
      post {
        always {
          // Публикуем результаты даже при падении тестов
          junit allowEmptyResults: true, testResults: '${REPORTS}/junit.xml'
          archiveArtifacts artifacts: '${REPORTS}/**', onlyIfSuccessful: false
          publishHTML(target: [
            reportDir: "${REPORTS}",
            reportFiles: 'pytest.html',
            reportName: 'PyTest Report',
            keepAll: true,
            alwaysLinkToLastBuild: true
          ])
        }
      }
    }
  }
}
