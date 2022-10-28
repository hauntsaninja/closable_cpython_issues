import argparse
import datetime
import json
import os
import re
import subprocess
import time
from collections import defaultdict
from typing import Any, Mapping

import requests

CACHE_DIR = os.path.expanduser("~/.cache/cpython_closable_issues")


def _delay_from_headers(headers: Mapping[str, str]) -> float:
    delay = max(0, float(headers.get("X-RateLimit-Reset", 0)) - time.time())
    delay /= max(1, int(headers.get("X-RateLimit-Remaining", 1)))
    delay *= 1.1
    return delay


def get_issue(issue: int, token: str, staleness: float) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc)

    cache_file = os.path.join(CACHE_DIR, f"gh-{issue}.json")
    if os.path.isfile(cache_file):
        with open(cache_file) as f:
            data = json.load(f)

        fetch_time = datetime.datetime.fromisoformat(data["fetch_time"])
        assert fetch_time.tzinfo is datetime.timezone.utc
        last_update_time = datetime.datetime.strptime(
            data["issue"]["updated_at"], "%Y-%m-%dT%H:%M:%S%z"
        )
        assert last_update_time.tzinfo is datetime.timezone.utc
        # If an issue has been updated recently, it's an indicator it may be updated again soon,
        # so invalidate the cache sooner.
        deadline = fetch_time + staleness * (fetch_time - last_update_time)
        deadline = min(deadline, fetch_time + datetime.timedelta(days=30))
        if now < deadline:
            return data["issue"]

    request_time = -time.perf_counter()
    url = f"https://api.github.com/repos/python/cpython/issues/{issue}"
    headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    request_time += time.perf_counter()

    if int(response.headers.get("X-RateLimit-Remaining", 0)) < 500:
        delay = _delay_from_headers(response.headers)
        delay = max(0, min(120, delay - request_time))
        time.sleep(delay)

    tmp_cache_file = cache_file + ".tmp"
    with open(tmp_cache_file, "w") as f:
        json.dump({"fetch_time": now.isoformat(), "issue": data}, f)
    os.replace(tmp_cache_file, cache_file)
    return data


def get_main_branch(repo: str) -> str:
    try:
        subprocess.check_output(["git", "rev-parse", "upstream/main"], cwd=repo)
        return "upstream/main"
    except subprocess.CalledProcessError:
        try:
            subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=repo)
            return "origin/main"
        except subprocess.CalledProcessError:
            return "main"


def gh_issue_to_commits_addressing(repo: str) -> dict[int, list[tuple[str, str]]]:
    subprocess.check_output(["git", "fetch", "--all"], cwd=repo)
    main = get_main_branch(repo)
    out = subprocess.check_output(
        ["git", "log", "--pretty=%h %s", "--since=2022-01-01", main], cwd=repo
    )
    issues_to_commits = defaultdict(list)
    for line in out.decode("utf-8").splitlines():
        commit, title = line.split(" ", maxsplit=1)
        if match := re.match(r"gh-(\d+)", title, re.IGNORECASE):
            issue = int(match.group(1))
            issues_to_commits[issue].append((commit, title))
    return issues_to_commits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default=os.environ.get("CPYTHON_REPO") or os.path.expanduser("~/dev/cpython"),
        help="Path to the CPython repo",
    )
    parser.add_argument(
        "--token", default=os.environ.get("GITHUB_TOKEN"), help="Personal access token from GitHub"
    )
    parser.add_argument(
        "--staleness",
        default=0.1,
        type=float,
        help="How stale the issue cache can get (0: not at all, 0.1: default, 100: very stale)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.repo) or not os.path.isdir(os.path.join(args.repo, ".git")):
        raise RuntimeError(f"Invalid repo path: {args.repo}")
    if args.token is None or not args.token.startswith(("ghp", "github")):
        raise RuntimeError("Invalid GitHub token")
    os.makedirs(CACHE_DIR, exist_ok=True)

    count = 0
    issues_to_commits = gh_issue_to_commits_addressing(args.repo)
    for issue_num, commits in issues_to_commits.items():
        issue = get_issue(issue_num, token=args.token, staleness=args.staleness)
        if issue["state"] == "closed":
            continue
        print(f"#{issue_num} {issue['title']}")
        print(f"\033[94m{issue['html_url']}\033[0m")
        for commit, title in commits:
            print(f"    \033[2m{commit} {title}\033[0m")
        count += 1

    print()
    print(f"{count} open issues with commits that reference their Github issue number")


if __name__ == "__main__":
    main()
