#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 analysis/analyse_part1.py
python3 analysis/analyse_f_part1.py
python3 analysis/analyse_part2.py
python3 analysis/analyse_part3.py
python3 analysis/plot_part1.py
python3 analysis/plot_f_part1.py
python3 analysis/plot_part2.py
python3 analysis/plot_part3.py
python3 analysis/plot_b1_b2.py

echo "All figures are generated"