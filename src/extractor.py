# extractor.py
from google import genai
import datetime
import time
client = genai.Client(api_key="AIzaSyDERfdem0xqFCgNhoqj9oRrLfDgQJOSLxA")

def extract_task_data(text,retries=3,delay=5):
    prompt = f"""
You are a Task Manager. Extract using any information thetask, the due date 
and estmate from your perspective the duration of the task(do not exceed 4 hours). 
the date and time for today is:{datetime.datetime.now().strftime("%A")} {datetime.datetime.now()}
Return in this format: (TASK, YYYY-MM-DD, DURATION)
Example: (Write report, 2025-08-10, 2h)
If no task found, return (NONE)

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
