#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Usa as pastas já criadas. Não registra nem formata OSDs.
for no in ceph1 ceph2 ceph3; do
  if [[ ! -d "dados/$no/mon/ceph-$no" ]]; then
    echo "Não encontrei os dados do monitor $no."
    echo 'Para uma instalação limpa, use configurar_cluster.sh.'
    exit 1
  fi
done
for id in 0 1 2; do
  no="ceph$((id + 1))"
  if [[ ! -d "dados/$no/osd/ceph-$id" ]]; then
    echo "Não encontrei os dados do osd.$id no $no."
    exit 1
  fi
done

docker compose up -d

esta_rodando() {
  local no="$1" tipo="$2" id="$3"
  docker exec "$no" sh -c "ps -ef | grep -E '[c]eph-$tipo -f -i $id( |$)' >/dev/null"
}

iniciar_se_ausente() {
  local no="$1" tipo="$2" id="$3"
  if esta_rodando "$no" "$tipo" "$id"; then
    echo "OK: $tipo no $no já estava ativo."
  else
    echo "Iniciando $tipo no $no..."
    docker exec -d -u ceph "$no" "ceph-$tipo" -f -i "$id"
  fi
}

for no in ceph1 ceph2 ceph3; do
  iniciar_se_ausente "$no" mon "$no"
done

# Evita tentar comandos de administração antes da formação do quórum.
echo 'Aguardando o quórum...'
QUORUM_OK=0
for _ in $(seq 1 18); do
  if timeout 10 docker exec ceph1 ceph quorum_status -f json 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    sys.exit(0 if len(d.get("quorum_names", []))>=2 else 1)
except Exception:
    sys.exit(1)
' 2>/dev/null; then
    QUORUM_OK=1
    break
  fi
  sleep 3
done
if [[ "$QUORUM_OK" -ne 1 ]]; then
  echo 'Sem quórum. Confira os monitores e a rede Docker.'
  exit 1
fi

iniciar_se_ausente ceph1 mgr ceph1
iniciar_se_ausente ceph1 osd 0
iniciar_se_ausente ceph2 osd 1
iniciar_se_ausente ceph3 osd 2

echo 'Serviços iniciados quando necessário. Conferindo estado:'
bash scripts/verificar_cluster.sh
