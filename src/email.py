import requests
import json
import os
from bs4 import BeautifulSoup
from src.extractor import extract_task_data
from src.scheduler import process_task

PROCESSED_IDS_FILE = "processed_emails.json"

def load_processed_ids():
    if os.path.exists(PROCESSED_IDS_FILE):
        with open(PROCESSED_IDS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_processed_ids(processed_ids):
    with open(PROCESSED_IDS_FILE, "w") as f:
        json.dump(list(processed_ids), f)

def get_emails_with_tasks(token_data, headers):
    if "access_token" not in token_data:
        print("❌ Token missing.")
        return

    res = requests.get("https://graph.microsoft.com/v1.0/me/messages?$top=10", headers=headers)
    emails = res.json().get('value', [])

    print(f"📥 Found {len(emails)} emails.")
    processed_ids = load_processed_ids()

    for msg in emails:
        msg_id = msg['id']
        if msg_id in processed_ids:
            continue

        full_msg = requests.get(f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}", headers=headers).json()
        subject = full_msg.get('subject', '(No Subject)')
        body = full_msg['body'].get('content', '')

        if full_msg['body']['contentType'] == 'html':
            soup = BeautifulSoup(body, 'html.parser')
            body = soup.get_text()

        print("📧 Subject:", subject)
        print("📝 Body:", body.strip())
        print("=" * 70)

        task_info = extract_task_data(body)
        print("📌 Extracted:", task_info)

        # 🧠 Process the task immediately
        process_task(task_info, headers)

        # ✅ Mark email as processed
        processed_ids.add(msg_id)
        save_processed_ids(processed_ids)
