import requests
from datetime import datetime, timedelta
from dateutil import parser as date_parser

# Track used time slots during current run
busy_slots = []

def event_exists(task, start, end, headers):
    url = f"https://graph.microsoft.com/v1.0/me/calendarview?startDateTime={start.isoformat()}&endDateTime={end.isoformat()}"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print("❌ Failed to check existing events.")
        return False

    for event in res.json().get("value", []):
        if event['subject'].lower() == task.lower():
            print(f"⚠️ Event already exists: {task}")
            return True
    return False


def find_slot(headers, due, duration):
    now = datetime.utcnow()
    if due <= now:
        print("⚠️ Due date is in the past.")
        return None

    if (due - now).days > 30:
        print("⚠️ Task too far in the future, skipping.")
        return None

    url = f"https://graph.microsoft.com/v1.0/me/calendarview?startDateTime={now.isoformat()}&endDateTime={due.isoformat()}"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print("❌ Error fetching events for busy check.")
        return None

    busy_ranges = [
        (date_parser.parse(ev["start"]["dateTime"]), date_parser.parse(ev["end"]["dateTime"]))
        for ev in res.json().get("value", [])
    ]

    slot_start = now
    while slot_start + timedelta(minutes=duration) <= due:
        slot_end = slot_start + timedelta(minutes=duration)
        is_busy = any(start < slot_end and end > slot_start for start, end in busy_ranges + busy_slots)

        if not is_busy:
            return slot_start, slot_end

        slot_start += timedelta(minutes=30)

    return None


def process_task(extracted, headers):
    if not extracted or extracted.lower().strip() == "(none)":
        print("✅ No task to schedule.")
        return

    try:
        task, date_str, duration_str = [p.strip() for p in extracted.strip("()").split(",")]
        due = date_parser.parse(date_str)

        if due.hour == 0:
            due = due.replace(hour=23, minute=59)

        if duration_str.lower().endswith("h"):
            duration = int(float(duration_str[:-1]) * 60)
        elif duration_str.lower().endswith("min"):
            duration = int(float(duration_str[:-3]))
        else:
            duration = 60

    except Exception as e:
        print(f"❌ Invalid task format: {extracted} → {e}")
        return

    slot = find_slot(headers, due, duration)
    if not slot:
        print("⚠️ No free slot available.")
        return

    start, end = slot

    if event_exists(task, start, end, headers):
        return

    busy_slots.append((start, end))  # block slot for this run

    event = {
        "subject": task,
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"}
    }

    res = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=event)
    if res.status_code == 201:
        print(f"📆 Scheduled: {task} on {start}")
    else:
        print(f"❌ Event creation failed: {res.status_code}, {res.text}")