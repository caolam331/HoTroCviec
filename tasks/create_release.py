import argparse, subprocess, os, sys

parser = argparse.ArgumentParser()
parser.add_argument("--repo_path", required=True)
parser.add_argument("--version", required=True)
parser.add_argument("--message", default="")
args = parser.parse_args()

if not os.path.isdir(os.path.join(args.repo_path, ".git")):
    print(f"[LỖI] Không phải git repo: {args.repo_path}")
    raise SystemExit(1)

tag = args.version
msg = args.message or f"Release {tag}"
repo = args.repo_path

def run(cmd):
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip())
    return r.returncode

print(f"Tạo release tag: {tag}")
print(f"Repo: {repo}")
print(f"Message: {msg}\n")

# Check tag chưa tồn tại
r = subprocess.run(["git", "-C", repo, "tag", "-l", tag],
                   capture_output=True, text=True)
if tag in r.stdout.split():
    print(f"[LỖI] Tag '{tag}' đã tồn tại.")
    raise SystemExit(1)

print("1. Tạo tag...")
rc = run(["git", "-C", repo, "tag", "-a", tag, "-m", msg])
if rc != 0:
    raise SystemExit(rc)

print("2. Push tag lên remote...")
rc = run(["git", "-C", repo, "push", "origin", tag])

if rc == 0:
    print(f"\n✓ Release {tag} đã được tạo và push thành công!")
else:
    print(f"\nTag đã tạo local. Push thủ công bằng: git push origin {tag}")
