#!/bin/sh

EDX_IMAGE=${EDX_IMAGE:=edx-juniper}

docker-compose -f docker-compose-unittest.yml run --rm ci-lms ./manage.py lms test ci_program.tests --verbosity=3 --keepdb
