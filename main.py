import time
from src.auth import get_token
from src.email import get_emails_with_tasks

POLL_INTERVAL = 60

def main():
    token_data = get_token()
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    print("🟢 AI Task Agent is now running... (Ctrl+C to stop)")
    while True:
        try:
            get_emails_with_tasks(token_data, headers)  # ← fully handles per-email
            print(f"⏳ Waiting {POLL_INTERVAL} seconds...\n")
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("🛑 Stopped by user.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
