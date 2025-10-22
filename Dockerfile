FROM jenkins/jenkins:lts

RUN jenkins-plugin-cli --plugins workflow-aggregator git

EXPOSE 8080
EXPOSE 50000