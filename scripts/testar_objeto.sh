#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Teste simples de leitura e escrita no pool sd.
OBJETO="teste_script"

docker exec ceph1 sh -c 'echo "Teste Ceph M2" > /tmp/teste_script.txt && rados -p sd put teste_script /tmp/teste_script.txt'

echo 'Leitura pelo ceph3:'
docker exec ceph3 rados -p sd get "$OBJETO" -

echo 'Mapeamento do objeto:'
docker exec ceph1 ceph osd map sd "$OBJETO"
