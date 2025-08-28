import re
from bs4 import BeautifulSoup
from clients.mcp_client import MCPClient
from src.extractor_mcp import extract_task_data
from src.scheduler_mcp import process_task

PROCESSED_IDS_FILE = "processed_emails.json"

import json, os
def load_processed_ids():
    if os.path.exists(PROCESSED_IDS_FILE):
        with open(PROCESSED_IDS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_processed_ids(processed_ids):
    with open(PROCESSED_IDS_FILE, "w") as f:
        json.dump(list(processed_ids), f)

def get_emails_with_tasks(graph_host="127.0.0.1", graph_port=8765, gemini_host="127.0.0.1", gemini_port=8766):
    email_client = MCPClient(host=graph_host, port=graph_port)
    processed_ids = load_processed_ids()

    emails = email_client.call("email.list", {"top": 10}) or []
    print(f"📥 Found {len(emails)} emails.")
    for brief in emails:
        msg_id = brief.get("id")
        if not msg_id or msg_id in processed_ids:
            continue
        full = email_client.call("email.get", {"id": msg_id}) or {}
        subject = full.get("subject", "(No Subject)")
        body = (full.get("body") or {}).get("content","")
        ctype = (full.get("body") or {}).get("contentType","text")

        if ctype.lower() == "html":
            soup = BeautifulSoup(body, 'html.parser')
            body = soup.get_text()

        print("📧 Subject:", subject)
        print("📝 Body:", (body or "").strip())
        print("=" * 70)

        extracted = extract_task_data(body, host=gemini_host, port=gemini_port)
        print("📌 Extracted:", extracted)

        # Schedule
        cal_client = MCPClient(host=graph_host, port=graph_port)
        process_task(cal_client, extracted)

        processed_ids.add(msg_id)
        save_processed_ids(processed_ids)
