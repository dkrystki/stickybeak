#!/usr/bin/env bash

set -euxo pipefail

cd /srv
sudo python setup.py sdist
sudo python setup.py bdist_wheel

