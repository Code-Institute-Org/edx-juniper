#!/bin/bash

set -e

LMS_PORT=${LMS_PORT:=8000}
IS_HEALTHY_FILE=/tmp/is_health_file_$HOSTNAME

if [ -f "$IS_HEALTHY_FILE" ]; then
    echo "$IS_HEALTHY_FILE exists."
else
    echo "$IS_HEALTHY_FILE does not exist."
    curl -f http://localhost:$LMS_PORT
    echo "success" > $IS_HEALTHY_FILE
fi
