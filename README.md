# 📅 AI Task Management Agent (MCP)

An intelligent agent that **reads tasks from emails** and **schedules them automatically into your calendar**.  
Built with **Microsoft Graph**, **Google Gemini LLM**, and a **lightweight MCP (Model Context Protocol)** architecture.

---

## 🚀 Features
- 📥 **Email Integration** – fetches emails from Outlook (via Microsoft Graph).  
- 🤖 **Task Extraction** – uses Gemini LLM to extract `(Task, Deadline, Duration)` tuples.  
- 📆 **Smart Scheduling** – finds the first free work slot before the deadline and creates calendar events.  
- ⚡ **Conflict Handling** – attempts to reschedule agent-managed events (`[AGENT]` tagged) to make room.  
- 🌍 **Timezone Awareness** – respects local timezone (`Africa/Tunis` by default).  
- 🔒 **Secure** – local MCP servers handle secrets & tokens; the agent only sees JSON-RPC calls.  

---

## 🛠️ Architecture

Emails (Graph API)
│
▼
📧 Graph MCP Server ←→ Agent Loop (main_mcp.py) ←→ Gemini MCP Server 🤖
│ │
▼ ▼
Calendar (Graph API) LLM Task Extraction

- **Graph MCP Server (`graph_mcp_server.py`)**  
  Exposes `email.list`, `email.get`, `calendar.list`, `calendar.create`, etc.  
- **Gemini MCP Server (`gemini_mcp_server.py`)**  
  Exposes `llm.generate` for LLM-based task extraction.  
- **Agent (`main_mcp.py`)**  
  - Calls `email.list` → `email.get`.  
  - Sends body to `llm.generate`.  
  - Runs `scheduler_mcp.find_slot` + `calendar.create`.

---

## 📂 Project Structure

.
├── main_mcp.py # Agent loop
├── src/
│ ├── email_mcp.py # Fetch emails + extract tasks
│ ├── scheduler_mcp.py # Scheduling logic (find_slot, make-room)
│ ├── extractor_mcp.py # Task extraction with Gemini
│ ├── clients/
│ │ └── mcp_client.py # JSON-RPC client
├── servers/
│ ├── graph_mcp_server.py # MCP wrapper for Microsoft Graph
│ ├── gemini_mcp_server.py # MCP wrapper for Gemini
├── agent_events.json # Local DB of scheduled events
├── processed_emails.json # Prevents reprocessing same email
├── token_cache.bin # Microsoft Graph auth cache
├── credentials.json # OAuth client credentials
├── token.json # Gmail/Gemini token
└── README.md # (you are here)

---

## ⚙️ Setup & Installation

### 1. Clone repo
```bash
git clone https://github.com/yourusername/ai-task-agent.git
cd ai-task-agent
```
### 2. Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```
### 3. Install dependencies
```bash
pip install -r requirements.txt
```
Core packages used:

msal (Microsoft Authentication Library)

requests

beautifulsoup4

python-dateutil

google-generativeai

## 🔑 Environment Variables
### Configure your .env or export variables manually:
```bash
# --- Gemini MCP ---
export GEMINI_API_KEY="your-gemini-api-key"
export MCP_GEMINI_HOST="127.0.0.1"
export MCP_GEMINI_PORT="8766"

# --- Microsoft Graph MCP ---
export MS_CLIENT_ID="your-azure-app-id"
export MS_AUTHORITY="https://login.microsoftonline.com/consumers"
export MS_TOKEN_CACHE="token_cache.bin"
export MCP_GRAPH_HOST="127.0.0.1"
export MCP_GRAPH_PORT="8765"

# --- Agent preferences ---
export AGENT_TZ="Africa/Tunis"
export AGENT_WORK_START="09:00"
export AGENT_WORK_END="18:00"
export AGENT_PREFER_MORNING="1"

```

## ▶️ Running the Agent
### 1. Start MCP Servers
```bash
# Terminal A
python graph_mcp_server.py

# Terminal B
python gemini_mcp_server.py

```
### 2. Run the Agent
```bash
python main_mcp.py
```
### Sample output:
```bash
🟢 AI Task Agent (MCP) is now running... (Ctrl+C to stop)
📥 Found 5 emails.
📧 Subject: Report due tomorrow
📝 Body: Please send the report by tomorrow.
📌 Extracted: (Submit report, 2025-08-30 17:00, 2h)
📆 Scheduled: Submit report on 2025-08-30 14:00
⏳ Waiting 60 seconds...
```
## 🧪 Testing with a Dataset
### You can simulate emails without Outlook by using the included test set:
```bash
python run_testset.py --mode schedule --testset ai_task_agent_test_set.json
```
## 📅 Roadmap

 Add task priority levels (urgent vs deep work).

 SLA alerts when deadlines cannot be met.

 Shared/team mailbox support.

 Support for Gmail API via a Gmail MCP server.
 
## 👨‍💻 Author
 
### Ahmed Chourou – Computer Science Student, Tunisia
### Building AI-powered productivity tools.

## 📜 License
### MIT License – feel free to use and adapt.
