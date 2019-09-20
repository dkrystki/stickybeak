#!/usr/bin/env bash

set -euxo pipefail

cd /srv
mkdir -p test-results
flake8 . | tee ./test-results/flake8.txt
