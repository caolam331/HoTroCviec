import argparse, subprocess, os

parser = argparse.ArgumentParser()
parser.add_argument("--project_path", required=True)
parser.add_argument("--manager", default="pip")
args = parser.parse_args()

if not os.path.isdir(args.project_path):
    print(f"[LỖI] Thư mục không tồn tại: {args.project_path}")
    raise SystemExit(1)

mgr = args.manager
print(f"Kiểm tra dependencies ({mgr})")
print(f"Thư mục: {args.project_path}\n")

cmd_map = {
    "pip":  ["pip", "list", "--outdated", "--format=columns"],
    "npm":  ["npm", "outdated"],
    "yarn": ["yarn", "outdated"],
    "pnpm": ["pnpm", "outdated"],
}
cmd = cmd_map.get(mgr)
if not cmd:
    print(f"[LỖI] Package manager không được hỗ trợ: {mgr}")
    raise SystemExit(1)

r = subprocess.run(
    cmd,
    cwd=args.project_path,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)

output = (r.stdout + r.stderr).strip()
if output:
    print(output)
else:
    print("✓ Tất cả packages đều cập nhật.")

if mgr == "pip" and r.stdout.strip():
    count = len(r.stdout.strip().splitlines()) - 2
    if count > 0:
        print(f"\n→ Cập nhật tất cả: pip install --upgrade $(pip list --outdated --format=freeze | cut -d= -f1)")
