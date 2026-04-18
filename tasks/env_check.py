import argparse, os

parser = argparse.ArgumentParser()
parser.add_argument("--project_path", required=True)
args = parser.parse_args()

root = args.project_path
env_file    = os.path.join(root, ".env")
example_file = os.path.join(root, ".env.example")

def read_keys(path):
    keys = {}
    if not os.path.exists(path):
        return keys
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k = line.split("=", 1)[0].strip()
                v = line.split("=", 1)[1].strip()
                keys[k] = v
    return keys

print(f"Kiểm tra file .env")
print(f"Thư mục: {root}\n")

has_env     = os.path.exists(env_file)
has_example = os.path.exists(example_file)

if not has_env and not has_example:
    print("Không tìm thấy .env hoặc .env.example")
    raise SystemExit(0)

env_keys     = read_keys(env_file)
example_keys = read_keys(example_file)

if not has_example:
    print(f"✓ .env tồn tại ({len(env_keys)} biến)\n")
    print("Các biến trong .env:")
    for k in sorted(env_keys):
        masked = env_keys[k][:2] + "***" if env_keys[k] else "(rỗng)"
        print(f"  {k} = {masked}")
    raise SystemExit(0)

missing   = [k for k in example_keys if k not in env_keys]
extra     = [k for k in env_keys if k not in example_keys]
empty_env = [k for k in env_keys if not env_keys[k] and k in example_keys]

print(f".env         : {len(env_keys)} biến")
print(f".env.example : {len(example_keys)} biến\n")

if not missing and not extra and not empty_env:
    print("✓ .env đồng bộ hoàn toàn với .env.example")
else:
    if missing:
        print(f"✗ Thiếu trong .env ({len(missing)} biến):")
        for k in missing:
            print(f"   - {k}  (example: {example_keys[k] or '(rỗng)'})")
    if empty_env:
        print(f"\n⚠ Biến rỗng ({len(empty_env)}):")
        for k in empty_env:
            print(f"   - {k}")
    if extra:
        print(f"\nℹ Có trong .env nhưng không trong example ({len(extra)}):")
        for k in extra:
            print(f"   + {k}")
