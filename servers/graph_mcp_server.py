# servers/graph_mcp_server.py
# Minimal JSON-RPC TCP server exposing Microsoft Graph as MCP-style tools.
# Adds get/update/delete so the scheduler can reshuffle events.

import json, os, socket, threading
from urllib.parse import urlencode

import requests
import msal

CLIENT_ID = os.environ.get("MS_CLIENT_ID", "0aa6072a-91f8-4729-8018-499d07d54bbf")
AUTHORITY = os.environ.get("MS_AUTHORITY", "https://login.microsoftonline.com/consumers")
SCOPE = ["Mail.Read", "Calendars.ReadWrite", "Calendars.Read"]
TOKEN_CACHE_PATH = os.environ.get("MS_TOKEN_CACHE", "token_cache.bin")

HOST = os.environ.get("MCP_GRAPH_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_GRAPH_PORT", "8765"))

# Optional: prefer a timezone for Outlook responses
PREFER_TZ = os.environ.get("AGENT_TZ", None)  # e.g., "Africa/Tunis"

def load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH, "r") as f:
            cache.deserialize(f.read())
    return cache

def save_cache(cache):
    if cache.has_state_changed:
        with open(TOKEN_CACHE_PATH, "w") as f:
            f.write(cache.serialize())

def get_token():
    cache = load_cache()
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPE, account=accounts[0])
        if result:
            save_cache(cache)
            return result

    flow = app.initiate_device_flow(scopes=SCOPE)
    if "message" not in flow:
        raise RuntimeError(f"Failed to initiate device flow: {flow}")
    print("== Microsoft login required ==")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    save_cache(cache)
    return result

def auth_headers():
    tok = get_token()
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    if PREFER_TZ:
        h["Prefer"] = f'outlook.timezone="{PREFER_TZ}"'
    return h

def list_messages(top=10):
    url = f"https://graph.microsoft.com/v1.0/me/messages?$top={int(top)}"
    res = requests.get(url, headers=auth_headers())
    res.raise_for_status()
    return res.json().get("value", [])

def get_message(msg_id: str):
    url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}"
    res = requests.get(url, headers=auth_headers())
    res.raise_for_status()
    return res.json()

def list_events(start_iso: str, end_iso: str):
    qs = urlencode({"startDateTime": start_iso, "endDateTime": end_iso})
    url = f"https://graph.microsoft.com/v1.0/me/calendarview?{qs}"
    res = requests.get(url, headers=auth_headers())
    res.raise_for_status()
    return res.json().get("value", [])

def get_event(event_id: str):
    url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
    res = requests.get(url, headers=auth_headers())
    res.raise_for_status()
    return res.json()

def create_event(subject: str, start_iso: str, end_iso: str, tz: str="UTC", body: dict|None=None):
    url = "https://graph.microsoft.com/v1.0/me/events"
    payload = {
        "subject": subject,
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": {"dateTime": end_iso, "timeZone": tz},
    }
    if body:
        payload["body"] = body  # {"contentType":"text","content":"..."}
    res = requests.post(url, headers=auth_headers(), json=payload)
    if res.status_code not in (200, 201):
        raise RuntimeError(f"Event creation failed: {res.status_code} {res.text}")
    return res.json()

def update_event_time(event_id: str, start_iso: str, end_iso: str, tz: str="UTC"):
    url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
    payload = {
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": {"dateTime": end_iso, "timeZone": tz},
    }
    res = requests.patch(url, headers=auth_headers(), json=payload)
    if res.status_code not in (200, 202):
        raise RuntimeError(f"Event update failed: {res.status_code} {res.text}")
    return res.json()

def delete_event(event_id: str):
    url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
    res = requests.delete(url, headers=auth_headers())
    if res.status_code not in (204,):
        raise RuntimeError(f"Event delete failed: {res.status_code} {res.text}")
    return {"ok": True}

# ------------ JSON-RPC TCP loop -------------
def handle_request(req: dict):
    method = req.get("method")
    params = req.get("params") or {}
    if method == "email.list":
        return list_messages(top=params.get("top", 10))
    if method == "email.get":
        return get_message(params["id"])
    if method == "calendar.list":
        return list_events(params["start"], params["end"])
    if method == "calendar.get":
        return get_event(params["id"])
    if method == "calendar.create":
        return create_event(params["subject"], params["start"], params["end"], params.get("tz","UTC"), params.get("body"))
    if method == "calendar.update":
        return update_event_time(params["id"], params["start"], params["end"], params.get("tz","UTC"))
    if method == "calendar.delete":
        return delete_event(params["id"])
    raise RuntimeError(f"Unknown method: {method}")

def serve_client(conn):
    try:
        data = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
        if not data:
            return
        req = json.loads(data.decode("utf-8").splitlines()[-1])
        try:
            result = handle_request(req)
            resp = {"jsonrpc":"2.0","id":req.get("id"),"result":result}
        except Exception as e:
            resp = {"jsonrpc":"2.0","id":req.get("id"),"error":str(e)}
        conn.sendall((json.dumps(resp)+"\n").encode("utf-8"))
    finally:
        conn.close()

def run():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(20)
        print(f"[MCP-Graph] Listening on {HOST}:{PORT}")
        while True:
            conn, _ = s.accept()
            threading.Thread(target=serve_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    run()
