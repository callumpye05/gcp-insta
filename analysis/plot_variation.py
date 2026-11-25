
import csv
from pathlib import Path
import matplotlib.pyplot as plt

figures = Path("figures")

with open(figures / "variation.csv", newline="") as f:
    rows = list(csv.DictReader(f))

files = []

for r in rows:
    if r["file"] not in files:
        files.append(r["file"])

#graphe du debit au cours du temps
plt.figure(figsize=(11, 6))

for file in files:
    x = []
    y = []

    for r in rows:
        if r["file"] == file:
            x.append(int(r["time_start"]))
            y.append(float(r["throughput_rps"]))

    plt.plot(x, y, marker="o", label=file.replace(".csv", ""))

plt.xlabel("Temps depuis le debut du test (s)")
plt.ylabel("Requetes par seconde")
plt.title("Evolution du debit pendant les benchmarks")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
plt.tight_layout()

plt.savefig(figures / "variation_throughput.png", dpi=200)
plt.close()


#graphe de la latence client
plt.figure(figsize=(11, 6))

for file in files:
    x = []
    y = []

    for r in rows:
        if r["file"] == file:
            x.append(int(r["time_start"]))
            y.append(float(r["client_median_ms"]))

    plt.plot(x, y, marker="o", label=file.replace(".csv", ""))

plt.xlabel("Temps depuis le debut du test (s)")
plt.ylabel("Latence client mediane (ms)")
plt.title("Evolution de la latence pendant les benchmarks")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
plt.tight_layout()

plt.savefig(figures / "variation_latency.png", dpi=200)
plt.close()

print("Graphes sauvegardes")
