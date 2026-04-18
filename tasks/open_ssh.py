import argparse, subprocess, sys, shutil

parser = argparse.ArgumentParser()
parser.add_argument("--host", required=True)
parser.add_argument("--user", default="root")
parser.add_argument("--port", type=int, default=22)
parser.add_argument("--key_file", default="")
args = parser.parse_args()

if not shutil.which("ssh"):
    print("[LỖI] SSH client không được cài đặt.")
    raise SystemExit(1)

target = f"{args.user}@{args.host}"
cmd = ["ssh", "-p", str(args.port), target]
if args.key_file and args.key_file.strip():
    cmd += ["-i", args.key_file]

print(f"Kết nối SSH:")
print(f"  Host : {args.host}:{args.port}")
print(f"  User : {args.user}")
if args.key_file:
    print(f"  Key  : {args.key_file}")
print(f"\nLệnh: {' '.join(cmd)}\n")
print("─" * 50)

# Mở SSH trong terminal mới (Windows)
if sys.platform == "win32":
    ssh_cmd = " ".join(cmd)
    subprocess.Popen(
        f'start cmd /k "{ssh_cmd}"',
        shell=True
    )
    print("✓ Đã mở cửa sổ terminal SSH.")
else:
    terms = ["x-terminal-emulator", "gnome-terminal", "xterm"]
    import shutil as sh
    term = next((t for t in terms if sh.which(t)), None)
    if term:
        subprocess.Popen([term, "--", *cmd])
        print("✓ Đã mở terminal SSH.")
    else:
        print("Không tìm thấy terminal emulator. Chạy thủ công:")
        print(f"  {' '.join(cmd)}")
