#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Parâmetros temporários para o E9; não usar em produção.
ESTADO="$(timeout 20 docker exec ceph1 ceph -s)"
if [[ "$ESTADO" != *'3 osds: 3 up'* || "$ESTADO" != *'3 in'* || "$ESTADO" != *'33 active+clean'* ]]; then
  echo 'O cluster precisa estar em 3 up, 3 in e 33 active+clean.'
  exit 1
fi

for no in ceph1 ceph2 ceph3; do
  echo "Configurando monitor $no..."
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_down_out_interval 45 >/dev/null
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_heartbeat_grace false >/dev/null
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_down_out_interval false >/dev/null

done

python3 - <<'PY'
import json, subprocess
for no in ('ceph1', 'ceph2', 'ceph3'):
    for nome, esperado in (
        ('mon_osd_down_out_interval', '45'),
        ('mon_osd_adjust_heartbeat_grace', 'false'),
        ('mon_osd_adjust_down_out_interval', 'false'),
    ):
        txt = subprocess.check_output(
            ['docker', 'exec', no, 'ceph', 'daemon', f'mon.{no}', 'config', 'get', nome],
            text=True, timeout=20,
        )
        atual = str(json.loads(txt)[nome]).lower()
        if atual != esperado:
            raise SystemExit(f'{no}: {nome}={atual}, esperado {esperado}')
print('Configuração temporária do E9 confirmada nos três monitores.')
PY

echo 'Depois: python3 experimentos/experimento_e9_serie.py 10 (ou 20)'
echo 'Ao terminar, use: bash scripts/restaurar_e9.sh'
