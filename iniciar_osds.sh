
#!/bin/bash
set -euo pipefail

echo "Iniciando configuracao dos OSDs..."

for NO in ceph1 ceph2 ceph3; do
    echo "--------------------------------"
    echo "Configurando armazenamento em $NO"

    # Gerar identificador e chave do novo OSD
    UUID=$(cat /proc/sys/kernel/random/uuid)
    CHAVE=$(docker exec ceph1 ceph-authtool --gen-print-key)

    # Registrar o OSD no cluster
    ID=$(printf '{"cephx_secret":"%s"}' "$CHAVE" |
        docker exec -i ceph1 ceph osd new "$UUID" -i -)

    echo "OSD criado: osd.$ID"

    # Criar diretorio de armazenamento
    docker exec "$NO" mkdir -p "/var/lib/ceph/osd/ceph-$ID"

    # Criar chave local do OSD
    docker exec "$NO" ceph-authtool \
        --create-keyring "/var/lib/ceph/osd/ceph-$ID/keyring" \
        --name "osd.$ID" \
        --add-key "$CHAVE"

    # Ajustar permissoes
    docker exec "$NO" chown -R ceph:ceph \
        "/var/lib/ceph/osd/ceph-$ID"

    # Inicializar o armazenamento BlueStore
    docker exec -u ceph "$NO" ceph-osd \
        -i "$ID" --mkfs --osd-uuid "$UUID"

    # Iniciar o servico
    docker exec -d -u ceph "$NO" \
        ceph-osd -f -i "$ID"

    echo "Inicializacao do osd.$ID solicitada."
done

echo "--------------------------------"
echo "Configuracao dos OSDs concluida."
