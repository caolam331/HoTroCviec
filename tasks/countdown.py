import argparse
import time
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", default="10", type=int)
parser.add_argument("--message", default="Done!")
args = parser.parse_args()

total = args.seconds
print(f"Bắt đầu đếm ngược {total} giây...\n")

for i in range(total, 0, -1):
    bar_len = 30
    filled = int(bar_len * (total - i) / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\r  [{bar}] {i:>4}s còn lại", end="", flush=True)
    time.sleep(1)

print(f"\r  [{'█' * 30}]  0s còn lại")
print(f"\n🔔 {args.message}")
