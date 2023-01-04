import os
import gzip
import json
import re
from pathlib import Path

with open("bpo_to_gh.json.gz", "rb") as f:
    bpo_to_gh = json.loads(gzip.decompress(f.read()))
bpo_to_gh = {int(k): int(v) for k, v in bpo_to_gh.items()}

CACHE_DIR = os.path.expanduser("~/.cache/cpython_closable_issues")

for fn in sorted(Path(CACHE_DIR).glob("gh-*.json")):
    with open(fn) as f:
        data = json.load(f)
    issue = data["issue"]
    if "pull_request" not in issue:
        continue
    if issue["state"] == "closed":
        continue
    if "idle" not in issue["title"].lower() and all(label["name"] != "expert-IDLE" for label in issue["labels"]):
        continue
    if (match := re.match(r"bpo-(\d+)", issue["title"], re.IGNORECASE)) is None:
        continue
    bpo_num = int(match.group(1))
    print(issue["title"])
    print(re.sub(r"bpo-\d+", f"gh-{bpo_to_gh[bpo_num]}", issue["title"], flags=re.IGNORECASE))
    print(f"\033[94m{issue['html_url']}\033[0m")
    print()
