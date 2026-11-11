
#adaptation de l'analyse pour le facteur F

import csv
import statistics
from pathlib import Path

raw =Path("raw/part1")
figures = Path("figures")

#20 tests de f 
tests = []

for f in range(5,101,5):
    file = f"f{f:02d}.csv"
    tests.append((f,file))

results =[]

for f, file in tests:
    path =raw /file
    if not path.exists():
        print(file, "pas trouvé")
        continue

    with open(path, newline="") as fichier:
        rows =list(csv.DictReader(fichier))

    client = []
    server = []
    instances =set()
    errors = 0

    for r in rows:
        if r["STATUS"] != "200":
            errors += 1
            continue

        client.append(float(r["LATENCY_MS"]))
        if r["SERVER_MS"]:
            server.append(float(r["SERVER_MS"]))
        if r["INSTANCE"]:
            instances.add(r["INSTANCE"])

    if len(server) == 0 or len(client) == 0:
        print(file, "pas de mesure valide")
        continue

    client_med =statistics.median(client)
    server_med =statistics.median(server)

    result ={"F": f,"server_median_ms": server_med,"client_median_ms": client_med,"instances_observed": len(instances),"failed_requests": errors}
    results.append(result)
    print(f"F={f} : serveur={server_med:.2f} ms, "f"client={client_med:.2f} ms, "f"instances={len(instances)}, erreurs={errors}")

#on sauvegarde les resultats
figures.mkdir(exist_ok=True)

with open(figures / "fig1b.csv", "w", newline="") as fichier:
    columns = ["F", "server_median_ms", "client_median_ms","instances_observed", "failed_requests"]
    writer =csv.DictWriter(fichier, fieldnames=columns)
    writer.writeheader()
    for r in results:
        writer.writerow(r)
print("fig1b.csv sauvegardée")
