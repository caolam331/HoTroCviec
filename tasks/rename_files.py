import argparse
import re
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--folder", required=True)
parser.add_argument("--pattern", default=".*")
parser.add_argument("--prefix", default="")
parser.add_argument("--dry_run", default="True")
args = parser.parse_args()

folder = Path(args.folder)
pattern = args.pattern
prefix = args.prefix
dry_run = args.dry_run.lower() in ("true", "1", "yes")

if not folder.exists():
    print(f"[LỖI] Thư mục không tồn tại: {folder}")
    exit(1)

print(f"Thư mục: {folder}")
print(f"Pattern: {pattern} | Prefix: '{prefix}' | Dry run: {dry_run}\n")

matched = [f for f in folder.iterdir() if f.is_file() and re.match(pattern, f.name)]

if not matched:
    print("Không tìm thấy file phù hợp.")
    exit(0)

for f in matched:
    new_name = prefix + f.name
    new_path = f.parent / new_name
    if dry_run:
        print(f"[DRY] {f.name}  →  {new_name}")
    else:
        f.rename(new_path)
        print(f"Đã đổi tên: {f.name}  →  {new_name}")

print(f"\nTổng cộng: {len(matched)} file{'(s)' if len(matched) > 1 else ''}")
if dry_run:
    print("(Chế độ thử — không có thay đổi thực sự)")
