import functools
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CACHE_DIR = os.path.expanduser("~/.cache/cpython_closable_issues")


def bpo_from_issue(data) -> int | None:
    if "pull_request" in data["issue"]:
        return None
    body = data["issue"]["body"] or ""
    m = re.match(r"^BPO \| \[(\d+)\]\(https://bugs.python.org/issue(\d+)\)", body)
    if m is None:
        return None
    assert m.group(1) == m.group(2)
    return int(m.group(1))


@functools.cache
def gh_bpo_from_file(filename: Path) -> tuple[int, int | None]:
    with open(filename) as f:
        data = json.load(f)
    gh_num = data["issue"]["number"]
    bpo_num = bpo_from_issue(data)
    return gh_num, bpo_num


def bpo_to_gh():
    result = {}
    with ThreadPoolExecutor() as executor:
        for gh_num, bpo_num in executor.map(gh_bpo_from_file, Path(CACHE_DIR).glob("gh-*.json")):
            if bpo_num is not None:
                result[bpo_num] = gh_num
    return result
