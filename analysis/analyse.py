
import csv
import statistics
from pathlib import Path
from collections import Counter

raw =Path("raw")
figures = Path("figures")
duration= 45

#fichier de different test
tests= []

for n in [1,2, 4]:
    for c in [1, 2, 4, 8, 16, 32,64]:
        file = f"fixed{n}_c{c}.csv"

        if n == 1:
            if c == 16:
                file= "run1.csv"
            else:
                file = f"baseline_c{c}.csv"

        tests.append((n,c,file))

        if n == 1 and c == 16:
            tests.append((1, 16, "baseline_c16.csv"))


def med(values):
    if len(values) == 0:
        return None
    return statistics.median(values)


def analyse(n, c, file):
    path = raw /file

    if not path.exists():
        return None

    with open(path, newline="") as f:
        rows =list(csv.DictReader(f))

    if len(rows) == 0:
        return None

    success= []
    errors= []

    for r in rows:
        if r["STATUS"] == "200":
            success.append(r)
        else:
            errors.append(r)

    times=[]
    server_times = []
    other_times = []

    for r in success:
        client =float(r["LATENCY_MS"])
        times.append(client)

        if r["SERVER_MS"]:
            server= float(r["SERVER_MS"])
            server_times.append(server)
            other_times.append(client - server)

    #pour les instances qui ont réelement répondu
    instances =set()
    for r in success:
        if r["INSTANCE"]:
            instances.add(r["INSTANCE"])

    error_types =Counter()
    for r in errors:
        if r["ERROR"]:
            error_types[r["ERROR"]] += 1
        else:
            error_types[f"HTTP {r['STATUS']}"] += 1

    rps =len(success) / duration
    failed = len(errors)

    result ={
        "instances_configured": n,
        "clients": c,
        "filename": file,
        "total_requests": len(rows),
        "successful_requests": len(success),
        "failed_requests": failed,
        "failure_rate_pct": round(failed / len(rows) * 100, 3),
        "throughput_rps": round(rps, 3),
        "client_mean_ms": round(statistics.mean(times), 3) if times else None,
        "client_median_ms": med(times),
        "server_median_ms": med(server_times),
        "other_median_ms": med(other_times),
        "little_prediction_ms": round(c / rps*1000,3) if rps else None,
        "instances_observed": len(instances),
        "errors": str(dict(error_types))
    }

    print(f"N={n},C={c} : {rps:.2f} req/s, median={med(times):.2f} ms, "
          f"instances={len(instances)},errors={failed}")

    if len(instances) !=n:
        print(f"Warning: expected {n} instances, got {len(instances)}")

    return result


def save_csv(file, data, columns):
    path = figures / file

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for row in data:
            line = {}
            for col in columns:
                line[col] = row.get(col)
            writer.writerow(line)

    print(f"Saved {file}")


def main():
    figures.mkdir(exist_ok=True)
    results = []

    for n, c, file in tests:
        result = analyse(n, c, file)

        if result is not None:
            results.append(result)

    if len(results) == 0:
        print("No results found")
        return

    save_csv("fig2_summary.csv", results, list(results[0].keys()))

    save_csv("fig2a.csv", results, [
        "instances_configured", "clients", "throughput_rps",
        "instances_observed", "failure_rate_pct"
    ])

    save_csv("fig2b.csv", results, [
        "instances_configured", "clients", "client_median_ms",
        "client_mean_ms", "little_prediction_ms"
    ])


if __name__ == "__main__":
    main()
