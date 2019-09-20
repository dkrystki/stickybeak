#!/usr/bin/env bash

set -euxo pipefail

cd /srv
python setup.py sdist
python setup.py bdist_wheel

