import argparse, urllib.request, json, datetime

parser = argparse.ArgumentParser()
parser.add_argument("--webhook_url", required=True)
parser.add_argument("--message", required=True)
parser.add_argument("--username", default="Dashboard Bot")
args = parser.parse_args()

payload = {
    "username": args.username,
    "text": args.message,
    "icon_emoji": ":robot_face:",
}

print(f"Gửi Slack notification")
print(f"  Username : {args.username}")
print(f"  Message  : {args.message}\n")

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    args.webhook_url,
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode()
        if body == "ok":
            print(f"✓ Đã gửi thành công lúc {datetime.datetime.now().strftime('%H:%M:%S')}")
        else:
            print(f"Response: {body}")
except Exception as e:
    print(f"✗ Lỗi: {e}")
    raise SystemExit(1)
