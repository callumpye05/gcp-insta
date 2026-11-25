

import csv
import statistics

resultats = []
for f in range(5, 101, 5):
    nom =f"f{f:02d}.csv"
    avant =[]
    apres = []

    with open("raw/part1/" + nom) as fichier:
        for ligne in csv.DictReader(fichier):
            if ligne["STATUS"] == "200" and ligne["SERVER_MS"]:
                avant.append(float(ligne["SERVER_MS"]))

    with open("raw/part3/followers/" + nom) as fichier:
        for ligne in csv.DictReader(fichier):
            if ligne["STATUS"] == "200" and ligne["SERVER_MS"]:
                apres.append(float(ligne["SERVER_MS"]))

    mediane_avant = statistics.median(avant)
    mediane_apres = statistics.median(apres)
    acceleration =mediane_avant / mediane_apres
    resultats.append([f,round(mediane_avant, 2),round(mediane_apres,2),round(acceleration,2)])

with open("figures/fig3.csv", "w", newline="") as fichier:
    writer = csv.writer(fichier)
    writer.writerow(["F","latence_avant_ms","latence_apres_ms","acceleration"])
    writer.writerows(resultats)

for ligne in resultats:
    print(f"F={ligne[0]} : {ligne[1]} ms devient {ligne[2]} ms ({ligne[3]}x)")

