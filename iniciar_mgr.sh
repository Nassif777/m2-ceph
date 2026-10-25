
#!/bin/bash
set -e

echo "Configurando o Ceph Manager..."

# Criar o diretorio do Manager
docker exec ceph1 mkdir -p /var/lib/ceph/mgr/ceph-ceph1

# Criar a chave de autenticacao do Manager
docker exec ceph1 ceph auth get-or-create mgr.ceph1 \
  mon 'allow profile mgr' \
  osd 'allow *' \
  mds 'allow *' \
  -o /var/lib/ceph/mgr/ceph-ceph1/keyring

# Ajustar as permissoes
docker exec ceph1 chown -R ceph:ceph /var/lib/ceph/mgr/ceph-ceph1

# Iniciar o Manager
docker exec -d -u ceph ceph1 ceph-mgr -f -i ceph1

echo "Inicializacao do Manager solicitada."
