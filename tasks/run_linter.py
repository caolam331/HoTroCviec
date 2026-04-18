import argparse, subprocess, os, sys

parser = argparse.ArgumentParser()
parser.add_argument("--project_path", required=True)
parser.add_argument("--linter", default="flake8")
args = parser.parse_args()

if not os.path.isdir(args.project_path):
    print(f"[LỖI] Thư mục không tồn tại: {args.project_path}")
    raise SystemExit(1)

linter = args.linter
cmd_map = {
    "flake8":  ["flake8", "."],
    "pylint":  ["pylint", "."],
    "ruff":    ["ruff", "check", "."],
    "eslint":  ["npx", "eslint", "."],
}
cmd = cmd_map.get(linter, [linter, "."])

print(f"Linter: {linter}")
print(f"Thư mục: {args.project_path}\n")
print("─" * 60)

r = subprocess.run(
    cmd,
    cwd=args.project_path,
    text=True,
    encoding="utf-8",
    errors="replace",
)

print("─" * 60)
if r.returncode == 0:
    print("✓ Không tìm thấy lỗi.")
else:
    print(f"✗ Phát hiện vấn đề (exit code: {r.returncode})")
raise SystemExit(r.returncode)
