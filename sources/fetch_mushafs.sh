#!/usr/bin/env bash
# Downloads every source in mushafs.json into this folder. Resumable; re-run until "ALL_DONE".
# Usage: bash sources/fetch_mushafs.sh [max_seconds_per_run]
set -u
cd "$(dirname "$0")"
MAXT="${1:-0}"
[ "$MAXT" != "0" ] && MT="--max-time $MAXT" || MT=""
python3 - <<'PY' > /tmp/dl_list.txt
import json; [print(s["file"]+"\t"+s["url"]) for s in json.load(open("mushafs.json"))["sources"]]
PY
cat /tmp/dl_list.txt | xargs -P 4 -L 1 bash -c 'f="$0"; u="$1";
  if [ -f "$f.done" ]; then exit 0; fi
  # discard a bogus tiny error page left by a previous failed run
  [ -f "$f" ] && [ $(stat -c %s "$f") -lt 10000 ] && : > "$f"
  code=$(curl -L -C - --retry 3 -sS '"$MT"' -o "$f" -w "%{http_code}" "$u"); rc=$?
  if [ "$code" = "500" ] || [ "$code" = "404" ]; then
    : > "$f"; u2=$(python3 resolve_url.py "$u"); echo "fallback $f -> $u2"
    code=$(curl -L -C - --retry 3 -sS '"$MT"' -o "$f" -w "%{http_code}" "$u2"); rc=$?
  fi
  if [ $rc -eq 0 ] && [ "$code" = "200" -o "$code" = "206" ]; then touch "$f.done"; echo "done $f"; else echo "partial/failed $f (curl rc=$rc http=$code)"; fi'
n=$(grep -c . /tmp/dl_list.txt); d=$(ls *.done 2>/dev/null | wc -l)
[ "$d" -eq "$n" ] && echo ALL_DONE || echo "$d/$n complete - re-run"
