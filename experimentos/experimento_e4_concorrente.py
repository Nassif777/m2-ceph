
import subprocess
import threading
import time
import csv
from pathlib import Path

from datetime import datetime
PASTA = Path(__file__).resolve().parents[1] / "evidencias" / "novas_execucoes" / "E4" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
PASTA.mkdir(parents=True, exist_ok=True)

OBJETO = "contador_e4_concorrente"
TOTAL = 20

estado = {"confirmado": 0}
resultados = []
erros = []

lock = threading.Lock()
finalizado = threading.Event()


def executar(no, comando):
    p = subprocess.run(
        ["docker", "exec", no, "sh", "-c", comando],
        capture_output=True,
        text=True,
        timeout=30
    )

    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip())

    return p.stdout.strip()


# Criar o objeto inicial
executar(
    "ceph1",
    f"echo 0 > /tmp/e4.txt && rados -p sd put {OBJETO} /tmp/e4.txt"
)

inicio = time.perf_counter()


def escritor():
    try:
        for numero in range(1, TOTAL + 1):
            executar(
                "ceph1",
                f"echo {numero} > /tmp/e4.txt && "
                f"rados -p sd put {OBJETO} /tmp/e4.txt"
            )

            with lock:
                estado["confirmado"] = numero
                resultados.append({
                    "tempo_s": time.perf_counter() - inicio,
                    "operacao": "ESCRITA",
                    "no": "ceph1",
                    "valor": numero,
                    "confirmado_inicio": "",
                    "resultado": "CONFIRMADA"
                })

            time.sleep(0.08)

    except Exception as erro:
        erros.append(str(erro))
    finally:
        finalizado.set()


def leitor(no):
    adicionais = 0

    try:
        while not finalizado.is_set() or adicionais < 5:
            with lock:
                confirmado = estado["confirmado"]

            valor = int(
                executar(
                    no,
                    f"rados -p sd get {OBJETO} -"
                )
            )

            consistente = valor >= confirmado

            with lock:
                resultados.append({
                    "tempo_s": time.perf_counter() - inicio,
                    "operacao": "LEITURA",
                    "no": no,
                    "valor": valor,
                    "confirmado_inicio": confirmado,
                    "resultado": (
                        "OK" if consistente else "DESATUALIZADA"
                    )
                })

            if finalizado.is_set():
                adicionais += 1

            time.sleep(0.03)

    except Exception as erro:
        erros.append(f"{no}: {erro}")


threads = [
    threading.Thread(target=leitor, args=("ceph2",)),
    threading.Thread(target=leitor, args=("ceph3",)),
    threading.Thread(target=escritor)
]

print("Iniciando teste concorrente...")

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

resultados.sort(key=lambda r: r["tempo_s"])

arquivo = PASTA / "concorrente.csv"

with arquivo.open("w", newline="", encoding="utf-8") as f:
    campos = [
        "tempo_s", "operacao", "no",
        "valor", "confirmado_inicio", "resultado"
    ]

    escritor_csv = csv.DictWriter(f, fieldnames=campos)
    escritor_csv.writeheader()
    escritor_csv.writerows(resultados)

leituras = [r for r in resultados if r["operacao"] == "LEITURA"]
inconsistencias = sum(
    r["resultado"] == "DESATUALIZADA" for r in leituras
)
escritas = sum(
    r["operacao"] == "ESCRITA" for r in resultados
)

print("\nRESULTADO DO E4 CONCORRENTE")
print(f"Escritas confirmadas: {escritas}")
print(f"Leituras realizadas: {len(leituras)}")
print(f"Leituras desatualizadas: {inconsistencias}")
print(f"Erros de execucao: {len(erros)}")

for erro in erros:
    print("ERRO:", erro)

print(f"Resultados salvos em: {arquivo}")
