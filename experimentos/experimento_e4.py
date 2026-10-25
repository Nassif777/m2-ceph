
import subprocess
import csv
from pathlib import Path

pasta = Path("evidencias/E4")
pasta.mkdir(parents=True, exist_ok=True)

resultados = []

def executar(no, comando):
    resultado = subprocess.run(
        ["docker", "exec", no, "sh", "-c", comando],
        capture_output=True,
        text=True,
        timeout=30,
        check=True
    )
    return resultado.stdout.strip()

print("INICIANDO EXPERIMENTO E4")
print("Teste de leitura apos escrita\n")

for numero in range(1, 21):

    # Escrever pelo primeiro servidor
    executar(
        "ceph1",
        f"echo {numero} > /tmp/e4.txt && "
        "rados -p sd put contador_e4 /tmp/e4.txt"
    )

    # Ler pelos outros dois servidores
    valor2 = executar(
        "ceph2",
        "rados -p sd get contador_e4 -"
    )

    valor3 = executar(
        "ceph3",
        "rados -p sd get contador_e4 -"
    )

    correto = (
        valor2 == str(numero)
        and valor3 == str(numero)
    )

    resultados.append({
        "escrita": numero,
        "leitura_ceph2": valor2,
        "leitura_ceph3": valor3,
        "consistente": correto
    })

    print(
        f"Teste {numero:02d}: "
        f"Escrito={numero} | "
        f"ceph2={valor2} | "
        f"ceph3={valor3} | "
        f"{'OK' if correto else 'FALHOU'}"
    )

with open(pasta / "resultados.csv", "w", newline="") as arquivo:
    escritor = csv.DictWriter(
        arquivo,
        fieldnames=resultados[0].keys()
    )
    escritor.writeheader()
    escritor.writerows(resultados)

total = len(resultados)
sucessos = sum(r["consistente"] for r in resultados)

print("\nRESULTADO FINAL DO E4")
print(f"Escritas realizadas: {total}")
print(f"Leituras realizadas: {total * 2}")
print(f"Testes consistentes: {sucessos}/{total}")
print(f"Inconsistencias: {total - sucessos}")
print("Resultados salvos em evidencias/E4/resultados.csv")
