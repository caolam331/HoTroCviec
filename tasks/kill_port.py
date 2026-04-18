import argparse, subprocess, sys, os

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
args = parser.parse_args()

port = args.port
print(f"Tìm tiến trình đang dùng cổng {port}...\n")

if sys.platform == "win32":
    result = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True
    )
    pids = set()
    for line in result.stdout.splitlines():
        if f":{port}" in line and ("LISTENING" in line or "ESTABLISHED" in line):
            parts = line.split()
            if parts:
                pids.add(parts[-1])

    if not pids:
        print(f"Không có tiến trình nào đang dùng cổng {port}.")
        raise SystemExit(0)

    for pid in pids:
        try:
            info = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True
            ).stdout.strip()
            print(f"PID {pid}: {info}")
            subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
            print(f"✓ Đã dừng tiến trình PID {pid}")
        except Exception as e:
            print(f"✗ Không thể dừng PID {pid}: {e}")
else:
    result = subprocess.run(
        ["lsof", "-ti", f":{port}"], capture_output=True, text=True
    )
    pids = result.stdout.strip().split()
    if not pids:
        print(f"Không có tiến trình nào đang dùng cổng {port}.")
        raise SystemExit(0)
    for pid in pids:
        subprocess.run(["kill", "-9", pid])
        print(f"✓ Đã dừng PID {pid}")
