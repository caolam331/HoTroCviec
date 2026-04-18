import argparse, subprocess, datetime, os

parser = argparse.ArgumentParser()
parser.add_argument("--repo_path", required=True)
parser.add_argument("--since_tag", default="")
parser.add_argument("--output", default="")
args = parser.parse_args()

if not os.path.isdir(os.path.join(args.repo_path, ".git")):
    print(f"[LỖI] Không phải git repo: {args.repo_path}")
    raise SystemExit(1)

cmd = [
    "git", "-C", args.repo_path, "log",
    "--no-merges", "--format=%h|%an|%ad|%s", "--date=short",
]
if args.since_tag:
    cmd += [f"{args.since_tag}..HEAD"]

r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
if r.returncode != 0:
    print(r.stderr)
    raise SystemExit(r.returncode)

lines = [l for l in r.stdout.strip().splitlines() if l]
if not lines:
    print("Không có commit nào.")
    raise SystemExit(0)

# Group by date
from collections import defaultdict
by_date = defaultdict(list)
for line in lines:
    parts = line.split("|", 3)
    if len(parts) == 4:
        h, author, date, subject = parts
        by_date[date].append((h.strip(), author.strip(), subject.strip()))

today = datetime.date.today().isoformat()
since_str = f" từ `{args.since_tag}`" if args.since_tag else ""
out = [f"# Changelog{since_str}\n", f"_Tạo lúc: {today}_\n"]

for date in sorted(by_date.keys(), reverse=True):
    out.append(f"\n## {date}\n")
    for h, author, subject in by_date[date]:
        out.append(f"- `{h}` **{author}**: {subject}")

content = "\n".join(out)
print(content)

if args.output:
    out_path = os.path.join(args.repo_path, args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n✓ Đã lưu vào: {out_path}")
