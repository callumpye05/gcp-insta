import csv
import matplotlib.pyplot as plt

followers= []
before =[]
after =[]
with open("figures/fig3.csv", newline="") as file:
    rows = csv.DictReader(file)
    for row in rows:
        followers.append(int(row["F"]))
        before.append(float(row["latence_avant_ms"]))
        after.append(float(row["latence_apres_ms"]))

plt.figure(figsize=(9, 5))

plt.plot(followers,before, marker="o", label="Originale")
plt.plot(followers, after, marker="o",label="Optimisée")

plt.xlabel("Nombre de comptes suivis(F)")
plt.ylabel("Temps serveur médian(ms)")
plt.title("Fig3 Avant et après optimisation")

plt.xticks(range(5, 101, 5), rotation=45)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("figures/fig3.png", dpi=150, bbox_inches="tight")
print("Figure créer :figures/fig3.png")