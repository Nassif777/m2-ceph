#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

normal() {
  timeout 15 docker exec ceph1 ceph status -f json | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except (ValueError, OSError):
    sys.exit(1)
o=d["osdmap"]; p=d["pgmap"]
q=d.get("quorum_names", [])
clean=sum(x["count"] for x in p.get("pgs_by_state",[]) if x["state_name"]=="active+clean")
sys.exit(0 if o["num_up_osds"]==3 and o["num_in_osds"]==3 and len(q)==3 and p["num_pgs"]>0 and clean==p["num_pgs"] else 1)
'
}

recuperar_ao_sair() {
  local codigo=$?
  trap - EXIT INT TERM
  if ! bash scripts/demo.sh recuperar; then
    echo 'Recuperacao incompleta. Nao continue a demonstracao; confira o status.'
    exit 1
  fi
  exit "$codigo"
}

case "${1:-ajuda}" in
  status) bash scripts/verificar_cluster.sh ;;
  objeto) normal; bash scripts/testar_objeto.sh ;;
  recuperar)
    bash scripts/reiniciar_cluster.sh
    for _ in $(seq 1 60); do
      if normal; then echo 'Recuperado: 3 up, 3 in, todos os PGs active+clean.'; exit 0; fi
      sleep 3
    done
    echo 'Recuperacao ainda incompleta. Confira o status.'; exit 1 ;;
  falha)
    normal || { echo 'Comece com tres MONs, tres OSDs e todos os PGs active+clean.'; exit 1; }
    # Restaura os servicos existentes mesmo se a demonstracao for interrompida.
    trap recuperar_ao_sair EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    bash scripts/testar_objeto.sh
    docker stop -t 5 ceph3
    detectado=0
    for _ in $(seq 1 45); do
      if timeout 10 docker exec ceph1 ceph status -f json | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except (ValueError, OSError):
    sys.exit(1)
o=d["osdmap"]; p=d["pgmap"]
estados=p.get("pgs_by_state", [])
prontos=(p["num_pgs"]>0 and sum(x["count"] for x in estados)==p["num_pgs"]
         and all("active" in x["state_name"].split("+") and "stale" not in x["state_name"].split("+") for x in estados))
sys.exit(0 if o["num_up_osds"]==2 and len(d.get("quorum_names", []))==2 and prontos else 1)
'; then detectado=1; break; fi
      sleep 2
    done
    [[ "$detectado" == 1 ]] || { echo 'Falha nao detectada no prazo.'; exit 1; }
    bash scripts/verificar_cluster.sh
    echo 'Leitura com um no parado:'
    timeout 15 docker exec ceph1 rados -p sd get teste_script -
    echo 'Escrita com um no parado:'
    timeout 15 docker exec ceph1 sh -c 'echo "escrita com 2 nos" > /tmp/demo_m2 && rados -p sd put demo_m2 /tmp/demo_m2'
    timeout 15 docker exec ceph2 rados -p sd get demo_m2 -
    echo 'Falha demonstrada. Iniciando recuperacao automatica.' ;;
  resultados)
    python3 - <<'PY'
import csv, statistics
from pathlib import Path
for teste, arquivo, campos in (
    ('E7', 'E7/resultados.csv', ['tempo_recuperacao_s']),
    ('E9 grace 10', 'E9/resultados_grace_10.csv', ['tempo_down_s','tempo_out_s']),
    ('E9 grace 20', 'E9/resultados_grace_20.csv', ['tempo_down_s','tempo_out_s']),
):
    with (Path('evidencias') / arquivo).open() as f:
        linhas=list(csv.DictReader(f))
    print(f'\n{teste}: {len(linhas)} repeticoes')
    for campo in campos:
        valores=[float(r[campo]) for r in linhas]
        print(f'{campo}: {statistics.mean(valores):.3f} +/- {statistics.stdev(valores):.3f} s (desvio amostral)')
PY
    ;;
  *) echo 'Uso: bash scripts/demo.sh status|objeto|falha|recuperar|resultados' ;;
esac
