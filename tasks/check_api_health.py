import argparse, urllib.request, urllib.error, time, json

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--expected_status", type=int, default=200)
parser.add_argument("--timeout", type=int, default=10)
args = parser.parse_args()

print(f"Kiểm tra API: {args.url}")
print(f"Expected status: {args.expected_status}  |  Timeout: {args.timeout}s\n")

start = time.time()
try:
    req = urllib.request.Request(args.url, headers={"User-Agent": "HealthCheck/1.0"})
    with urllib.request.urlopen(req, timeout=args.timeout) as resp:
        elapsed = (time.time() - start) * 1000
        status = resp.status
        body = resp.read(2048).decode("utf-8", errors="replace")

        if status == args.expected_status:
            print(f"✓ OK  |  Status: {status}  |  Thời gian: {elapsed:.0f}ms")
        else:
            print(f"✗ FAIL  |  Status: {status} (mong đợi {args.expected_status})  |  {elapsed:.0f}ms")

        print("\n─── Response (2KB đầu) ───")
        try:
            parsed = json.loads(body)
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except Exception:
            print(body)

        raise SystemExit(0 if status == args.expected_status else 1)

except urllib.error.HTTPError as e:
    elapsed = (time.time() - start) * 1000
    print(f"✗ HTTP {e.code}  |  {elapsed:.0f}ms  |  {e.reason}")
    raise SystemExit(1)
except Exception as e:
    elapsed = (time.time() - start) * 1000
    print(f"✗ LỖI  |  {elapsed:.0f}ms  |  {e}")
    raise SystemExit(1)
