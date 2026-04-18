import argparse, os, sys

parser = argparse.ArgumentParser()
parser.add_argument("--log_file", required=True)
parser.add_argument("--lines", type=int, default=100)
args = parser.parse_args()

if not os.path.exists(args.log_file):
    print(f"[LỖI] File không tồn tại: {args.log_file}")
    raise SystemExit(1)

size = os.path.getsize(args.log_file)
print(f"File : {args.log_file}")
print(f"Kích thước: {size:,} bytes")
print(f"Hiển thị {args.lines} dòng cuối:\n")
print("─" * 60)

with open(args.log_file, "r", encoding="utf-8", errors="replace") as f:
    all_lines = f.readlines()

for line in all_lines[-args.lines:]:
    print(line, end="")

print("\n─" * 60)
print(f"\nTổng: {len(all_lines)} dòng, hiển thị {min(args.lines, len(all_lines))} dòng cuối.")
