
import csv
import statistics
from pathlib import Path

raw = Path("raw/part1")
figures = Path("figures")

#les tests pour U et P
tests = []

for u in [100, 1000, 10000]:
    tests.append(("U", u, f"u{u}.csv"))

for p in [10, 100, 1000]:
    tests.append(("P", p, f"p{p}.csv"))

results =[]

for facteur, valeur, file in tests:
    path =raw / file

    if not path.exists():
        print(file, "pas trouvé")
        continue

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    client =[]
    server = []
    instances = set()
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
        print(file, "pas de mesures valide")
        continue

    client_med = statistics.median(client)
    server_med = statistics.median(server)
    result = {"facteur": facteur,"valeur": valeur,"server_median_ms": server_med,"client_median_ms": client_med,"instances_observed": len(instances),"failed_requests": errors}
    results.append(result)
    print(f"{facteur}={valeur} : serveur={server_med:.2f} ms, " f"client={client_med:.2f} ms, instances={len(instances)}, erreurs={errors}")

#on sauvegarde les resultats
figures.mkdir(exist_ok=True)

with open(figures / "fig1a.csv", "w", newline="") as f:
    columns = ["facteur", "valeur", "server_median_ms","client_median_ms", "instances_observed", "failed_requests"]
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()

    for r in results:
        writer.writerow(r)

print("fig1a.csv sauvegarde")

