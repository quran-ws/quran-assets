#!/usr/bin/env python3
"""Resolve an archive.org item URL to a direct storage-server URL via the metadata API
(the dnXXX front mirrors sometimes return HTTP 500). Prints the resolved URL."""
import json, sys, re, urllib.request, urllib.parse
url = sys.argv[1]
m = re.search(r"/items/([^/]+)/(.+)$", url) or re.search(r"/download/([^/]+)/(.+)$", url)
if not m: print(url); sys.exit()
item, fname = m.group(1), urllib.parse.unquote(m.group(2))
d = json.load(urllib.request.urlopen(f"https://archive.org/metadata/{item}", timeout=30))
print(f"https://{d['server']}{d['dir']}/{urllib.parse.quote(fname)}")
