#!/usr/bin/env bash
# Optimize every generated SVG in place (needs `npx svgo` or a global svgo).
cd "$(dirname "$0")/.."
SVGO=$(command -v svgo || echo "$HOME/node_modules/.bin/svgo")
for f in assets/*/*/*.svg; do "$SVGO" -q --config pipeline/svgo.config.mjs "$f" -o "$f"; done
du -ch assets/*/*/*.svg | tail -1
