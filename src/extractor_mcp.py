from clients.mcp_client import MCPClient
import datetime
import time

def extract_task_data(text, retries=3, delay=5, host="127.0.0.1", port=8766):
    client = MCPClient(host=host, port=port)
    prompt = f"""
You are a Task Manager. Extract the task, due date, and estimate (max 4h).
Today's datetime is: {datetime.datetime.now().strftime("%A")} {datetime.datetime.now()}.
Return EXACTLY in this format: (TASK, YYYY-MM-DD HH:MM, DURATION)
- Use 24h time (HH:MM)
- Convert relative times like "tomorrow 3pm" to concrete date and 24h time
- If no explicit time is present, use 17:00 as a reasonable default for a deadline

EMAIL:
{text}
"""
    for attempt in range(retries):
        try:
            result = client.call("llm.generate", {"model": "gemini-2.5-flash", "prompt": prompt})
            return result.get("text","").strip()
        except Exception as e:
            print(f"⚠️ MCP Gemini error: {e}")
            if attempt < retries - 1:
                print(f"🔁 Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("❌ Failed after multiple attempts.")
                return "(NONE)"
