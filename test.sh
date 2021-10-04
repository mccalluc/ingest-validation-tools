#!/usr/bin/env bash
set -o errexit

start() { echo "::group::$1"; }
end() { echo "::endgroup::"; }
die() { set +v; echo "$*" 1>&2 ; sleep 1; exit 1; }

CONTINUE_FROM="$1"

python -c 'import requests; print(requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS)'

# github ci
# ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:ECDH+AESGCM:DH+AESGCM:ECDH+AES:DH+AES:RSA+AESGCM:RSA+AES:!aNULL:!eNULL:!MD5:!DSS
# local
# ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:ECDH+AESGCM:DH+AESGCM:ECDH+AES:DH+AES:RSA+AESGCM:RSA+AES:!aNULL:!eNULL:!MD5:!DSS

pip freeze | grep 'requests\|urllib3'

# github ci
# requests==2.22.0
# urllib3==1.25.11
# local
# requests==2.22.0
# urllib3==1.25.11

echo DEBUG
./debug_ssl.py
echo TEST
tests/test-tsv-examples.sh

# github ci
# Caused by SSLError(
#  SSLError(1, ''[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:852)''),
# )): "https://www.uniprot.org/uniprot/G9N9I7"'

if [[ -z $CONTINUE_FROM ]]; then
  start flake8
  flake8 src || die 'Try: autopep8 --in-place --aggressive -r .'
  end flake8

  start mypy
  mypy
  end mypy
fi

for TEST in tests/test-*; do
  if [[ -z $CONTINUE_FROM ]] || [[ $CONTINUE_FROM = $TEST ]]; then
    CONTINUE_FROM=''
    start $TEST
    eval $TEST
    end $TEST
  fi
done

start changelog
if [ "$TRAVIS_BRANCH" != 'main' ]; then
  diff CHANGELOG.md <(curl -s https://raw.githubusercontent.com/hubmapconsortium/ingest-validation-tools/main/CHANGELOG.md) \
    && die 'Update CHANGELOG.md'
fi
end changelog
