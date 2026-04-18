import argparse, subprocess, sys

parser = argparse.ArgumentParser()
parser.add_argument("--show_all", default="False")
args = parser.parse_args()

show_all = args.show_all.lower() in ("true", "1", "yes")

# Check docker available
r = subprocess.run(["docker", "--version"], capture_output=True, text=True)
if r.returncode != 0:
    print("[LỖI] Docker không được cài đặt hoặc không chạy.")
    raise SystemExit(1)
print(r.stdout.strip())

# Containers
print("\n─── Containers ───")
cmd = ["docker", "ps", "--format",
       "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
if show_all:
    cmd.append("-a")

r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout if r.stdout.strip() else "Không có container nào.")

# Images summary
print("─── Images ───")
r2 = subprocess.run(
    ["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
lines = r2.stdout.strip().splitlines()
print("\n".join(lines[:11]))
if len(lines) > 11:
    print(f"... và {len(lines)-11} image khác")

# Disk usage
print("\n─── Disk usage ───")
r3 = subprocess.run(["docker", "system", "df"], capture_output=True, text=True)
print(r3.stdout.strip())
