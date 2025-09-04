# Minimal JSON-RPC TCP server exposing Gemini generate_content as MCP-style tool.
import json, os, socket, threading
from datetime import datetime

# You need: pip install google-generativeai (or google-genai for your variant)
try:
    import google.generativeai as genai
    HAS_LIB = True
except Exception:
    HAS_LIB = False

HOST = os.environ.get("MCP_GEMINI_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_GEMINI_PORT", "8766"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # set in your env

def llm_generate(model: str, prompt: str):
    if not HAS_LIB:
        raise RuntimeError("google-generativeai not installed. pip install google-generativeai")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY env var is not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    m = genai.GenerativeModel(model)
    resp = m.generate_content(prompt)
    return {"text": getattr(resp, "text", "").strip()}

def handle_request(req: dict):
    method = req.get("method")
    params = req.get("params") or {}
    if method == "llm.generate":
        return llm_generate(params.get("model","gemini-1.5-flash"), params["prompt"])
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

        # Take the last complete line for robustness
        try:
            req = json.loads(data.decode("utf-8").splitlines()[-1])
        except Exception as e:
            resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            }
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
            return

        try:
            result = handle_request(req)
            resp = {"jsonrpc": "2.0", "id": req.get("id"), "result": result}
        except Exception as e:
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "error": {"code": -32000, "message": str(e)}
            }

        conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
    finally:
        conn.close()


def run():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(20)
        print(f"[MCP-Gemini] Listening on {HOST}:{PORT}")
        while True:
            conn, _ = s.accept()
            threading.Thread(target=serve_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    run()
