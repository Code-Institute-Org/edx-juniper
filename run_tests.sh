#!/bin/sh

EDX_IMAGE=${EDX_IMAGE:=edx-juniper}
TEST_CASE_CLASS="${1:-ci_program.tests}"

docker-compose -f docker-compose-unittest.yml run --rm ci-lms ./manage.py lms test ${TEST_CASE_CLASS} --verbosity=3 --keepdb --settings=unittests
