#!/usr/bin/env bash

set -euxo pipefail

cd /srv
mkdir -p test-results
cd tests
pytest --cov-config=.coveragerc --cov=stickybeak --junitxml=../workspace/test-results/summary.xml --cov-report=xml --cov-report=html
