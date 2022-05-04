#!/usr/bin/env bash

set -e
set -x

pytest app/tests/integration/question_tests.py "${@}"
#pytest --cov=app --cov-report=term-missing app/tests/integration/match_tests.py::TestCaseMatchEndpoints::t_successfulCreationOfAMatch "${@}"
