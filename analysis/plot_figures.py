
import csv
import statistics
from pathlib import Path
from collections import defaultdict
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

figures = Path("figures")
file = figures / "fig2_summary.csv"

#recupere les resultats des benchmark
with open(file, newline="") as f:
    rows = list(csv.DictReader(f))

#on regroupe les tests avec les meme valeurs N et C
groupes= defaultdict(list)

for r in rows:
    n =int(r["instances_configured"])
    c = int(r["clients"])

    #pour N=1 et C=16 on utilise seulement run1.csv car c'était la tentative initial
    if n ==1 and c == 16:
        if r["filename"] != "run1.csv":
            continue

    groupes[(n,c)].append(r)

data = []

for (n,c), essais in sorted(groupes.items()):
    debits = []
    latences = []
    moyennes = []
    predictions = []

    for r in essais:
        debits.append(float(r["throughput_rps"]))
        latences.append(float(r["client_median_ms"]))
        moyennes.append(float(r["client_mean_ms"]))
        predictions.append(float(r["little_prediction_ms"]))

    data.append({
        "instances": n,
        "clients": c,
        "throughput_rps": statistics.mean(debits),
        "latency_median_ms": statistics.mean(latences),
        "latency_mean_ms": statistics.mean(moyennes),
        "little_prediction_ms": statistics.mean(predictions),
        "nb_tests": len(essais)
    })


def save_csv(name, columns):
    with open(figures / name, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for r in data:
            line= {}
            for col in columns:
                line[col] = r[col]
            writer.writerow(line)


#les csv utilises pour generer les deux figures
save_csv("fig2a.csv", [
    "instances", "clients", "throughput_rps", "nb_tests"
])

save_csv("fig2b.csv", [
    "instances", "clients", "latency_median_ms",
    "latency_mean_ms", "little_prediction_ms", "nb_tests"
])


#figure 2a : debit en fonction de la concurrence
plt.figure(figsize=(9,5))

for n in [1,2,4]:
    valeurs= [r for r in data if r["instances"] == n]
    x = [r["clients"] for r in valeurs]
    y = [r["throughput_rps"] for r in valeurs]
    plt.plot(x,y,marker="o",label=f"{n} instance(s)")

plt.xscale("log",base=2)
plt.xticks([1,2,4,8,16,32,64], ["1","2","4","8","16","32","64"])
plt.xlabel("Nombre d'utilisateurs Locust (C)")
plt.ylabel("Debit (requetes/s)")
plt.title("Fig. 2a - Debit selon la concurrence")
plt.grid(True,alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(figures /"fig2a.png", dpi=200)
plt.close()

print("Fig 2a sauvegardee")

#fig 2b latence et prediction de Little
plt.figure(figsize=(9,5))

for n in [1,2,4]:
    valeurs= [r for r in data if r["instances"] == n]

    x =[r["clients"] for r in valeurs]
    y= [r["latency_median_ms"] for r in valeurs]
    little = [r["little_prediction_ms"] for r in valeurs]
    ligne, = plt.plot(x,y,marker="o",label=f"N={n} mediane")
    
    #meme couleur mais en pointille pour la prediction
    plt.plot(x,little,linestyle="--",color=ligne.get_color(),
             label=f"N={n} Little")

plt.xscale("log",base=2)
plt.xticks([1,2,4,8,16,32,64],["1","2","4","8","16","32","64"])
plt.xlabel("Nombre d'utilisateurs Locust (C)")
plt.ylabel("Latence (ms)")
plt.title("Fig. 2b - Latence et loi de Little")
plt.grid(True,alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(figures /"fig2b.png", dpi=200)
plt.close()
print("la fig 2b est sauvegardee")
