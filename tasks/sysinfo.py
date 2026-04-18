import platform
import os
import shutil

def bar(used, total, width=30):
    pct = used / total if total else 0
    filled = int(width * pct)
    return "[" + "█" * filled + "░" * (width - filled) + f"] {pct*100:.1f}%"

print("=" * 45)
print("  SYSTEM INFORMATION")
print("=" * 45)
print(f"  OS       : {platform.system()} {platform.release()}")
print(f"  Version  : {platform.version()[:40]}")
print(f"  Machine  : {platform.machine()}")
print(f"  Hostname : {platform.node()}")
print(f"  Python   : {platform.python_version()}")
print()

# Disk
total, used, free = shutil.disk_usage("/")
GB = 1024 ** 3
print(f"  Disk     : {used/GB:.1f} GB / {total/GB:.1f} GB")
print(f"           : {bar(used, total)}")
print(f"  Free     : {free/GB:.1f} GB")
print()

# CPU / Memory (basic without psutil)
try:
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    print(f"  CPU      : {bar(cpu, 100, 20)} ({psutil.cpu_count()} cores)")
    print(f"  RAM      : {mem.used/GB:.1f} GB / {mem.total/GB:.1f} GB")
    print(f"           : {bar(mem.used, mem.total)}")
except ImportError:
    print("  (Cài psutil để xem CPU/RAM: pip install psutil)")

print("=" * 45)
