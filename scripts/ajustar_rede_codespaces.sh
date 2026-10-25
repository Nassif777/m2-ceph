#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Ajuste usado no Codespaces do experimento.
# Execute somente se a bridge Docker bloquear o tráfego entre contêineres.
REDE="m2-ceph_cephnet"
BRIDGE="br-$(docker network inspect -f '{{.Id}}' "$REDE" | cut -c1-12)"

echo "Bridge encontrada: $BRIDGE"
if sudo iptables-legacy -C FORWARD -i "$BRIDGE" -o "$BRIDGE" -j ACCEPT 2>/dev/null; then
  echo 'A comunicação nessa bridge já está permitida.'
else
  sudo iptables-legacy -I FORWARD 1 -i "$BRIDGE" -o "$BRIDGE" -j ACCEPT
  echo 'Regra de comunicação adicionada para essa bridge.'
fi
