import argparse, subprocess, datetime, os
from collections import defaultdict

parser = argparse.ArgumentParser()
parser.add_argument("--repos_dir", required=True)
parser.add_argument("--output_format", default="markdown")
args = parser.parse_args()

root = args.repos_dir
if not os.path.isdir(root):
    print(f"[LỖI] Thư mục không tồn tại: {root}")
    raise SystemExit(1)

repos = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d, ".git"))]
today = datetime.date.today().isoformat()

all_commits = defaultdict(list)  # author -> [(repo, hash, subject)]

for repo in sorted(repos):
    path = os.path.join(root, repo)
    r = subprocess.run(
        ["git", "-C", path, "log",
         f"--after={today} 00:00", f"--before={today} 23:59",
         "--no-merges", "--format=%an|%h|%s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    for line in r.stdout.strip().splitlines():
        if "|" in line:
            author, h, subject = line.split("|", 2)
            all_commits[author.strip()].append((repo, h.strip(), subject.strip()))

fmt = args.output_format
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

if fmt == "markdown":
    print(f"# Báo cáo Standup — {today}\n")
    print(f"_Tạo lúc {now_str} từ {len(repos)} repo_\n")
    if not all_commits:
        print("_Chưa có commit nào hôm nay._")
    for author in sorted(all_commits):
        commits = all_commits[author]
        print(f"## {author} ({len(commits)} commit)\n")
        for repo, h, subject in commits:
            print(f"- `{h}` [{repo}] {subject}")
        print()

elif fmt == "html":
    print(f"<h2>Báo cáo Standup — {today}</h2>")
    for author in sorted(all_commits):
        commits = all_commits[author]
        print(f"<h3>{author} ({len(commits)} commit)</h3><ul>")
        for repo, h, subject in commits:
            print(f"  <li><code>{h}</code> [{repo}] {subject}</li>")
        print("</ul>")

else:  # text
    print(f"BÁO CÁO STANDUP — {today}")
    print("=" * 60)
    if not all_commits:
        print("Chưa có commit nào hôm nay.")
    for author in sorted(all_commits):
        commits = all_commits[author]
        print(f"\n{author} ({len(commits)} commit):")
        for repo, h, subject in commits:
            print(f"  [{repo}] {h} — {subject}")

total = sum(len(v) for v in all_commits.values())
print(f"\nTổng: {total} commit từ {len(all_commits)} thành viên")
