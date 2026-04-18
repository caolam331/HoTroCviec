import argparse, subprocess, datetime, os

parser = argparse.ArgumentParser()
parser.add_argument("--repo_path", required=True)
parser.add_argument("--author", default="")
args = parser.parse_args()

if not os.path.isdir(os.path.join(args.repo_path, ".git")):
    print(f"[LỖI] Không phải git repo: {args.repo_path}")
    raise SystemExit(1)

today = datetime.date.today().isoformat()
print(f"Git log hôm nay ({today})")
print(f"Repo: {args.repo_path}")
if args.author:
    print(f"Tác giả: {args.author}")
print("─" * 60)

cmd = [
    "git", "-C", args.repo_path, "log",
    f"--after={today} 00:00",
    f"--before={today} 23:59",
    "--format=%C(yellow)%h%Creset %C(cyan)%an%Creset %s  %C(green)%ar%Creset",
    "--no-merges",
]
if args.author:
    cmd += [f"--author={args.author}"]

r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
output = r.stdout.strip()

if not output:
    print("Không có commit nào hôm nay.")
else:
    print(output)
    count = len(output.splitlines())
    print(f"\nTổng: {count} commit hôm nay.")
