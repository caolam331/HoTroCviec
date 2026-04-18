import argparse, os

parser = argparse.ArgumentParser()
parser.add_argument("--directory", required=True)
parser.add_argument("--min_size_mb", type=int, default=100)
parser.add_argument("--top_n", type=int, default=20)
args = parser.parse_args()

if not os.path.isdir(args.directory):
    print(f"[LỖI] Thư mục không tồn tại: {args.directory}")
    raise SystemExit(1)

min_bytes = args.min_size_mb * 1024 * 1024
print(f"Tìm file lớn hơn {args.min_size_mb} MB")
print(f"Thư mục: {args.directory}\n")

found = []
scanned = 0
for dirpath, _, filenames in os.walk(args.directory):
    for fname in filenames:
        fpath = os.path.join(dirpath, fname)
        try:
            size = os.path.getsize(fpath)
            scanned += 1
            if size >= min_bytes:
                found.append((size, fpath))
        except OSError:
            pass

found.sort(reverse=True)
shown = found[:args.top_n]

if not shown:
    print(f"Không tìm thấy file nào lớn hơn {args.min_size_mb} MB.")
else:
    print(f"{'Kích thước':>12}  Đường dẫn")
    print("─" * 70)
    for size, path in shown:
        if size >= 1024**3:
            sz = f"{size/1024**3:>8.2f} GB"
        elif size >= 1024**2:
            sz = f"{size/1024**2:>8.1f} MB"
        else:
            sz = f"{size/1024:>8.1f} KB"
        print(f"  {sz}  {path}")

    if len(found) > args.top_n:
        print(f"\n  ... và {len(found) - args.top_n} file khác")

total_mb = sum(s for s, _ in found) / 1024**2
print(f"\nĐã quét: {scanned:,} file  |  Tìm thấy: {len(found)} file  |  Tổng: {total_mb:.1f} MB")
