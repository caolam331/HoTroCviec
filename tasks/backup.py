import argparse
import shutil
import zipfile
import os
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--destination", required=True)
parser.add_argument("--compress", default="True")
args = parser.parse_args()

src = Path(args.source)
dst = Path(args.destination)
compress = args.compress.lower() in ("true", "1", "yes")

if not src.exists():
    print(f"[LỖI] Thư mục nguồn không tồn tại: {src}")
    exit(1)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dst.mkdir(parents=True, exist_ok=True)

if compress:
    out = dst / f"backup_{src.name}_{timestamp}.zip"
    print(f"Đang nén {src} → {out}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(src))
                print(f"  + {f.relative_to(src)}")
    print(f"\nHoàn thành! File ZIP: {out}")
else:
    out = dst / f"backup_{src.name}_{timestamp}"
    print(f"Đang copy {src} → {out}")
    shutil.copytree(src, out)
    print(f"Hoàn thành! Thư mục: {out}")
