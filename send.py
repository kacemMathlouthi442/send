import subprocess
import time
import random
from supabase import create_client, Client

# -----------------------
# CONFIG
# -----------------------

SUPABASE_URL = "https://pqeynvgtrvihofjzcmoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBxZXludmd0cnZpaG9manpjbW9lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mjk2Mzk0NiwiZXhwIjoyMDY4NTM5OTQ2fQ.A7N8FmxOFE7wT5HenYCFsqqYZG1s0sbHSg5SZHb5CS8"

CHECK_INTERVAL = 3  # seconds between DB checks
MIN_DELAY = 3       # minimum seconds delay between SMS
MAX_DELAY = 10      # maximum seconds delay between SMS
MAX_PER_HOUR = 30   # safe limit (adjust for your SIM)

# -----------------------
# INIT
# -----------------------

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
sent_this_hour = 0
hour_start = time.time()


def send_local_sms(phone, text):
    try:
        subprocess.run(["termux-sms-send", "-n", phone, text], check=True)
        return True
    except Exception as e:
        print(f"[ERROR] SMS failed: {e}")
        return False


def throttle():
    """Apply random delay to avoid SIM detection."""
    delay = random.uniform(MMIN_DELAY, MAX_DELAY)
    print(f"[WAIT] Sleeping {delay:.1f} seconds…")
    time.sleep(delay)


def check_hour_limit():
    global sent_this_hour, hour_start
    now = time.time()

    # reset every hour
    if now - hour_start >= 3600:
        sent_this_hour = 0
        hour_start = now

    return sent_this_hour < MAX_PER_HOUR


def process_pending():
    global sent_this_hour

    if not check_hour_limit():
        print("[LIMIT] Hourly limit reached. Waiting 5 minutes…")
        time.sleep(300)
        return

    result = supabase.table("numbers").select("*").eq("status", "pending").execute()
    rows = result.data

    if not rows:
        return

    for row in rows:
        if not check_hour_limit():
            print("[LIMIT] Hourly limit reached. Pausing.")
            return

        phone = row["phone"]
        message = row["message"]

        print(f"[INFO] Sending SMS to {phone}…")

        ok = send_local_sms(phone, message)

        if ok:
            sent_this_hour += 1
            supabase.table("numbers").update({"status": "sent"}).eq("id", row["id"]).execute()
            print("[OK] SMS sent")
        else:
            print("[FAIL] SMS send error")

        throttle()  # delay between SMS


def main():
    print("📱 Safe Bulk SMS Worker Started…")
    while True:
        process_pending()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
