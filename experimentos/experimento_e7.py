
import subprocess
import time
import csv
import json
import statistics
from pathlib import Path

PASTA = Path("evidencias/E7")
PASTA.mkdir(parents=True, exist_ok=True)

resultados = []


def comando(args, limite=20):
    p = subprocess.run(
        args, capture_output=True, text=True, timeout=limite
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout


def status_cluster():
    return comando(["docker", "exec", "ceph1", "ceph", "-s"])


def osd2_ativo():
    saida = comando([
        "docker", "exec", "ceph1", "ceph",
        "osd", "tree", "-f", "json"
    ])
    dados = json.loads(saida)
    return any(
        n.get("id") == 2 and n.get("status") == "up"
        for n in dados["nodes"]
    )


def cluster_recuperado():
    status = status_cluster()
    return (
        "3 osds: 3 up" in status
        and "3 in" in status
        and "33 active+clean" in status
        and "quorum ceph1,ceph2,ceph3" in status
    )


def religar_ceph3():
    estado = comando([
        "docker", "inspect", "-f", "{{.State.Running}}", "ceph3"
    ]).strip()

    if estado != "true":
        comando(["docker", "start", "ceph3"], 40)

    processos = comando([
        "docker", "exec", "ceph3", "ps", "-ef"
    ])

    if "ceph-mon -f -i ceph3" not in processos:
        comando([
            "docker", "exec", "-d", "-u", "ceph",
            "ceph3", "ceph-mon", "-f", "-i", "ceph3"
        ])

    if "ceph-osd -f -i 2" not in processos:
        comando([
            "docker", "exec", "-d", "-u", "ceph",
            "ceph3", "ceph-osd", "-f", "-i", "2"
        ])


if not cluster_recuperado():
    raise RuntimeError("O cluster precisa estar recuperado antes do E7.")

try:
    for i in range(1, 6):
        print(f"\nREPETICAO {i}/5")

        # Simular falha de um servidor
        comando(["docker", "stop", "-t", "5", "ceph3"], 30)
        print("ceph3 desligado.")

        # Confirmar que o Ceph detectou a falha
        limite = time.monotonic() + 90

        while osd2_ativo():
            if time.monotonic() > limite:
                raise RuntimeError("Falha nao detectada em 90 segundos.")
            time.sleep(2)

        print("Falha detectada pelo Ceph.")

        # Medir a recuperacao a partir do reinicio
        inicio = time.perf_counter()
        religar_ceph3()

        limite = time.monotonic() + 180

        while not cluster_recuperado():
            if time.monotonic() > limite:
                raise RuntimeError("Recuperacao excedeu 180 segundos.")
            time.sleep(2)

        tempo = time.perf_counter() - inicio

        resultados.append({
            "repeticao": i,
            "tempo_recuperacao_s": round(tempo, 3)
        })

        (PASTA / f"status_{i}.txt").write_text(
            status_cluster(), encoding="utf-8"
        )

        print(f"Cluster recuperado em {tempo:.3f} segundos.")

except (Exception, KeyboardInterrupt) as erro:
    print(f"\nExperimento interrompido: {erro}")
    print("Tentando religar o ceph3...")
    try:
        religar_ceph3()
    except Exception as erro_recuperacao:
        print(f"Verificar manualmente ceph3: {erro_recuperacao}")

finally:
    if resultados:
        with (PASTA / "resultados.csv").open(
            "w", newline="", encoding="utf-8"
        ) as arquivo:
            escritor = csv.DictWriter(
                arquivo,
                fieldnames=["repeticao", "tempo_recuperacao_s"]
            )
            escritor.writeheader()
            escritor.writerows(resultados)

        tempos = [r["tempo_recuperacao_s"] for r in resultados]

        print("\nRESULTADOS DO E7")
        for r in resultados:
            print(
                f"Repeticao {r['repeticao']}: "
                f"{r['tempo_recuperacao_s']:.3f} s"
            )

        if len(tempos) >= 2:
            print(f"Media: {statistics.mean(tempos):.3f} s")
            print(
                f"Desvio padrao: "
                f"{statistics.stdev(tempos):.3f} s"
            )

        print(f"Medicoes concluidas: {len(resultados)}/5")
