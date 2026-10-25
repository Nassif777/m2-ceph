
#!/bin/bash
set -e

# Identificador do cluster
FSID=$(awk '/^fsid[[:space:]]*=/{print $3}' ceph.conf)

# Criar o mapa dos tres monitores
docker exec ceph1 monmaptool --create \
  --fsid "$FSID" \
  --add ceph1 172.30.0.11 \
  --add ceph2 172.30.0.12 \
  --add ceph3 172.30.0.13 \
  --enable-all-features /tmp/monmap

# Criar a chave dos monitores
docker exec ceph1 ceph-authtool \
  --create-keyring /tmp/ceph.mon.keyring \
  --gen-key -n mon. --cap mon 'allow *'

# Copiar configuracoes para os tres servidores
TEMP=$(mktemp -d)
trap 'rm -rf "$TEMP"' EXIT

docker cp ceph1:/tmp/monmap "$TEMP/monmap"
docker cp ceph1:/tmp/ceph.mon.keyring "$TEMP/ceph.mon.keyring"

for NO in ceph1 ceph2 ceph3; do
  echo "Inicializando monitor $NO"

  docker cp "$TEMP/monmap" "$NO:/tmp/monmap"
  docker cp "$TEMP/ceph.mon.keyring" "$NO:/tmp/ceph.mon.keyring"

  docker exec "$NO" sh -c "
    mkdir -p /var/lib/ceph/mon/ceph-$NO
    chown -R ceph:ceph /var/lib/ceph/mon
    chown ceph:ceph /tmp/monmap /tmp/ceph.mon.keyring
  "

  docker exec -u ceph "$NO" ceph-mon \
    --mkfs -i "$NO" \
    --monmap /tmp/monmap \
    --keyring /tmp/ceph.mon.keyring

  docker exec -d -u ceph "$NO" \
    ceph-mon -f -i "$NO"
done

echo "Inicializacao dos monitores solicitada."
