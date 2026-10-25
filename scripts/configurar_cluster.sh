#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Este arquivo é só para a primeira instalação.
# Não execute em um cluster que já possui dados.
if [[ -d dados ]] && [[ -n "$(find dados -mindepth 2 -print -quit)" ]]; then
  echo 'Há arquivos dentro de dados/. Instalação cancelada para preservar o cluster.'
  echo 'Para iniciar serviços existentes, use: bash scripts/reiniciar_cluster.sh'
  exit 1
fi

read -r -p 'Primeira instalação em um ambiente vazio? Digite INSTALAR: ' CONFIRMACAO
if [[ "$CONFIRMACAO" != 'INSTALAR' ]]; then
  echo 'Operação cancelada.'
  exit 1
fi

for arquivo in ceph.conf iniciar_mons.sh iniciar_mgr.sh iniciar_osds.sh; do
  [[ -f "$arquivo" ]] || { echo "Arquivo ausente: $arquivo"; exit 1; }
done

docker compose up -d

# Inicializa os serviços. Os scripts abaixo não devem ser repetidos.
bash iniciar_mons.sh

echo 'Aguardando os três monitores formarem quórum...'
QUORUM_OK=0
for _ in $(seq 1 24); do
  if timeout 10 docker exec ceph1 ceph quorum_status -f json 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    sys.exit(0 if len(d.get("quorum_names", []))==3 else 1)
except Exception:
    sys.exit(1)
' 2>/dev/null; then
    QUORUM_OK=1
    break
  fi
  sleep 3
done

if [[ "$QUORUM_OK" -ne 1 ]]; then
  echo 'O quórum não se formou. Verifique a rede e os monitores.'
  echo 'No Codespaces, veja: bash scripts/ajustar_rede_codespaces.sh'
  echo 'Não rode novamente este instalador; os monitores já foram inicializados.'
  exit 1
fi

bash iniciar_mgr.sh
bash iniciar_osds.sh

docker exec ceph1 ceph osd pool create sd 32
docker exec ceph1 ceph osd pool application enable sd rados

echo 'Instalação solicitada. Confira a recuperação do cluster:'
bash scripts/verificar_cluster.sh
