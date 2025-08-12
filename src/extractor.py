# extractor.py
from google import genai
import os
import datetime
import time

client = genai.Client(api_key="AIzaSyDERfdem0xqFCgNhoqj9oRrLfDgQJOSLxA")

def extract_task_data(text, retries=3, delay=5):
    """
    Return one of:
      (meeting, TASK, YYYY-MM-DD HH:MM, DURATION)
      (deadline, TASK, YYYY-MM-DD, DURATION)
      (NONE)
    Notes:
      • If it's a meeting, include a time (HH:MM, 24h).
      • If it's a deadline (no explicit meeting), date only.
      • Duration max 4h, format like `1h`, `90min`, `2.5h`.
    """
    now = datetime.datetime.now()
    prompt = f"""
You are a precise Task Manager that extracts scheduling data from emails.

Today is {now.strftime("%A %Y-%m-%d %H:%M")} (local user context).

Classify the email as either a MEETING or a DEADLINE:

• MEETING: There is a call/meeting/sync/interview/class/etc. with a specific date/time or clear appointment words.
  - Output MUST include a time (HH:MM, 24h). If none is stated, infer a sensible time from context (e.g., "tomorrow morning" → 09:00).
• DEADLINE: A deliverable due by a date (report, assignment, payment, submission, etc.). No appointment to attend.
  - Output date only (no time). Do NOT invent a meeting time.

Duration:
  - Estimate how long the user likely needs blocked on their calendar (<= 4h), e.g., "1h", "90min", "2.5h".

Output STRICTLY one of:
  (meeting, TASK, YYYY-MM-DD HH:MM, DURATION)
  (deadline, TASK, YYYY-MM-DD, DURATION)
  (NONE)

Examples:
  Email: "Let's meet Wednesday 15:30 to review." → (meeting, Review session, 2025-08-13 15:30, 1h)
  Email: "Submit the draft by Friday." → (deadline, Submit draft, 2025-08-15, 2h)

EMAIL:
{text}
"""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
            if attempt < retries - 1:
                print(f"🔁 Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("❌ Failed after multiple attempts.")
                return "(NONE)"
