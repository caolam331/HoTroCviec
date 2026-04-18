import argparse, os, shutil

parser = argparse.ArgumentParser()
parser.add_argument("--project_path", required=True)
parser.add_argument("--dry_run", default="True")
args = parser.parse_args()

dry = args.dry_run.lower() in ("true", "1", "yes")
root = args.project_path

if not os.path.isdir(root):
    print(f"[LỖI] Thư mục không tồn tại: {root}")
    raise SystemExit(1)

TARGETS = {"build", "dist", ".pytest_cache", "__pycache__",
           ".mypy_cache", ".ruff_cache", "node_modules/.cache",
           ".next", ".nuxt", "coverage", "htmlcov", ".eggs", "*.egg-info"}

print(f"{'[DRY RUN] ' if dry else ''}Dọn dẹp build artifacts")
print(f"Thư mục: {root}\n")

found = []
for dirpath, dirnames, _ in os.walk(root):
    for d in list(dirnames):
        if d in TARGETS or d.endswith(".egg-info"):
            full = os.path.join(dirpath, d)
            size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(full)
                for f in fs
            ) // 1024
            found.append((full, size))
            dirnames.remove(d)

if not found:
    print("✓ Không có gì cần dọn.")
    raise SystemExit(0)

total_kb = 0
for path, size_kb in found:
    action = "[bỏ qua]" if dry else "[xóa]"
    print(f"  {action} {path}  ({size_kb:,} KB)")
    if not dry:
        shutil.rmtree(path, ignore_errors=True)
    total_kb += size_kb

print(f"\nTổng: {len(found)} thư mục  |  {total_kb:,} KB ({total_kb//1024} MB)")
if dry:
    print("\n→ Thêm --dry_run False để xóa thật.")
else:
    print("✓ Đã dọn xong.")
