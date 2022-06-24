#!/usr/bin/env bash
set -o errexit

die() { set +v; echo "$*" 1>&2 ; exit 1; }

flake8 src || die 'Try: autopep8 --in-place --aggressive -r .'
mypy
pytest --doctest-modules
