#!/bin/sh

docker-compose exec mysql mysql openedx -u root -parglebargle -e "CREATE DATABASE IF NOT EXISTS openedx_csmh; GRANT ALL PRIVILEGES ON openedx_csmh.* TO openedx"
docker-compose exec ci-lms ./manage.py lms migrate
docker-compose exec ci-lms ./manage.py cms migrate
docker-compose exec ci-lms ./manage.py lms migrate --database=student_module_history coursewarehistoryextended
