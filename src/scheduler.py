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
    if not extracted or extracted.strip().lower() in {"(none)", "none"}:
        print("✅ No task to schedule.")
        return

    try:
        parts = [p.strip() for p in extracted.strip().strip("()").split(",")]

        # Backward compatibility: (TASK, DATE, DURATION) → treat as deadline
        if len(parts) == 3:
            task_type = "deadline"
            task, date_str, duration_str = parts
        elif len(parts) >= 4:
            task_type, task, date_str, duration_str = parts[:4]
        else:
            print(f"❌ Invalid task format: {extracted}")
            return

        task_type = task_type.lower()

        # Parse duration
        ds = duration_str.lower()
        if ds.endswith("h"):
            duration = int(float(ds[:-1]) * 60)
        elif ds.endswith("min"):
            duration = int(float(ds[:-3]))
        else:
            duration = 60
        duration = min(duration, 4 * 60)  # cap at 4 hours

        # Parse date/time
        due = date_parser.parse(date_str)

        if task_type == "meeting":
            # MUST schedule exactly on provided date/time (not before).
            # If only a date was provided (00:00), nudge to 09:00 as a sensible default.
            if due.hour == 0 and due.minute == 0:
                due = due.replace(hour=9, minute=0)
            start = due
            end = start + timedelta(minutes=duration)

            # Conflict check: if something overlaps, we still respect the instruction
            # and either fail with a clear message or you could auto-shift — here we fail.
            if event_exists(task, start, end, headers):
                return

            # Optional: you can check for overlaps and print a warning
            now = datetime.utcnow()
            url = f"https://graph.microsoft.com/v1.0/me/calendarview?startDateTime={start.isoformat()}&endDateTime={end.isoformat()}"
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                busy_ranges = [
                    (date_parser.parse(ev["start"]["dateTime"]), date_parser.parse(ev["end"]["dateTime"]))
                    for ev in res.json().get("value", [])
                ]
                overlapping = any(s < end and e > start for s, e in busy_ranges)
                if overlapping:
                    print("⚠️ Meeting time conflicts with an existing event. Not auto-moving (by design).")

        else:
            # DEADLINE: find a free slot BEFORE due date
            # If date has no time (00:00), set to 23:59 of that day to allow slots during the day.
            if due.hour == 0 and due.minute == 0:
                due = due.replace(hour=23, minute=59)

            slot = find_slot(headers, due, duration)
            if not slot:
                print("⚠️ No free slot available before the deadline.")
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
            print(f"📆 Scheduled {task_type}: {task} on {start}")
        else:
            print(f"❌ Event creation failed: {res.status_code}, {res.text}")

    except Exception as e:
        print(f"❌ Invalid task format: {extracted} → {e}")
        return
