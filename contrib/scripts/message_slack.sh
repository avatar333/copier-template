#!/usr/bin/env bash
#title           :message_slack.sh
#description     :This script will receive env vars from inside a Gitlab Runner and post a message to a Slack channel
#author          :Kevin Pillay
#date            :23/07/2025
#version         :0.1
#usage           :bash message_slack.sh
#notes           :Install Vim and curl to use this script.
#shell_version    :bash/zsh
#==============================================================================

CI_JOB_STAGE=$1
CI_JOB_STATUS=$2
CI_PROJECT_NAME=$3
CI_JOB_NAME=$4
GITLAB_USER_NAME="$5"
CI_JOB_URL=$6
SLACK_WEBHOOK=$7

if [ "$CI_JOB_STAGE" == "build" ] || [ "$CI_JOB_STAGE" == "staging" ] || [ "$CI_JOB_STAGE" == "production" ]; then
  DEPLOYMENT_DATE=$(date +"%Y-%m-%dT%H:%M:%SZ")
  CI_JOB_STATUS_UPPER=$(echo ${CI_JOB_STATUS} | tr "[:lower:]" "[:upper:]")
  if [ "$CI_JOB_STATUS" == "success" ]; then
    EMOJI_STATUS=":white_check_mark:"
  else
    EMOJI_STATUS=":exclamation:"
  fi
  curl -s -X POST -H 'Content-type: application/json' --data "{
    \"text\": \"*Project:* $CI_PROJECT_NAME\n*Job:* $CI_JOB_NAME\n*Stage:* $CI_JOB_STAGE\n*User:* $GITLAB_USER_NAME\n*Deployment Date:* $DEPLOYMENT_DATE\n*Status:* $CI_JOB_STATUS_UPPER $EMOJI_STATUS\n*Details:* <$CI_JOB_URL|Job Details>\",
    \"mrkdwn\": true
  }" $SLACK_WEBHOOK;
fi
