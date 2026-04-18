import argparse, shutil, os

parser = argparse.ArgumentParser()
parser.add_argument("--path", default="C:\\")
args = parser.parse_args()

paths = [args.path] if os.path.exists(args.path) else []
if not paths:
    print(f"[LỖI] Đường dẫn không tồn tại: {args.path}")
    raise SystemExit(1)

# Show all drives on Windows + the specified path
checked = set()
try:
    import string
    drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    paths = list(dict.fromkeys([args.path] + drives))
except Exception:
    pass

print(f"{'Ổ đĩa / Thư mục':<30} {'Tổng':>10} {'Đã dùng':>10} {'Còn trống':>10} {'%':>6}")
print("─" * 70)
for p in paths:
    try:
        total, used, free = shutil.disk_usage(p)
        pct = used / total * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"{p:<30} {total//2**30:>8}GB {used//2**30:>8}GB {free//2**30:>8}GB {pct:>5.1f}%")
        print(f"  [{bar}]")
    except Exception as e:
        print(f"{p:<30} (không đọc được: {e})")
