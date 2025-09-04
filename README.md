# 🤖 AI Task Management Agent

> An intelligent agent that automatically reads tasks from your emails and schedules them into your calendar using AI-powered task extraction and smart scheduling algorithms.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green.svg)](https://modelcontextprotocol.io/)

---

## ✨ Key Features

- **📥 Email Integration** – Seamlessly connects to Outlook via Microsoft Graph API
- **🧠 AI-Powered Task Extraction** – Uses Google Gemini LLM to intelligently extract tasks, deadlines, and durations
- **📆 Smart Scheduling** – Automatically finds optimal time slots in your work schedule
- **⚡ Conflict Resolution** – Intelligently reschedules agent-managed events to avoid conflicts
- **🌍 Timezone Aware** – Fully supports local timezone handling (default: Africa/Tunis)
- **🔒 Security First** – Local MCP servers manage sensitive tokens and credentials
- **🔄 Duplicate Prevention** – Tracks processed emails to avoid scheduling the same task twice

---

## 🏗️ Architecture Overview

The system uses a **Model Context Protocol (MCP)** architecture with separate servers for different functionalities:

```
📧 Email Source (Outlook) 
    ↓
🔄 Graph MCP Server ←→ 🤖 AI Agent ←→ 🧠 Gemini MCP Server
    ↓                    ↓
📅 Calendar Events    💡 Task Extraction
```

### Components

- **Graph MCP Server** (`graph_mcp_server.py`) - Handles Microsoft Graph API interactions
- **Gemini MCP Server** (`gemini_mcp_server.py`) - Manages AI task extraction via Google Gemini
- **AI Agent** (`main_mcp.py`) - Orchestrates the entire workflow
- **Scheduler** (`scheduler_mcp.py`) - Implements intelligent scheduling algorithms

---

## 📂 Project Structure

```
ai-task-management-agent/
├── 🤖 main_mcp.py                    # Main agent orchestration
├── 📁 src/
│   ├── email_mcp.py                  # Email fetching and processing
│   ├── scheduler_mcp.py              # Smart scheduling logic
│   ├── extractor_mcp.py              # AI task extraction
│   └── clients/
│       └── mcp_client.py             # JSON-RPC MCP client
├── 🖥️ servers/
│   ├── graph_mcp_server.py           # Microsoft Graph MCP wrapper
│   └── gemini_mcp_server.py          # Google Gemini MCP wrapper
├── 📊 Data Files
│   ├── agent_events.json             # Local event database
│   ├── processed_emails.json         # Processed email tracking
│   ├── token_cache.bin               # Microsoft Graph auth cache
│   └── credentials.json              # OAuth credentials
├── 📋 requirements.txt
├── 🧪 run_testset.py                 # Testing utilities
└── 📖 README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Microsoft Azure App Registration (for Graph API)
- Google Gemini API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-task-management-agent.git
   cd ai-task-management-agent
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   
   # On Linux/macOS
   source .venv/bin/activate
   
   # On Windows
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Google Gemini Configuration
GEMINI_API_KEY="your-gemini-api-key-here"
MCP_GEMINI_HOST="127.0.0.1"
MCP_GEMINI_PORT="8766"

# Microsoft Graph Configuration
MS_CLIENT_ID="your-azure-app-registration-id"
MS_AUTHORITY="https://login.microsoftonline.com/consumers"
MS_TOKEN_CACHE="token_cache.bin"
MCP_GRAPH_HOST="127.0.0.1"
MCP_GRAPH_PORT="8765"

# Agent Preferences
AGENT_TZ="Africa/Tunis"          # Your timezone
AGENT_WORK_START="09:00"         # Work day start
AGENT_WORK_END="18:00"           # Work day end
AGENT_PREFER_MORNING="1"         # Prefer morning slots (1) or evening (0)
```

### Setup Guide

#### Microsoft Graph API Setup
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application
3. Add permissions: `Mail.Read`, `Calendars.ReadWrite`
4. Copy the Application ID to `MS_CLIENT_ID`

#### Google Gemini API Setup
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Generate an API key
3. Add it to `GEMINI_API_KEY`

---

## ▶️ Running the Agent

### Start the MCP Servers

Open two separate terminals:

**Terminal 1 - Graph Server:**
```bash
python servers/graph_mcp_server.py
```

**Terminal 2 - Gemini Server:**
```bash
python servers/gemini_mcp_server.py
```

### Launch the Agent

**Terminal 3 - Main Agent:**
```bash
python main_mcp.py
```

### Expected Output

```
🟢 AI Task Management Agent is now running... (Press Ctrl+C to stop)

📥 Scanning emails...
   Found 3 new emails to process

📧 Processing: "Project deadline reminder"
   📝 Email content: "Please complete the quarterly report by Friday 5 PM..."
   🧠 AI Analysis: Extracted task details
   📌 Task: "Complete quarterly report"
   ⏰ Deadline: 2024-03-15 17:00
   ⏱️  Duration: 3 hours
   
📅 Scheduling...
   🔍 Finding optimal time slot...
   ✅ Scheduled: March 14, 2024 at 2:00 PM - 5:00 PM
   📝 Calendar event created successfully

⏳ Next scan in 60 seconds...
```

---

## 🧪 Testing

Test the system without real emails using the provided test dataset:

```bash
# Test task extraction only
python run_testset.py --mode extract --testset test_data/sample_emails.json

# Test full scheduling workflow
python run_testset.py --mode schedule --testset test_data/sample_emails.json
```

---

## 🔧 Core Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `msal` | Microsoft Authentication | Latest |
| `requests` | HTTP client | Latest |
| `beautifulsoup4` | HTML parsing | Latest |
| `python-dateutil` | Date/time handling | Latest |
| `google-generativeai` | Gemini LLM integration | Latest |

---

## 📈 Roadmap

### Planned Features
- [ ] **Priority Levels** - Urgent vs. deep work task classification
- [ ] **SLA Monitoring** - Alerts when deadlines cannot be met
- [ ] **Team Support** - Shared mailbox and team calendar integration
- [ ] **Gmail Integration** - Support for Gmail via dedicated MCP server
- [ ] **Multi-language** - Support for non-English task extraction
- [ ] **Mobile App** - Companion mobile application
- [ ] **Analytics Dashboard** - Task completion and productivity metrics

### Version History
- **v1.0.0** - Initial release with Outlook and Gemini integration
- **v1.1.0** - Added conflict resolution and timezone support
- **v1.2.0** - Implemented MCP architecture for better modularity

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting pull requests.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🐛 Troubleshooting

### Common Issues

**Authentication Errors**
- Verify your Azure app permissions include `Mail.Read` and `Calendars.ReadWrite`
- Ensure the Gemini API key is valid and has sufficient quota

**Scheduling Conflicts**
- Check that your work hours are correctly configured
- Verify timezone settings match your location

**MCP Server Connection**
- Ensure both MCP servers are running before starting the agent
- Check that ports 8765 and 8766 are available

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Ahmed Chourou**  
Computer Science Student | Tunisia  
🚀 Building AI-powered productivity tools

[![GitHub](https://img.shields.io/badge/GitHub-Profile-black?logo=github)](https://github.com/yourusername)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://linkedin.com/in/yourprofile)

---

## 🙏 Acknowledgments

- Microsoft Graph API team for excellent documentation
- Google AI team for the powerful Gemini models
- The MCP community for protocol specifications
- Open source contributors who made this project possible

---

<div align="center">
  <p>⭐ Star this repository if it helped you automate your task management!</p>
  <p>🐛 Found a bug? <a href="https://github.com/yourusername/ai-task-management-agent/issues">Report it here</a></p>
</div>
