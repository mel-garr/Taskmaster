import os
import time

print(f"Worker started! PID: {os.getpid()}", flush=True)

time.sleep(0.2)

print("Worker crashing intentionally!", flush=True)

exit(1)
