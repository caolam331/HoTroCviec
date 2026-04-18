import argparse, os, hashlib

parser = argparse.ArgumentParser()
parser.add_argument("--folder_a", required=True)
parser.add_argument("--folder_b", required=True)
parser.add_argument("--show_same", default="False")
args = parser.parse_args()

show_same = args.show_same.lower() in ("true", "1", "yes")

for label, path in [("A", args.folder_a), ("B", args.folder_b)]:
    if not os.path.isdir(path):
        print(f"[LỖI] Thư mục {label} không tồn tại: {path}")
        raise SystemExit(1)

def get_files(folder):
    result = {}
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, folder)
            try:
                result[rel] = os.path.getsize(full)
            except OSError:
                result[rel] = -1
    return result

def md5(path):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None

print(f"So sánh thư mục:")
print(f"  A: {args.folder_a}")
print(f"  B: {args.folder_b}\n")

files_a = get_files(args.folder_a)
files_b = get_files(args.folder_b)
all_keys = sorted(set(files_a) | set(files_b))

only_a = only_b = same = diff = 0

for rel in all_keys:
    in_a = rel in files_a
    in_b = rel in files_b

    if in_a and not in_b:
        print(f"  ← Chỉ trong A : {rel}  ({files_a[rel]:,} B)")
        only_a += 1
    elif in_b and not in_a:
        print(f"  → Chỉ trong B : {rel}  ({files_b[rel]:,} B)")
        only_b += 1
    else:
        pa = os.path.join(args.folder_a, rel)
        pb = os.path.join(args.folder_b, rel)
        if files_a[rel] != files_b[rel] or md5(pa) != md5(pb):
            print(f"  ≠ Khác nhau   : {rel}  (A:{files_a[rel]:,}B  B:{files_b[rel]:,}B)")
            diff += 1
        else:
            if show_same:
                print(f"  = Giống nhau  : {rel}")
            same += 1

print(f"\n{'─'*50}")
print(f"Chỉ trong A : {only_a} file")
print(f"Chỉ trong B : {only_b} file")
print(f"Khác nhau   : {diff} file")
print(f"Giống nhau  : {same} file")
print(f"Tổng        : {len(all_keys)} file")
