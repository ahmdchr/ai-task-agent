import msal
import os

CLIENT_ID = '0aa6072a-91f8-4729-8018-499d07d54bbf'
AUTHORITY = 'https://login.microsoftonline.com/consumers'
SCOPE = ["Mail.Read", "Calendars.ReadWrite", "Calendars.Read"]

TOKEN_CACHE_PATH = "token_cache.bin"

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
            print("✅ Silent login successful.")
            save_cache(cache)
            return result

    flow = app.initiate_device_flow(scopes=SCOPE)
    if "message" not in flow:
        print("❌ Failed to initiate device flow:", flow)
        exit()

    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    save_cache(cache)
    return result
