import time
from src.email_mcp import get_emails_with_tasks

POLL_INTERVAL = 60

def main():
    print("🟢 AI Task Agent (MCP) is now running... (Ctrl+C to stop)")
    while True:
        try:
            get_emails_with_tasks()
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
