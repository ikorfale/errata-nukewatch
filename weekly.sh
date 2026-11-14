#!/bin/bash
# Daily check (timer errata-nukewatch): extend the series when a new IAEA update is archived,
# test the parser, commit and push. Quiet when nothing is new.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I parse.py --test >/dev/null
out=$(python3 -I update.py)
echo "$out"
n=$(echo "$out" | sed -n 's/^new: //p')
if [ "${n:-0}" -gt 0 ]; then
  last=$(tail -1 data/series.csv | cut -d, -f1)
  git add data/series.csv data/parser_only.json data/nukewatch-weekly.png
  git commit -q -m "Weekly series: add $n update(s) through Update $last (parser only, not blind-checked)"
  git push -q origin HEAD
  echo "pushed through u$last"
fi
