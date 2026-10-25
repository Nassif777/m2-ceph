# M2 - Ceph (Sistemas Distribuídos)

Trabalho da disciplina de Sistemas Distribuídos da Univali.

**Tema:** T2 - Ceph  
**Ênfase:** C - Detecção de falhas lentas

Neste projeto montei um cluster Ceph com três nós no Docker e fiz testes de replicação, consistência, falha de nós, partição de rede, eleição de monitores e recuperação. A parte de aprofundamento compara o tempo de detecção de falhas usando diferentes valores de `osd_heartbeat_grace`.

## Ambiente

Os testes foram feitos no GitHub Codespaces, com Linux e aproximadamente 7,8 GiB de RAM.

- Ceph 19.2.7 (Squid)
- Docker 29.8.0 e Docker Compose 5.5.1
- Rede `172.30.0.0/24`
- Pool `sd`, com `size = 3` e `min_size = 2`

| Nó | IP | Processos | Limite de RAM |
|---|---|---|---|
| ceph1 | 172.30.0.11 | MON, MGR e OSD.0 | 1 GiB |
| ceph2 | 172.30.0.12 | MON e OSD.1 | 512 MiB |
| ceph3 | 172.30.0.13 | MON e OSD.2 | 512 MiB |

Os diretórios `dados/` armazenam o estado dos serviços, mas **não estão no Git**. Os comandos de instalação e os de reinício são diferentes justamente para não formatar OSDs existentes.

## Organização dos arquivos

- `docker-compose.yml` e `ceph.conf`: contêineres e configuração do Ceph.
- `iniciar_mons.sh`, `iniciar_mgr.sh` e `iniciar_osds.sh`: criação dos serviços na primeira instalação.
- `scripts/`: comandos para instalar, verificar ou reiniciar o laboratório.
- `experimento_e3.py` até `experimento_e9_serie.py`: programas usados nos testes.
- `evidencias/`: saídas de terminal, medições e resumos dos experimentos.

## Como usar

### Cluster que já foi instalado

Para consultar o estado:

```bash
bash scripts/verificar_cluster.sh
```

Se os contêineres foram desligados e os dados continuam em `dados/`, é possível iniciar os processos que estiverem ausentes:

```bash
bash scripts/reiniciar_cluster.sh
```

Esse script não cria nem formata OSDs. Não use `docker compose down -v` e não apague `dados/` se quiser preservar o cluster.

Para fazer uma operação simples de escrita e leitura:

```bash
bash scripts/testar_objeto.sh
```

### Instalação nova

Em uma pasta sem dados anteriores do Ceph, com Docker e Compose instalados:

```bash
docker compose up -d
```

No Codespaces utilizado houve bloqueio de comunicação na bridge Docker. Se isso também acontecer, o ajuste de rede empregado no laboratório está em:

```bash
bash scripts/ajustar_rede_codespaces.sh
```

Esse ajuste modifica uma regra de firewall do ambiente e só deve ser usado quando necessário.

Com a rede funcionando, a instalação inicial pode ser iniciada por:

```bash
bash scripts/configurar_cluster.sh
```

O script pede confirmação antes de criar os MONs, MGR e OSDs e bloqueia a instalação se encontrar dados existentes. **Não execute esse comando no cluster atual.** Os scripts de inicialização originais não foram feitos para rodar duas vezes sobre os mesmos dados.

> Observação: o ambiente do trabalho foi montado e testado no Codespaces original. A instalação inteira a partir de um clone limpo ainda precisa ser validada em outro ambiente. Os scripts desta reorganização também precisam dessa validação.

## Experimentos

| Teste | O que foi observado | Arquivos |
|---|---|---|
| E1 | Topologia e quórum | `evidencias/E1/` |
| E2 | Escrita, leitura e localização de objeto | `evidencias/E2/` |
| E3 | Replicação e desempenho (5 medições) | `evidencias/E3/` |
| E4 | Leituras após escritas e operações concorrentes | `evidencias/E4/` |
| E5 | Quórum com um e dois nós desligados | `evidencias/E5/` |
| E6 | Comportamento durante partição de rede | `evidencias/E6/` |
| E7 | Tempo de recuperação (5 medições) | `evidencias/E7/` |
| E8 | Eleição de líder entre monitores | `evidencias/E8/` |
| E9 | Detecção de falhas com diferentes heartbeats | `evidencias/E9/` |

Os arquivos de E5 e E6 são resumos das saídas obtidas durante os testes, não logs brutos coletados automaticamente.

### Resultado principal do E9

Foi usado `docker pause ceph3` para simular um nó que parou de responder. O tempo foi medido desde a suspensão até o estado `down` e depois até `out`.

| Parâmetro | Média até DOWN | Média até OUT | Repetições |
|---|---:|---:|---:|
| Grace de 10 s | 18,593 s | 66,089 s | 5 |
| Grace de 20 s | 28,318 s | 74,498 s | 5 |

No laboratório, a detecção com grace de 10 s foi cerca de 34% mais rápida. A contrapartida esperada é uma tolerância menor a atrasos de rede, com possível aumento de falsos positivos. **Não houve medição direta de falsos positivos.**

A tentativa adicional com grace de 30 s foi interrompida durante a recuperação porque o processo OSD.2 parou. O cluster foi recuperado depois, mas essa tentativa não entrou nas médias.

Para preparar os parâmetros temporários e rodar novamente o E9, **somente em um cluster saudável**:

```bash
bash scripts/preparar_e9.sh
python3 experimento_e9_serie.py 10
# ou: python3 experimento_e9_serie.py 20
bash scripts/restaurar_e9.sh
```

Não rode esses experimentos em paralelo. Confira se o Ceph voltou a `3 up`, `3 in` e `active+clean` antes de cada nova execução. Se ocorrer um erro, recupere o cluster antes de continuar.

## Limitações

Os três nós estavam na mesma máquina virtual, usando a mesma infraestrutura física e relógio. Por isso, os resultados não representam um cluster instalado em três servidores independentes. Os discos dos OSDs também foram simulados com armazenamento local.

A autenticação do Ceph foi desativada para simplificar os testes, e os contêineres usam `privileged: true`. **Essa configuração é apenas de laboratório e não deve ser exposta à internet ou usada em produção.**

## Referências

- WEIL, S. A. et al. *Ceph: A Scalable, High-Performance Distributed File System*. OSDI, 2006.
- WEIL, S. A. et al. *CRUSH: Controlled, Scalable, Decentralized Placement of Replicated Data*. SC, 2006.
- [Documentação do Ceph](https://docs.ceph.com/).
