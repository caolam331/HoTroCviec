import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("--name", default="World")
parser.add_argument("--greet", default="Hello")
args = parser.parse_args()

print(f"{args.greet}, {args.name}!")
print("Đang xử lý", end="", flush=True)
for _ in range(5):
    time.sleep(0.3)
    print(".", end="", flush=True)
print("\nXong!")
