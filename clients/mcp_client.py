
# clients/mcp_client.py
# A super-lightweight JSON-RPC over TCP client to talk to our local MCP servers.
# This is NOT the official MCP SDK; it's a pragmatic minimal transport for your project.
import json
import socket
import threading

class MCPClient:
    def __init__(self, host="127.0.0.1", port=8765, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._req_id = 0
        self._lock = threading.Lock()

    def call(self, method: str, params: dict|None=None):
        if params is None:
            params = {}
        with self._lock:
            self._req_id += 1
            rid = self._req_id
        req = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        data = (json.dumps(req) + "\n").encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.sendall(data)
            s.shutdown(socket.SHUT_WR)
            buf = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        if not buf:
            raise RuntimeError("Empty response from MCP server")
        lines = buf.decode("utf-8").splitlines()
        # take the last complete line
        resp = json.loads(lines[-1])
        if "error" in resp:
            raise RuntimeError(f"MCP error: {resp['error']}")
        return resp.get("result")
