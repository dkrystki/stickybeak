#!/usr/bin/env bash

set -euxo pipefail

cd /srv
mkdir -p test-results
rstcheck README.rst | tee ./test-results/rstcheck.txt
