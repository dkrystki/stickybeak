#!/usr/bin/env bash

set -euxo pipefail

cd /srv
mkdir -p test-results
mypy . | tee ./test-results/mypy.txt
