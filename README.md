# M2 — Ceph · Ênfase C: detecção de falhas lentas

Laboratório de Sistemas Distribuídos: três contêineres Ceph, experimentos E1–E9
e comparação do tempo até DOWN/OUT com `osd_heartbeat_grace` de 10 e 20 segundos.

## Demonstração ao vivo

Execute dentro da pasta do projeto, com o cluster já instalado e em execução:

```bash
bash scripts/demo.sh status
bash scripts/demo.sh objeto
bash scripts/demo.sh falha
bash scripts/demo.sh resultados
```

1. **status:** mostra os nós, OSDs, quórum, líder e época.
2. **objeto:** escreve pelo ceph1, lê pelo ceph3 e mostra PG, acting e primário.
3. **falha:** para ceph3, aguarda a detecção, mostra leitura e escrita com dois
   nós e recupera automaticamente os serviços usando os dados existentes.
4. **resultados:** apresenta as cinco medições de recuperação e as duas séries
   E9, com média e desvio padrão amostral. Não repete os experimentos.

Se precisar retomar uma recuperação: `bash scripts/demo.sh recuperar`.
O fluxo de demonstração foi executado no Codespace original, com leitura e
escrita durante a falha e recuperação para 3 up, 3 in e todos os PGs active+clean.
O passo de falha pode levar alguns minutos; ensaie o tempo antes da apresentação.
O teste de objeto e a demonstração gravam apenas objetos de laboratório no pool `sd`.
Não são executados instaladores durante a apresentação.

## Ambiente

Ceph 19.2.7; Docker 29.8.0; Compose 5.5.1; Codespaces com 7,8 GiB de RAM.
Pool `sd`: `size=3`, `min_size=2`; disco simulado de 2 GiB por OSD.

| Nó | IP | Serviços | Limite de RAM |
|---|---|---|---|
| ceph1 | 172.30.0.11 | MON, MGR, OSD.0 | 1 GiB |
| ceph2 | 172.30.0.12 | MON, OSD.1 | 512 MiB |
| ceph3 | 172.30.0.13 | MON, OSD.2 | 512 MiB |

MON: portas 3300/6789; os demais endereços de serviço são anunciados pelo mapa
do cluster. Os processos usam a rede Docker `m2-ceph_cephnet`.

## Instalação e reinício

**Cluster existente:** `bash scripts/reiniciar_cluster.sh` inicia os serviços
ausentes; não registra nem formata OSDs. Aguarde todos os PGs voltarem a
`active+clean`. Um aviso de autenticação de laboratório pode manter HEALTH_WARN.

**Somente ambiente novo, sem dados anteriores:**

```bash
bash scripts/configurar_cluster.sh
```

Requer Linux, Docker Compose, Bash, Python 3, `timeout` e acesso à imagem
`quay.io/ceph/ceph:v19`. No Codespaces, o instalador aplica o ajuste de firewall
da bridge usado neste laboratório; ele exige sudo. O instalador pede confirmação
e recusa dados existentes. A instalação a partir de clone limpo foi validada em um Codespace separado em 27/10/2026 (commit `a832af0`), com `HEALTH_OK`, três MONs em quórum, três OSDs ativos e 33 PGs `active+clean`. A escrita pelo ceph1 e a leitura pelo ceph3 também foram verificadas. Registro: [`evidencias/validacao_instalacao_20261027.txt`](evidencias/validacao_instalacao_20261027.txt).

**Preserve `dados/` e `.git/`. Não execute instaladores no cluster atual,
não apague os dados e não use `docker compose down -v`.**

## Experimentos e evidências

| Teste | Evidência e execução |
|---|---|
| E1 | `evidencias/E1/`: status, topologia e quórum |
| E2 | `evidencias/E2/`: leitura, mapeamento e replicação |
| E3 | `evidencias/E3/`; `python3 experimentos/experimento_e3.py` |
| E4 | `evidencias/E4/`; `python3 experimentos/experimento_e4_concorrente.py` |
| E5 | `evidencias/complemento_20261026_192303_878620/E5_*.txt`: saídas dos testes com três, dois e um nó |
| E6 | `evidencias/complemento_20261026_192303_878620/E6_*.txt`: operações nos dois lados da partição e recuperação |
| E7 | `evidencias/E7/`; `python3 experimentos/experimento_e7.py` |
| E8 | `evidencias/E8/`: troca de líder e épocas |
| E9 | `evidencias/E9/`: cinco repetições para grace 10 e 20 |

Experimentos interrompidos ou com erros retornam código diferente de zero.
A demonstração aguarda os PGs ativos antes de testar operações com dois nós
e informa falha se a recuperação automática não concluir.

As novas execuções dos programas Python salvam em subpastas exclusivas de
`evidencias/novas_execucoes/`, preservando os registros originais. Execute apenas
um experimento por vez, sempre com o cluster recuperado.

Para repetir o E9, fora da apresentação:

```bash
bash scripts/preparar_e9.sh
python3 experimentos/experimento_e9_serie.py 10
python3 experimentos/experimento_e9_serie.py 20
bash scripts/restaurar_e9.sh
```

Se ocorrer erro, confirme a recuperação e execute a restauração antes de continuar.
A preparação configura temporariamente `mon_osd_down_out_interval=45` e desativa ajustes adaptativos;
a restauração retorna aos valores do laboratório: 120 s e grace 20 s.

## Resultados principais

| Série (n=5) | Até DOWN, média ± desvio | Até OUT, média ± desvio |
|---|---:|---:|
| Grace 10 s | 18,593 ± 2,002 s | 66,089 ± 2,701 s |
| Grace 20 s | 28,318 ± 1,442 s | 74,498 ± 2,124 s |

Recuperação E7: **15,754 ± 1,115 s**, cinco repetições, desvio amostral.
O grace 10 reduziu em aproximadamente 34% a média até DOWN neste laboratório.
A menor tolerância a atrasos pode aumentar falsos positivos, mas eles não foram
medidos. Os tempos do E9 foram observados por consultas a cada 2 s, além
do tempo dos comandos; não representam uma medição exata do timeout interno.
A série de grace 30 foi interrompida; seu CSV vazio não entra na análise.

## Limites e itens da entrega

Os três nós compartilham máquina, armazenamento e relógio. Cephx desativado,
contêineres privilegiados e discos em arquivo são escolhas apenas de laboratório.
Com três hosts e size=3, retirar um host não permite recompor três cópias em três
hosts distintos; os registros da falha longa mostram PGs ainda degradados.

Os diretórios `evidencias/E5/` e `evidencias/E6/` preservam os resumos iniciais.
As saídas completas posteriores estão em
`evidencias/complemento_20261026_192303_878620/`:

- E5: leitura e escrita funcionaram com três e dois nós; com um nó, ambas
  atingiram timeout de 15 s (código 124), assim como a consulta de status.
- E6: leitura e escrita funcionaram no lado majoritário; no nó isolado, ambas
  atingiram timeout de 15 s (código 124).
- Após cada etapa, foi confirmada a recuperação para 3 up, 3 in e todos os PGs
  active+clean. As capturas de status anteriores à confirmação mostram a transição.

O resumo antigo de E5 usa timeout de 12 s; a execução complementar documenta
o timeout de 15 s solicitado no roteiro, sem substituir os registros originais.

O relatório deve apresentar os diagramas próprios, Q1–Q14, S1–S4,
previsões/análises de E1–E9, quadro-síntese, referências, papel dos integrantes
e declaração de uso de IA, conforme o PDF do professor.
O roteiro tem indicações conflitantes de duração da demonstração; ensaie o tempo
com a equipe. Prepare vídeo de contingência e comece com o cluster em execução.

## Referências

- WEIL et al. *Ceph: A Scalable, High-Performance Distributed File System*. OSDI, 2006.
- WEIL et al. *CRUSH: Controlled, Scalable, Decentralized Placement of Replicated Data*. SC, 2006.
- Documentação oficial: https://docs.ceph.com/
