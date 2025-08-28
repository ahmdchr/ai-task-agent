from clients.mcp_client import MCPClient
from datetime import datetime, timedelta, time as dtime, date as ddate
from dateutil import parser as date_parser
from zoneinfo import ZoneInfo
import re, os, json

busy_slots = []

LOCAL_TZ = os.getenv("AGENT_TZ", "Africa/Tunis")
TAG = "[AGENT]"  # marker so we only move our own events
DB_FILE = "agent_events.json"

# New: working window + preference
WORK_START = os.getenv("AGENT_WORK_START", "09:00")  # HH:MM
WORK_END   = os.getenv("AGENT_WORK_END",   "18:00")  # HH:MM
PREFER_MORNING = os.getenv("AGENT_PREFER_MORNING", "1") in ("1","true","True","yes","YES")

def _tz():
    return ZoneInfo(LOCAL_TZ)

def _parse_hhmm(s: str) -> dtime:
    hh, mm = s.split(":")
    return dtime(int(hh), int(mm))

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

def event_exists(client: MCPClient, task, start, end):
    events = client.call("calendar.list", {
        "start": start.astimezone(ZoneInfo("UTC")).isoformat(),
        "end":   end.astimezone(ZoneInfo("UTC")).isoformat()
    })
    for ev in events:
        subj = (ev.get("subject") or "").lower()
        if subj == task.lower():
            print(f"⚠️ Event already exists: {task}")
            return True
    return False

def find_slot(client: MCPClient, due, duration, exclude_windows=None):
    """
    Search day-by-day within work hours, preferring mornings.
    - due: aware datetime in LOCAL_TZ (deadline at/before which it must fit)
    - duration: minutes
    """
    tz = _tz()
    now = datetime.now(tz)

    if due <= now:
        print("⚠️ Due date is in the past.")
        return None
    if (due - now).days > 30:
        print("⚠️ Task too far in the future, skipping.")
        return None

    # Build a quick busy map from Graph between now and due
    events = client.call("calendar.list", {
        "start": now.astimezone(ZoneInfo("UTC")).isoformat(),
        "end":   due.astimezone(ZoneInfo("UTC")).isoformat()
    }) or []

    busy_ranges = [
        (date_parser.parse(ev["start"]["dateTime"]).astimezone(tz),
         date_parser.parse(ev["end"]["dateTime"]).astimezone(tz))
        for ev in events
    ]
    busy_ranges += busy_slots
    if exclude_windows:
        busy_ranges += exclude_windows

    ws = _parse_hhmm(WORK_START)
    we = _parse_hhmm(WORK_END)
    step = timedelta(minutes=30)

    # Iterate days from today to deadline day (inclusive if time allows)
    day = now.date()
    last_day = due.date()

    while day <= last_day:
        # Day window in local tz
        day_start = datetime.combine(day, ws, tzinfo=tz)
        day_end   = datetime.combine(day, we, tzinfo=tz)

        # Clip today's window to "now"
        if day == now.date():
            day_start = max(day_start, now)

        # Clip the last day to the deadline time
        if day == last_day:
            day_end = min(day_end, due)

        if day_start < day_end:
            # If we prefer mornings, we already start from work start (earliest first).
            # Otherwise you could set PREFER_MORNING=0 and we still scan from day_start forward.
            slot_start = day_start
            while slot_start + timedelta(minutes=duration) <= day_end:
                slot_end = slot_start + timedelta(minutes=duration)
                is_busy = any(s < slot_end and e > slot_start for s, e in busy_ranges)
                if not is_busy:
                    return slot_start, slot_end
                slot_start += step

        day = ddate.fromordinal(day.toordinal() + 1)

    return None

def _build_body_meta(task, due, duration_min):
    # Put metadata in the body so we can relocate later respecting its deadline.
    meta = f"{TAG} deadline={due.isoformat()} duration_min={duration_min}"
    return {"contentType": "text", "content": meta}

def _parse_meta_from_event(event_json):
    """
    Returns (deadline: datetime|None, duration_min: int|None) if this is our event.
    Looks into event body first; fallback to DB if present.
    """
    tz = _tz()
    # Try body.content
    body = (event_json.get("body") or {}).get("content", "") or ""
    if TAG in body:
        # crude parse
        dl_match = re.search(r"deadline=([^\s]+)", body)
        du_match = re.search(r"duration_min=(\d+)", body)
        deadline = None
        duration_min = None
        if dl_match:
            try:
                deadline = date_parser.parse(dl_match.group(1))
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=tz)
            except Exception:
                pass
        if du_match:
            duration_min = int(du_match.group(1))
        return deadline, duration_min
    return None, None

def _get_full_event(client: MCPClient, event_id: str):
    try:
        return client.call("calendar.get", {"id": event_id})
    except Exception:
        return None

def _our_event_with_meta(client: MCPClient, event_stub):
    """Check if event has our TAG and extract meta by fetching full event."""
    ev_id = event_stub.get("id")
    full = _get_full_event(client, ev_id)
    if not full:
        return None
    deadline, duration_min = _parse_meta_from_event(full)
    if deadline and duration_min:
        return {
            "id": ev_id,
            "subject": full.get("subject"),
            "start": date_parser.parse(full["start"]["dateTime"]),
            "end": date_parser.parse(full["end"]["dateTime"]),
            "deadline": deadline,
            "duration_min": duration_min
        }
    return None

def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and a_end > b_start

def _try_make_room(client: MCPClient, want_start, want_end, depth=2):
    """
    Try to move our own events (with metadata) to free [want_start, want_end).
    Greedy, limited recursion depth.
    """
    tz = _tz()
    window = (want_start.astimezone(tz), want_end.astimezone(tz))
    # List all events that overlap this window
    events = client.call("calendar.list", {
        "start": want_start.astimezone(ZoneInfo("UTC")).isoformat(),
        "end":   want_end.astimezone(ZoneInfo("UTC")).isoformat()
    }) or []

    # Collect our movable events with metadata
    candidates = []
    for ev in events:
        cand = _our_event_with_meta(client, ev)
        if not cand:
            continue  # not ours, don't touch
        if not _overlaps(cand["start"].astimezone(tz), cand["end"].astimezone(tz), *window):
            continue
        candidates.append(cand)

    # Sort by slack = (deadline - current_end), smallest first (least flexible first)
    def slack(c):
        return (c["deadline"] - c["end"].astimezone(_tz())).total_seconds()
    candidates.sort(key=slack)

    for cand in candidates:
        # Try to find a new slot for cand before its own deadline
        dur = cand["duration_min"]
        exclude = [(window[0], window[1])]  # don't re-use the wanted window
        new_slot = find_slot(client, cand["deadline"].astimezone(tz), dur, exclude_windows=exclude)
        if new_slot:
            new_start, new_end = new_slot
            # Move it
            client.call("calendar.update", {
                "id": cand["id"],
                "start": new_start.isoformat(),
                "end":   new_end.isoformat(),
                "tz":    LOCAL_TZ
            })
            print(f"↪️ Moved '{cand['subject']}' to {new_start}–{new_end} to make room.")
            return True

    # If depth allows, try recursive chain move: temporarily try to move a conflicting event,
    # then see if that frees the window; if not, revert (best-effort).
    if depth > 0:
        for cand in candidates:
            dur = cand["duration_min"]
            exclude = [(window[0], window[1])]
            new_slot = find_slot(client, cand["deadline"].astimezone(tz), dur, exclude_windows=exclude)
            if not new_slot:
                # Maybe we can make room for cand itself (chain)
                c_start, c_end = cand["start"].astimezone(tz), cand["end"].astimezone(tz)
                if _try_make_room(client, c_start, c_end, depth-1):
                    # After freeing cand's own window, try again to place cand
                    new_slot2 = find_slot(client, cand["deadline"].astimezone(tz), dur, exclude_windows=exclude)
                    if new_slot2:
                        ns, ne = new_slot2
                        client.call("calendar.update", {
                            "id": cand["id"],
                            "start": ns.isoformat(),
                            "end":   ne.isoformat(),
                            "tz":    LOCAL_TZ
                        })
                        print(f"↪️ (chain) Moved '{cand['subject']}' to {ns}–{ne}.")
                        return True
    return False

def process_task(client: MCPClient, extracted):
    if not extracted or extracted.lower().strip() == "(none)":
        print("✅ No task to schedule.")
        return

    try:
        task, date_str, duration_str = [p.strip() for p in extracted.strip("()").split(",")]

        tz = _tz()
        has_time = bool(re.search(r"\d{1,2}:\d{2}", date_str))
        due = date_parser.parse(date_str)
        if due.tzinfo is None:
            due = due.replace(tzinfo=tz)
        if not has_time:
            due = due.replace(hour=17, minute=0)

        ds = duration_str.lower()
        if re.fullmatch(r"\d+(\.\d+)?", ds):
            duration = int(float(ds) * 60)   # bare number = hours
        elif ds.endswith("h"):
            duration = int(float(ds[:-1]) * 60)
        elif ds.endswith("min"):
            duration = int(float(ds[:-3]))
        else:
            duration = 60
    except Exception as e:
        print(f"❌ Invalid task format: {extracted} → {e}")
        return

    if has_time:
        start = due
        end = due + timedelta(minutes=duration)

        # direct conflict check
        events = client.call("calendar.list", {
            "start": start.astimezone(ZoneInfo("UTC")).isoformat(),
            "end":   end.astimezone(ZoneInfo("UTC")).isoformat()
        })
        if events:
            print("⚠️ Time busy. Trying to make room...")
            if not _try_make_room(client, start, end, depth=2):
                print("⛔ Could not make room without violating other deadlines.")
                return

        if event_exists(client, task, start, end):
            return

        body = _build_body_meta(task, due, duration)
        created = client.call("calendar.create", {
            "subject": task,
            "start": start.isoformat(),
            "end":   end.isoformat(),
            "tz":    LOCAL_TZ,
            "body":  body
        })
        if created:
            # store metadata locally too
            db = load_db()
            db[created["id"]] = {
                "subject": task,
                "deadline": due.isoformat(),
                "duration_min": duration,
                "tz": LOCAL_TZ
            }
            save_db(db)
            print(f"📆 Scheduled (fixed time): {task} at {start}")
    else:
        # Find a free working slot before the deadline
        slot = find_slot(client, due, duration)
        if not slot:
            print("⚠️ No free slot available. Trying to make room in the last {duration} minutes before deadline...")
            # target the last 'duration' block before the deadline
            start = (due - timedelta(minutes=duration))
            end = due
            if not _try_make_room(client, start, end, depth=2):
                print("⛔ Could not make room before deadline.")
                return
            # After making room, the desired final window should be free
            slot = (start, end)

        start, end = slot
        if event_exists(client, task, start, end):
            return

        body = _build_body_meta(task, due, duration)
        created = client.call("calendar.create", {
            "subject": task,
            "start": start.isoformat(),
            "end":   end.isoformat(),
            "tz":    LOCAL_TZ,
            "body":  body
        })
        if created:
            db = load_db()
            db[created["id"]] = {
                "subject": task,
                "deadline": due.isoformat(),
                "duration_min": duration,
                "tz": LOCAL_TZ
            }
            save_db(db)
            print(f"📆 Scheduled: {task} on {start} (before deadline {due})")
