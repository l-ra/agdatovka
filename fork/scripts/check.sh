#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 "$root/scripts/smoke.py" --profile offline-fixture
for profile in ag-synthetic isds-public-test; do
  python3 "$root/scripts/smoke.py" --profile "$profile"
done
if grep -RInE 'https?://(www\.)?(datovka\.gov\.cz|isds\.cz)|password:|token:|private_key:' "$root/profiles"; then
  echo 'forbidden production host or inline secret pattern found' >&2
  exit 1
fi
if grep -RInE 'agdatovka/(data|db)|BEGIN (RSA |EC )?PRIVATE KEY' "$root/profiles" "$root/fixtures"; then
  echo 'former data or private key material found in fork artifact' >&2
  exit 1
fi
echo 'fork checks: pass'
