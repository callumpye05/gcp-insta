
import csv
from pathlib import Path
import matplotlib.pyplot as plt

figures =Path("figures")

#lecture resultat
with open(figures / "fig1a.csv", newline="") as f:
    rows = list(csv.DictReader(f))

users =[]
posts = []

for r in rows:
    if r["facteur"] == "U":
        users.append(r)
    else:
        posts.append(r)

x_u = []
y_u =[]
x_p = []
y_p = []

for r in users:
    x_u.append(int(r["valeur"]))
    y_u.append(float(r["server_median_ms"]))

for r in posts:
    x_p.append(int(r["valeur"]))
    y_p.append(float(r["server_median_ms"]))


#fig 1a :impact de U et P
fig, axes = plt.subplots(1,2,figsize=(11,4.5))
axes[0].plot(x_u,y_u,marker="o")
axes[0].set_xscale("log")
axes[0].set_xticks([100,1000,10000])
axes[0].set_xticklabels(["100","1000","10000"])
axes[0].set_xlabel("Nombre d'utilisateur (U)")
axes[0].set_ylabel("Temps serveur median (ms)")
axes[0].set_title("Impact du nombre d'utilisateur")
axes[0].grid(True,alpha=0.3)

axes[1].plot(x_p,y_p,marker="o")
axes[1].set_xscale("log")
axes[1].set_xticks([10,100,1000])
axes[1].set_xticklabels(["10","100","1000"])
axes[1].set_xlabel("Posts par utilisateur (P)")
axes[1].set_ylabel("Temps serveur median (ms)")
axes[1].set_title("Impact du nombre de post")
axes[1].grid(True,alpha=0.3)

fig.suptitle("Fig. 1a - Temps serveur selon U et P")

#parametres fixe pour chaque expérience réalisé 
fig.text(0.25,0.01,"P=20, F=20, N=1, C=1",ha="center",fontsize=9)
fig.text(0.75,0.01,"U=100, F=20, N=1, C=1",ha="center",fontsize=9)

plt.tight_layout(rect=[0,0.05,1,0.94])
plt.savefig(figures / "fig1a.png",dpi=200)
plt.close()
print("Fig 1a sauvegardée")
