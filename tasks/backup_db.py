import argparse, subprocess, os, datetime

parser = argparse.ArgumentParser()
parser.add_argument("--db_type", required=True)
parser.add_argument("--db_name", required=True)
parser.add_argument("--output_path", required=True)
args = parser.parse_args()

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = args.output_path
os.makedirs(out_dir, exist_ok=True)

db = args.db_name
dtype = args.db_type
fname = f"{db}_{ts}.sql"
out_file = os.path.join(out_dir, fname)

print(f"Backup database: {db} ({dtype})")
print(f"Output: {out_file}\n")

cmd_map = {
    "postgresql": ["pg_dump", "-F", "c", "-f", out_file, db],
    "mysql":      ["mysqldump", "--result-file", out_file, db],
    "sqlite":     None,
    "mongodb":    ["mongodump", "--db", db, "--out", os.path.join(out_dir, f"{db}_{ts}")],
}

if dtype == "sqlite":
    import shutil, glob
    candidates = glob.glob(f"**/{db}.db", recursive=True) + glob.glob(f"**/{db}.sqlite3", recursive=True)
    if not candidates:
        print(f"[LỖI] Không tìm thấy file SQLite: {db}.db")
        raise SystemExit(1)
    src = candidates[0]
    out_file = os.path.join(out_dir, f"{os.path.basename(src)}_{ts}.bak")
    shutil.copy2(src, out_file)
    size = os.path.getsize(out_file)
    print(f"✓ Đã sao chép: {src} → {out_file}")
    print(f"  Kích thước: {size:,} bytes")
    raise SystemExit(0)

cmd = cmd_map.get(dtype)
if not cmd:
    print(f"[LỖI] Không hỗ trợ: {dtype}")
    raise SystemExit(1)

r = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace")
if r.returncode == 0:
    size = os.path.getsize(out_file) if os.path.exists(out_file) else 0
    print(f"✓ Backup thành công!")
    print(f"  File: {out_file}")
    print(f"  Kích thước: {size:,} bytes")
else:
    print("✗ Backup thất bại.")
raise SystemExit(r.returncode)
