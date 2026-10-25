
import subprocess
import re
import csv
import statistics
from pathlib import Path

pasta = Path("evidencias/E3")
pasta.mkdir(parents=True, exist_ok=True)

resultados = []


def executar(nome, comando):
    processo = subprocess.run(
        comando,
        capture_output=True,
        text=True
    )

    saida = processo.stdout + processo.stderr
    (pasta / f"{nome}.txt").write_text(saida, encoding="utf-8")

    if processo.returncode != 0:
        print(saida[-1500:])
        raise RuntimeError(f"Erro no teste: {nome}")

    return saida


def valor(saida, campo):
    padrao = rf"^{re.escape(campo)}:\s*([0-9.]+)"
    resultado = re.search(padrao, saida, re.MULTILINE)

    if not resultado:
        raise ValueError(f"Campo nao encontrado: {campo}")

    return float(resultado.group(1))


for i in range(1, 6):
    nome = f"m2e3_{i}"
    print(f"\nExecutando repeticao {i}/5")

    base = ["docker", "exec", "ceph1", "rados", "-p", "sd"]

    escrita = executar(
        f"escrita_{i}",
        base + [
            "bench", "10", "write",
            "-b", "4096", "-t", "4",
            "--no-cleanup", "--run-name", nome
        ]
    )

    leitura = executar(
        f"leitura_{i}",
        base + [
            "bench", "5", "seq",
            "-t", "4", "--run-name", nome
        ]
    )

    resultados.append({
        "repeticao": i,
        "escrita_MB_s": valor(escrita, "Bandwidth (MB/sec)"),
        "escrita_IOPS": valor(escrita, "Average IOPS"),
        "escrita_lat_ms": valor(escrita, "Average Latency(s)") * 1000,
        "leitura_MB_s": valor(leitura, "Bandwidth (MB/sec)"),
        "leitura_IOPS": valor(leitura, "Average IOPS"),
        "leitura_lat_ms": valor(leitura, "Average Latency(s)") * 1000,
        "leitura_tempo_s": valor(leitura, "Total time run")
    })

    executar(f"limpeza_{i}", base + [
        "cleanup", "--run-name", nome
    ])

    print(f"Repeticao {i} concluida.")


arquivo = pasta / "resultados.csv"

with arquivo.open("w", newline="", encoding="utf-8") as f:
    escritor = csv.DictWriter(f, fieldnames=resultados[0].keys())
    escritor.writeheader()
    escritor.writerows(resultados)

print("\nRESULTADOS FINAIS DO E3")

for campo in resultados[0]:
    if campo == "repeticao":
        continue

    numeros = [linha[campo] for linha in resultados]

    media = statistics.mean(numeros)
    desvio = statistics.stdev(numeros)

    print(f"{campo}: media={media:.4f}, desvio={desvio:.4f}")

print(f"\nResultados salvos em: {arquivo}")
