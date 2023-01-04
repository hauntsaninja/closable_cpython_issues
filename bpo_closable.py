import functools
import gzip

from closable_cpython_issues import *


@functools.cache
def get_cached_issue(issue: int):
    cache_file = os.path.join(CACHE_DIR, f"gh-{issue}.json")
    if os.path.isfile(cache_file):
        with open(cache_file) as f:
            data = json.load(f)
        return data["issue"]
    return None

with open("bpo_to_gh.json.gz", "rb") as f:
    bpo_to_gh = json.loads(gzip.decompress(f.read()))
bpo_to_gh = {int(k): int(v) for k, v in bpo_to_gh.items()}


def bpo_issue_to_commits_addressing(repo: str) -> dict[int, list[tuple[str, str]]]:
    subprocess.check_output(["git", "fetch", "--all"], cwd=repo)
    main = get_main_branch(repo)
    out = subprocess.check_output(["git", "log", "--pretty=%h %s", main], cwd=repo)
    issues_to_commits = defaultdict(list)
    for line in out.decode("utf-8").splitlines():
        commit, title = line.split(" ", maxsplit=1)
        if match := re.match(r"bpo-(\d+)", title, re.IGNORECASE):
            issue = int(match.group(1))
            issues_to_commits[issue].append((commit, title))
    return issues_to_commits


repo = os.path.expanduser("~/dev/cpython")
issues_to_commits = bpo_issue_to_commits_addressing(repo)
single_commit_issues = [k for k, v in issues_to_commits.items() if len(v) == 1]
open_single_commit_issues = [
    k
    for k in single_commit_issues
    if k in bpo_to_gh
    and get_cached_issue(bpo_to_gh[k])
    and get_cached_issue(bpo_to_gh[k])["state"] != "closed"
]
open_single_commit_issues.sort(key=lambda k: get_cached_issue(bpo_to_gh[k])["updated_at"], reverse=True)
for k in open_single_commit_issues:
    print(k, bpo_to_gh[k], get_cached_issue(bpo_to_gh[k])["html_url"], get_cached_issue(bpo_to_gh[k])["updated_at"], get_cached_issue(bpo_to_gh[k])["comments"])
print(len(open_single_commit_issues))

# for i in issues:
#     get_issue(i, os.environ.get("GITHUB_TOKEN"), staleness=0)
