
import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

GRACE = int(sys.argv[1]) if len(sys.argv) > 1 else 20
REPETICOES = 5
from datetime import datetime
PASTA = Path(__file__).resolve().parents[1] / "evidencias" / "novas_execucoes" / "E9" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
PASTA.mkdir(parents=True, exist_ok=True)
ARQUIVO = PASTA / f"resultados_grace_{GRACE}.csv"
resultados = []


def executar(*args, limite=30):
    processo = subprocess.run(
        list(args), capture_output=True, text=True, timeout=limite
    )
    if processo.returncode != 0:
        raise RuntimeError(
            processo.stderr.strip() or processo.stdout.strip()
            or f"Comando terminou com codigo {processo.returncode}"
        )
    return processo.stdout.strip()


def ceph(*args):
    return executar("docker", "exec", "ceph1", "ceph", *args)


def estado_osd():
    dados = json.loads(ceph("osd", "dump", "-f", "json"))
    osd = next(item for item in dados["osds"] if item["osd"] == 2)
    return int(osd["up"]), int(osd["in"])


def cluster_normal():
    saida = ceph("-s")
    return (
        "3 osds: 3 up" in saida
        and "3 in" in saida
        and "33 active+clean" in saida
        and "quorum ceph1,ceph2,ceph3" in saida
    )


def configurar_grace(valor):
    processos = [
        ("ceph1", "mon.ceph1"),
        ("ceph2", "mon.ceph2"),
        ("ceph3", "mon.ceph3"),
        ("ceph1", "osd.0"),
        ("ceph2", "osd.1"),
        ("ceph3", "osd.2"),
    ]

    for no, daemon in processos:
        executar(
            "docker", "exec", no, "ceph", "daemon", daemon,
            "config", "set", "osd_heartbeat_grace", str(valor)
        )

        resposta = executar(
            "docker", "exec", no, "ceph", "daemon", daemon,
            "config", "get", "osd_heartbeat_grace"
        )

        efetivo = str(json.loads(resposta)["osd_heartbeat_grace"])

        if efetivo != str(valor):
            raise RuntimeError(
                f"{daemon}: esperado {valor}, encontrado {efetivo}"
            )

    print(f"Grace configurado e verificado: {valor} segundos.")


def salvar():
    with ARQUIVO.open("w", newline="", encoding="utf-8") as arquivo:
        campos = [
            "repeticao",
            "grace_s",
            "tempo_down_s",
            "tempo_out_s",
            "intervalo_down_out_s",
        ]

        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resultados)


def descongelar():
    pausado = executar(
        "docker", "inspect",
        "-f", "{{.State.Paused}}", "ceph3"
    )

    if pausado == "true":
        executar("docker", "unpause", "ceph3")
        print("ceph3 descongelado.")


def recuperar():
    descongelar()

    limite = time.monotonic() + 180

    while time.monotonic() < limite:
        up, dentro = estado_osd()

        if up == 1 and dentro == 0:
            ceph("osd", "in", "2")

        if cluster_normal():
            return True

        time.sleep(3)

    return False


print(f"E9 - SERIE COM GRACE = {GRACE} SEGUNDOS")

try:
    if GRACE <= 0:
        raise ValueError("O grace deve ser maior que zero.")

    if not cluster_normal():
        raise RuntimeError(
            "O cluster precisa estar em 3 up, 3 in e 33 active+clean."
        )

    for no in ("ceph1", "ceph2", "ceph3"):
        intervalo = ceph(
            "config", "show", f"mon.{no}",
            "mon_osd_down_out_interval"
        ).strip()

        if intervalo != "45":
            raise RuntimeError(
                f"mon.{no}: intervalo ate OUT e {intervalo}, nao 45."
            )

    configurar_grace(GRACE)

    for repeticao in range(1, REPETICOES + 1):
        if not cluster_normal():
            raise RuntimeError(
                "Cluster degradado antes de iniciar a repeticao."
            )

        print(f"\nREPETICAO {repeticao}/{REPETICOES}")

        tempo_down = None
        tempo_out = None

        try:
            inicio = time.monotonic()

            executar("docker", "pause", "ceph3")

            limite = time.monotonic() + 150

            while time.monotonic() < limite:
                up, dentro = estado_osd()
                tempo = time.monotonic() - inicio

                if up == 0 and tempo_down is None:
                    tempo_down = tempo
                    print(f"DOWN: {tempo_down:.2f} s")

                if dentro == 0 and tempo_out is None:
                    tempo_out = tempo
                    print(f"OUT: {tempo_out:.2f} s")

                if tempo_down is not None and tempo_out is not None:
                    break

                time.sleep(2)

        finally:
            print("Recuperando ceph3...")
            recuperado = recuperar()

        if not recuperado:
            raise RuntimeError(
                "Recuperacao incompleta. Serie interrompida."
            )

        if tempo_down is None or tempo_out is None:
            raise RuntimeError(
                "DOWN ou OUT nao observado. Serie interrompida."
            )

        resultados.append({
            "repeticao": repeticao,
            "grace_s": GRACE,
            "tempo_down_s": round(tempo_down, 3),
            "tempo_out_s": round(tempo_out, 3),
            "intervalo_down_out_s": round(
                tempo_out - tempo_down, 3
            ),
        })

        salvar()

        print("Cluster recuperado: 3 up, 3 in, 33 active+clean")

except (Exception, KeyboardInterrupt) as erro:
    print("\nEXPERIMENTO INTERROMPIDO:", erro)

finally:
    try:
        descongelar()
    except Exception as erro:
        print("ATENCAO: nao foi possivel confirmar o unpause:", erro)

    try:
        configurar_grace(20)
        print("Grace restaurado para 20 segundos.")
    except Exception as erro:
        print("ATENCAO: confira a restauracao do grace:", erro)

    salvar()


print("\nRESULTADOS DO E9")
print(f"Repeticoes concluidas: {len(resultados)}/{REPETICOES}")

if len(resultados) >= 2:
    for campo in (
        "tempo_down_s",
        "tempo_out_s",
        "intervalo_down_out_s"
    ):
        valores = [linha[campo] for linha in resultados]

        print(f"\n{campo}")
        print(f"Media: {statistics.mean(valores):.3f} s")
        print(
            f"Desvio padrao: {statistics.stdev(valores):.3f} s"
        )

print(f"\nArquivo: {ARQUIVO}")
