import argparse, urllib.request, urllib.error, json, time

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--method", default="GET")
parser.add_argument("--headers", default="{}")
parser.add_argument("--body", default="")
args = parser.parse_args()

try:
    extra_headers = json.loads(args.headers) if args.headers.strip() else {}
except json.JSONDecodeError:
    extra_headers = {}

body_bytes = args.body.encode("utf-8") if args.body.strip() else None
method = args.method.upper()

print(f"→ {method} {args.url}")
if extra_headers:
    for k, v in extra_headers.items():
        print(f"  {k}: {v}")
if body_bytes:
    print(f"\n  Body: {args.body[:200]}")
print()

headers = {"Content-Type": "application/json", "User-Agent": "Dashboard/1.0"}
headers.update(extra_headers)

req = urllib.request.Request(args.url, data=body_bytes, headers=headers, method=method)
start = time.time()

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        elapsed = (time.time() - start) * 1000
        status = resp.status
        raw = resp.read()
        body_str = raw.decode("utf-8", errors="replace")

        print(f"← {status} {resp.reason}  ({elapsed:.0f}ms)")
        print(f"   Content-Type: {resp.headers.get('Content-Type','')}")
        print(f"   Content-Length: {len(raw)} bytes\n")
        print("─── Response Body ───")
        try:
            print(json.dumps(json.loads(body_str), ensure_ascii=False, indent=2))
        except Exception:
            print(body_str[:3000])

except urllib.error.HTTPError as e:
    elapsed = (time.time() - start) * 1000
    print(f"← {e.code} {e.reason}  ({elapsed:.0f}ms)")
    try:
        print(e.read().decode("utf-8", errors="replace")[:2000])
    except Exception:
        pass
    raise SystemExit(1)
except Exception as e:
    elapsed = (time.time() - start) * 1000
    print(f"✗ Lỗi ({elapsed:.0f}ms): {e}")
    raise SystemExit(1)
