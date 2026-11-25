
import csv
from pathlib import Path
import matplotlib.pyplot as plt

figures =Path("figures")

#lecture des resultats de f
with open(figures / "fig1b.csv", newline="") as f:
    rows =list(csv.DictReader(f))

x =[]
server = []
client = []

for r in rows:
    x.append(int(r["F"]))
    server.append(float(r["server_median_ms"]))
    client.append(float(r["client_median_ms"]))

#fig 1b: temps serveur et latence client selon F
plt.figure(figsize=(10,5))
plt.plot(x,server,marker="o",label="Temps serveur median")
plt.plot(x,client,marker="o",label="Latence client mediane")
plt.xlabel("Nombre de comptes suivis (F)")
plt.ylabel("Temps (ms)")
plt.title("Fig. 1b - Temps de traitement selon F")
plt.xticks(range(5,101,5),rotation=45)
plt.grid(True,alpha=0.3)
plt.legend()

#parametres fixe
plt.figtext(0.5,0.01,"U=120, P=20, N=1, C=1",ha="center",fontsize=9)

plt.tight_layout(rect=[0,0.05,1,1])
plt.savefig(figures / "fig1b.png",dpi=200)
plt.close()
print("Fig 1b sauvegardée")
