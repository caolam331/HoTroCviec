import argparse, os, subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--repos_dir", required=True)
parser.add_argument("--branch", default="")
args = parser.parse_args()

root = args.repos_dir
if not os.path.isdir(root):
    print(f"[LỖI] Thư mục không tồn tại: {root}")
    raise SystemExit(1)

repos = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d, ".git"))]
if not repos:
    print(f"Không tìm thấy repo git nào trong: {root}")
    raise SystemExit(0)

print(f"Tìm thấy {len(repos)} repo trong {root}\n")
ok = fail = 0

for repo in sorted(repos):
    path = os.path.join(root, repo)
    print(f"{'─'*50}")
    print(f"📁 {repo}")

    cmd = ["git", "-C", path, "pull"]
    if args.branch:
        cmd += ["origin", args.branch]

    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = (r.stdout + r.stderr).strip()
    for line in output.splitlines():
        print(f"   {line}")

    if r.returncode == 0:
        print("   ✓ Thành công")
        ok += 1
    else:
        print("   ✗ Thất bại")
        fail += 1

print(f"\n{'═'*50}")
print(f"Kết quả: ✓ {ok} thành công  |  ✗ {fail} thất bại")
