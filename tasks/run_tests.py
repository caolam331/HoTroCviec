import argparse, subprocess, os, sys

parser = argparse.ArgumentParser()
parser.add_argument("--project_path", required=True)
parser.add_argument("--test_command", default="pytest")
parser.add_argument("--verbose", default="True")
args = parser.parse_args()

if not os.path.isdir(args.project_path):
    print(f"[LỖI] Thư mục không tồn tại: {args.project_path}")
    raise SystemExit(1)

verbose = args.verbose.lower() in ("true", "1", "yes")
cmd_parts = args.test_command.split()
if verbose and cmd_parts[0] in ("pytest", "python"):
    if cmd_parts[0] == "pytest":
        cmd_parts.append("-v")

print(f"Chạy tests: {' '.join(cmd_parts)}")
print(f"Thư mục: {args.project_path}\n")
print("─" * 60)

r = subprocess.run(
    cmd_parts,
    cwd=args.project_path,
    text=True,
    encoding="utf-8",
    errors="replace",
)

print("─" * 60)
status = "✓ PASSED" if r.returncode == 0 else "✗ FAILED"
print(f"\n{status} (exit code: {r.returncode})")
raise SystemExit(r.returncode)
