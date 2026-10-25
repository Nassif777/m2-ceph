
import subprocess
import json
import time
import csv
from pathlib import Path

PASTA = Path("evidencias/E9")
PASTA.mkdir(parents=True, exist_ok=True)


def executar(*args, limite=30):
    p = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=limite
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip()


def estado_osd():
    saida = executar(
        "docker", "exec", "ceph1",
        "ceph", "osd", "dump", "-f", "json"
    )
    dados = json.loads(saida)

    osd = next(
        item for item in dados["osds"]
        if item["osd"] == 2
    )

    return int(osd["up"]), int(osd["in"])


def cluster_normal():
    saida = executar(
        "docker", "exec", "ceph1", "ceph", "-s"
    )

    return (
        "3 osds: 3 up" in saida
        and "3 in" in saida
        and "33 active+clean" in saida
    )


if not cluster_normal():
    raise SystemExit(
        "Cluster nao esta normal. Experimento cancelado."
    )

print("E9 - DETECCAO DE FALHAS LENTAS")
print("Grace: 20 segundos")
print("Intervalo down/out: 45 segundos")

registros = []
tempo_down = None
tempo_out = None
inicio = None

try:
    print("\nSuspendendo ceph3...")
    inicio = time.monotonic()

    executar("docker", "pause", "ceph3")

    limite_teste = time.monotonic() + 180

    while time.monotonic() < limite_teste:
        up, dentro = estado_osd()
        tempo = time.monotonic() - inicio

        if up == 0 and tempo_down is None:
            tempo_down = tempo
            print(f"OSD.2 DOWN em {tempo:.2f} segundos")

            registros.append({
                "evento": "down",
                "tempo_s": round(tempo, 3)
            })

        if dentro == 0 and tempo_out is None:
            tempo_out = tempo
            print(f"OSD.2 OUT em {tempo:.2f} segundos")

            registros.append({
                "evento": "out",
                "tempo_s": round(tempo, 3)
            })

        if tempo_down is not None and tempo_out is not None:
            break

        time.sleep(2)

except Exception as erro:
    print("Problema durante o teste:", erro)

finally:
    print("\nRestaurando ceph3...")

    try:
        pausado = executar(
            "docker", "inspect",
            "-f", "{{.State.Paused}}", "ceph3"
        )

        if pausado == "true":
            executar("docker", "unpause", "ceph3")

        print("ceph3 descongelado.")

    except Exception as erro:
        print("ATENCAO: verificar ceph3:", erro)

    with (PASTA / "teste_inicial.csv").open(
        "w", newline="", encoding="utf-8"
    ) as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=["evento", "tempo_s"]
        )
        escritor.writeheader()
        escritor.writerows(registros)


print("\nRESULTADO E9")

print(
    "Tempo ate DOWN:",
    f"{tempo_down:.2f} s" if tempo_down is not None
    else "Nao observado"
)

print(
    "Tempo ate OUT:",
    f"{tempo_out:.2f} s" if tempo_out is not None
    else "Nao observado"
)

if tempo_down is not None and tempo_out is not None:
    print(
        "Intervalo DOWN -> OUT:",
        f"{tempo_out - tempo_down:.2f} s"
    )

print("\nVerificando recuperacao...")

limite_recuperacao = time.monotonic() + 180
recuperado = False

while time.monotonic() < limite_recuperacao:
    try:
        up, dentro = estado_osd()

        if up == 1 and dentro == 0:
            executar(
                "docker", "exec", "ceph1",
                "ceph", "osd", "in", "2"
            )
            print("OSD.2 marcado novamente como IN.")

        if cluster_normal():
            recuperado = True
            break

    except Exception as erro:
        print("Verificacao:", erro)

    time.sleep(3)

if recuperado:
    print("Cluster recuperado: 3 up, 3 in, 33 active+clean")
else:
    print("ATENCAO: recuperacao incompleta. Verificar ceph -s.")

print("Resultados salvos em evidencias/E9/teste_inicial.csv")
