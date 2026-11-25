
import csv
import statistics
from pathlib import Path

raw = Path("raw/part3")
figures = Path("figures")

files = [
    "sync_c16_cpu_test.csv",
    "sync_c16_repeat.csv",
    "worker2_c16_cpu_test.csv",
    "worker2thread2_c16.csv",
    "worker4thread4_c16.csv",
    "worker4thread4_c16_repeat.csv"
]

results = []

for file in files:
    path = raw / file

    if not path.exists():
        print(file, "pas trouve")
        continue

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) == 0:
        continue

    #debut du test
    start = min(float(r["T_START"]) for r in rows)

    #on divise le test en intervalles de 15 secondes
    for interval in range(12):
        debut = start + interval * 15
        fin = debut + 15

        client = []
        server = []
        errors = 0

        for r in rows:
            t = float(r["T_START"])

            if debut <= t < fin:
                if r["STATUS"] == "200":
                    client.append(float(r["LATENCY_MS"]))

                    if r["SERVER_MS"]:
                        server.append(float(r["SERVER_MS"]))
                else:
                    errors += 1

        if len(client) == 0:
            continue

        result = {
            "file": file,
            "interval": interval,
            "time_start": interval * 15,
            "throughput_rps": round(len(client) / 15, 2),
            "client_median_ms": statistics.median(client),
            "server_median_ms": statistics.median(server) if server else "",
            "errors": errors
        }

        results.append(result)

        print(f"{file} | {interval * 15}-{(interval + 1) * 15}s "
              f"| {result['throughput_rps']} req/s "
              f"| client={result['client_median_ms']} ms "
              f"| server={result['server_median_ms']} ms")

figures.mkdir(exist_ok=True)

with open(figures / "variation.csv", "w", newline="") as f:
    columns = [
        "file", "interval", "time_start",
        "throughput_rps", "client_median_ms",
        "server_median_ms", "errors"
    ]

    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()

    for r in results:
        writer.writerow(r)

print("variation.csv sauvegarde")
