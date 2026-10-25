#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo '--- Contêineres ---'
docker compose ps

echo
echo '--- Estado do Ceph ---'
timeout 20 docker exec ceph1 ceph -s

echo
echo '--- OSDs ---'
timeout 20 docker exec ceph1 ceph osd tree

echo
echo '--- Quórum dos monitores ---'
timeout 20 docker exec ceph1 ceph quorum_status -f json | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("Líder:", d.get("quorum_leader_name", "indefinido"))
print("Monitores:", ", ".join(d.get("quorum_names", [])))
print("Epoch:", d.get("election_epoch", "-"))
'
