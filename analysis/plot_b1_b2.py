
import csv
from pathlib import Path
from collections import defaultdict
from statistics import median
import matplotlib.pyplot as plt

#les 4 fichiers
files = {"B1 - Essai 1": "worker4thread4_c16.csv","B1 - Essai 2": "worker4thread4_c16_repeat.csv","B2 - Essai 1": "b2cpu_c16_run1.csv","B2 - Essai 2": "b2cpu_c16_run2.csv",}

raw_dir = Path("raw/part3")
output =Path("figures/part-3-second-bottleneck")
output.mkdir(exist_ok=True)

interval =15  #regroupement des mesures par 15 secondes
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8),sharex=True)

for label, filename in files.items():
    with open(raw_dir / filename, newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: float(r["T_START"]))
    start = float(rows[0]["T_START"])
    buckets = defaultdict(list)
    for row in rows:
        if row["STATUS"] != "200":
            continue
        elapsed = float(row["T_START"]) - start
        bucket = int(elapsed // interval)
        buckets[bucket].append(float(row["LATENCY_MS"]))
    times = []
    throughputs = []
    latencies = []
    for bucket, values in sorted(buckets.items()):
        times.append(bucket* interval + interval / 2)
        throughputs.append(len(values) / interval)
        latencies.append(median(values))
    ax1.plot(times, throughputs, marker="o", label=label)
    ax2.plot(times, latencies, marker="o", label=label)
ax1.set_title("Débit selon la classe d'instance")
ax1.set_ylabel("Requêtes par seconde")
ax1.grid(alpha=0.3)
ax1.legend()
ax2.set_title("Latence client médiane")
ax2.set_xlabel("Temps écoulé (secondes)")
ax2.set_ylabel("Latence (ms)")
ax2.grid(alpha=0.3)
ax2.legend()
fig.suptitle("Comparaison B1 / B2 - 4 workers, 4 threads, C=16")
plt.tight_layout()
plt.savefig(output / "comparaison_b1_b2.png", dpi=150)
plt.close()
print("Figure créée : figures/part-3-second-bottleneck/comparaison_b1_b2.png")
