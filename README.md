# M2 — Sistemas Distribuídos: Cluster Ceph

**Disciplina:** Sistemas Distribuídos — Univali  
**Tema:** T2 — Sistema de armazenamento distribuído Ceph  
**Ênfase C:** Detecção de falhas lentas  
**Objetivo:** investigar replicação, consistência, quórum, eleição de monitores, partições de rede e recuperação, com medições práticas.

> **Ambiente exclusivamente acadêmico.** A autenticação Ceph foi desativada e os contêineres usam `privileged: true`. Não utilizar esta configuração em produção nem expor os serviços à internet.

## 1. Ambiente utilizado

Os testes foram executados em **GitHub Codespaces**, em Linux x86_64, com cerca de 7,8 GiB de RAM.

| Componente | Versão / configuração observada |
|---|---|
| Ceph | 19.2.7 — Squid (`quay.io/ceph/ceph:v19`) |
| Docker | 29.8.0 |
| Docker Compose | v5.5.1 |
| Rede Docker | `m2-ceph_cephnet` — `172.30.0.0/24` |
| Pool de objetos | `sd`, `size = 3`, `min_size = 2` |
| Armazenamento por OSD | BlueStore, bloco configurado para 2 GiB |

### Topologia

| Contêiner | IP | Serviços | Limite de memória |
|---|---|---|---|
| `ceph1` | `172.30.0.11` | MON, MGR, OSD.0 | 1 GiB |
| `ceph2` | `172.30.0.12` | MON, OSD.1 | 512 MiB |
| `ceph3` | `172.30.0.13` | MON, OSD.2 | 512 MiB |

O cluster tem três monitores, três OSDs e um Manager. Os monitores mantêm o mapa e o quórum. Os OSDs armazenam os objetos e suas réplicas.

## 2. Arquivos do projeto

- `docker-compose.yml`: define os três contêineres, os limites de memória, os volumes e a rede.
- `ceph.conf`: configuração inicial do cluster.
- `iniciar_mons.sh`: cria o mapa e inicializa os três monitores **somente na primeira instalação**.
- `iniciar_mgr.sh`: inicializa o Manager **somente na primeira instalação**.
- `iniciar_osds.sh`: registra e formata os três OSDs **somente na primeira instalação**.
- `experimento_e3.py`, `experimento_e4.py`, `experimento_e4_concorrente.py`, `experimento_e7.py`, `experimento_e9_teste.py`, `experimento_e9_serie.py`: scripts dos experimentos.
- `evidencias/`: arquivos CSV, TXT e JSON coletados ou organizados após as execuções.
- `dados/`: diretórios persistentes dos serviços Ceph; **não publicar no Git nem excluir durante a recuperação**.

## 3. Primeira instalação em um ambiente vazio

**Pré-requisitos:** Linux com Docker, Docker Compose, espaço para a imagem Ceph e suporte à execução de contêineres privilegiados. Este procedimento foi executado no Codespaces; a instalação do zero em outros computadores não foi validada.

Dentro da pasta do projeto:

```bash
docker compose up -d
docker compose ps
```

**Atenção:** no Codespaces utilizado, o Docker bloqueou inicialmente a comunicação entre contêineres da mesma bridge. Foi necessário permitir **somente** tráfego de ida e volta nessa interface. Aplicar o ajuste abaixo apenas se houver esse problema no ambiente de laboratório:

```bash
BR="br-$(docker network inspect -f '{{.Id}}' m2-ceph_cephnet | cut -c1-12)"
sudo iptables-legacy -C FORWARD -i "$BR" -o "$BR" -j ACCEPT \
  || sudo iptables-legacy -I FORWARD 1 -i "$BR" -o "$BR" -j ACCEPT
```

Na **primeira inicialização, com `dados/` ainda não inicializado**, executar:

```bash
bash iniciar_mons.sh
# Aguardar a formação de quórum. Consultar o estado:
timeout 20 docker exec ceph1 ceph -s

bash iniciar_mgr.sh
bash iniciar_osds.sh

# Criar o pool de testes, uma única vez:
docker exec ceph1 ceph osd pool create sd 32
docker exec ceph1 ceph osd pool application enable sd rados

# Verificação final:
docker exec ceph1 ceph -s
docker exec ceph1 ceph osd tree
```

**Não executar novamente `iniciar_mons.sh` ou `iniciar_osds.sh` se o cluster já tiver sido inicializado.** Eles fazem operações de criação e formatação, não são scripts de reinício seguros.

O resultado saudável esperado inclui três monitores em quórum, `3 osds: 3 up, 3 in` e `33 active+clean`. Um aviso de autenticação pode aparecer no laboratório devido à configuração simplificada.

## 4. Reinício de contêineres existentes

O `docker-compose.yml` mantém cada contêiner ativo com `sleep infinity`; **os serviços MON, MGR e OSD não são reiniciados automaticamente**. Se os contêineres tiverem sido desligados, iniciar os contêineres e reativar somente os processos ausentes, sem recriar ou reformatar os dados:

```bash
docker compose up -d

# Verificar processos em cada contêiner:
for no in ceph1 ceph2 ceph3; do
  echo "=== $no ==="
  docker exec "$no" sh -c "ps -ef | grep -E '[c]eph-(mon|osd|mgr)'"
done
```

Se necessário, e **apenas se o respectivo processo não estiver em execução**, usar:

```bash
docker exec -d -u ceph ceph1 ceph-mon -f -i ceph1
docker exec -d -u ceph ceph2 ceph-mon -f -i ceph2
docker exec -d -u ceph ceph3 ceph-mon -f -i ceph3

docker exec -d -u ceph ceph1 ceph-mgr -f -i ceph1

docker exec -d -u ceph ceph1 ceph-osd -f -i 0
docker exec -d -u ceph ceph2 ceph-osd -f -i 1
docker exec -d -u ceph ceph3 ceph-osd -f -i 2
```

Verificar `docker exec ceph1 ceph -s` e `docker exec ceph1 ceph osd tree`. **Não** executar os comandos de inicialização/`--mkfs` para recuperar processos. **Não** remover os diretórios `dados/` nem usar comandos que apaguem volumes/dados.

## 5. Teste rápido de escrita e leitura

```bash
docker exec ceph1 sh -c 'echo "Teste Ceph M2" > /tmp/teste.txt && rados -p sd put exemplo_readme /tmp/teste.txt'
docker exec ceph3 rados -p sd get exemplo_readme -
docker exec ceph1 ceph osd map sd exemplo_readme
```

Esses comandos demonstram um cliente gravando a partir de um nó, outro cliente lendo e o mapeamento do objeto para um PG e seus OSDs.

## 6. Experimentos executados

| Experimento | O que foi observado | Evidências |
|---|---|---|
| E1 — Topologia | 3 MONs, 3 OSDs, 1 MGR | `evidencias/E1/topologia.txt` |
| E2 — Operação | Escrita/leitura e mapeamento de objeto | `evidencias/E2/operacoes.txt` |
| E3 — Replicação/desempenho | Cinco testes de escrita e leitura | `evidencias/E3/` |
| E4 — Consistência | Leituras sequenciais e concorrentes sem regressões observadas | `evidencias/E4/` |
| E5 — Falha e quórum | Um nó indisponível: leitura/escrita; dois: timeout | `evidencias/E5/resultados.txt` |
| E6 — Partição de rede | Lado majoritário disponível; leitura na minoria: timeout | `evidencias/E6/resultados.txt` |
| E7 — Recuperação | Cinco tempos de recuperação | `evidencias/E7/resultados.csv` |
| E8 — Coordenação | Após suspender líder MON, eleição `ceph1` → `ceph2`, epoch 52 → 54 | `evidencias/E8/` |
| E9 — Falhas lentas | Cinco execuções com grace de 10 s e cinco com 20 s | `evidencias/E9/` |

Os registros de E5 e E6 em TXT foram **transcritos dos resultados observados no terminal**, não são logs brutos capturados automaticamente. Os testes com grace de 30 s foram interrompidos durante a recuperação e **não** constituem uma série completa.

### Principais medições

| Medição | Resultado |
|---|---:|
| E7 — tempo médio de recuperação | 15,754 s (desvio 1,115 s) |
| E9 — grace 10 s, média até DOWN | 18,593 s (desvio 2,002 s) |
| E9 — grace 10 s, média até OUT | 66,089 s (desvio 2,701 s) |
| E9 — grace 20 s, média até DOWN | 28,318 s (desvio 1,442 s) |
| E9 — grace 20 s, média até OUT | 74,498 s (desvio 2,124 s) |

O E9 usa `docker pause ceph3` para simular uma falha lenta. Houve redução aproximada de 34% no tempo médio até DOWN ao passar de 20 s para 10 s de grace. O possível aumento de falsos positivos com configurações mais agressivas foi discutido teoricamente, **não medido diretamente**.

### Reproduzir o E9 com parâmetros experimentais

**Apenas em cluster saudável e sob acompanhamento.** O script `experimento_e9_serie.py` exige intervalo efetivo de `45` s nos três monitores e restaura o grace de `20` s ao terminar. Configurar o intervalo experimental e desativar os ajustes automáticos diretamente em cada monitor:

```bash
for no in ceph1 ceph2 ceph3; do
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_down_out_interval 45
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_heartbeat_grace false
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_down_out_interval false
done

python3 experimento_e9_serie.py 10
python3 experimento_e9_serie.py 20
```

Conferir a recuperação do cluster antes de iniciar uma nova série. Depois, restaurar os valores usados originalmente:

```bash
for no in ceph1 ceph2 ceph3; do
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_down_out_interval 120
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_heartbeat_grace true
  docker exec "$no" ceph daemon "mon.$no" config set mon_osd_adjust_down_out_interval true
done

docker exec ceph1 ceph -s
```

## 7. Limitações e segurança

- Os três nós compartilham a mesma máquina virtual e o mesmo relógio; o experimento não equivale a três servidores físicos independentes.
- Os discos dos OSDs são simulados por armazenamento local; não reproduzem necessariamente latência e falhas reais de discos físicos.
- A autenticação foi desabilitada somente para simplificar o laboratório.
- A inicialização dos daemons é manual; os scripts iniciais ainda **não são idempotentes** e o processo completo não foi revalidado a partir de uma nova instalação limpa.
- Uma execução adicional do E9 com grace de 30 s foi interrompida porque o processo do OSD.2 deixou de funcionar durante a recuperação. O processo foi reiniciado manualmente e o cluster voltou a `active+clean`.

## 8. Referências básicas

- WEIL, S. A. et al. *Ceph: A Scalable, High-Performance Distributed File System*. OSDI, 2006.
- WEIL, S. A. et al. *CRUSH: Controlled, Scalable, Decentralized Placement of Replicated Data*. SC, 2006.
- Documentação oficial do Ceph: https://docs.ceph.com/

**Status:** README descritivo do laboratório executado. Antes de declarar reprodutibilidade completa, testar a instalação a partir de diretórios vazios em ambiente isolado, sem tocar nos dados do experimento atual.
