import argparse
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="google.com")
parser.add_argument("--count", default="4")
args = parser.parse_args()

host = args.host
count = int(args.count)

print(f"Đang ping {host} ({count} lần)...\n")

flag = "-n" if sys.platform == "win32" else "-c"
result = subprocess.run(
    ["ping", flag, str(count), host],
    capture_output=False,
    text=True,
)

if result.returncode == 0:
    print("\nKết nối thành công!")
else:
    print("\nKhông thể kết nối tới host.")
    sys.exit(1)
