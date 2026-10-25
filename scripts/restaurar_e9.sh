#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Volta aos parâmetros originais do laboratório.
for no in ceph1 ceph2 ceph3; do
  echo "Restaurando monitor $no..."
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_down_out_interval 120 >/dev/null
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_heartbeat_grace true >/dev/null
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_down_out_interval true >/dev/null
done

for item in 'ceph1 mon.ceph1' 'ceph2 mon.ceph2' 'ceph3 mon.ceph3' \
            'ceph1 osd.0' 'ceph2 osd.1' 'ceph3 osd.2'; do
  read -r no daemon <<< "$item"
  docker exec "$no" ceph daemon "$daemon" config set osd_heartbeat_grace 20 >/dev/null
done

python3 - <<'PY'
import json, subprocess
for no in ('ceph1','ceph2','ceph3'):
    for nome, esperado in (
        ('mon_osd_down_out_interval', '120'),
        ('mon_osd_adjust_heartbeat_grace', 'true'),
        ('mon_osd_adjust_down_out_interval', 'true'),
    ):
        txt = subprocess.check_output(
            ['docker','exec',no,'ceph','daemon',f'mon.{no}','config','get',nome],
            text=True,timeout=20,
        )
        atual = str(json.loads(txt)[nome]).lower()
        if atual != esperado:
            raise SystemExit(f'{no}: {nome}={atual}, esperado {esperado}')
for no,daemon in (
    ('ceph1','mon.ceph1'),('ceph2','mon.ceph2'),('ceph3','mon.ceph3'),
    ('ceph1','osd.0'),('ceph2','osd.1'),('ceph3','osd.2'),
):
    txt = subprocess.check_output(
        ['docker','exec',no,'ceph','daemon',daemon,'config','get','osd_heartbeat_grace'],
        text=True,timeout=20,
    )
    if str(json.loads(txt)['osd_heartbeat_grace']) != '20':
        raise SystemExit(f'{daemon}: grace não voltou para 20')
print('Configuração original confirmada nos seis processos.')
PY

bash scripts/verificar_cluster.sh
