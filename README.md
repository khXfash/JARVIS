# JARVIS - AI Voice Receptionist & Dashboard

An intelligent AI receptionist system powered by LiveKit and Google Gemini, featuring real-time conversational voice handling, automated appointment scheduling with Google Calendar, call analytics, and an interactive web dashboard.

---

## 🌟 Features

- **Real-Time Voice Agent**: Powered by LiveKit agents and Google Gemini.
- **Calendar Integration**: Google Calendar OAuth integration for automated appointment booking and scheduling checks.
- **Full Call Analytics & Logging**: Stores caller history, call logs, full transcripts, and appointment details in SQLite.
- **Interactive Web Dashboard**: Monitor active calls, call volume, booked appointments, and review call transcripts.
- **SIP / Telephony Support**: Integration-ready with LiveKit SIP inbound trunks (e.g., Twilio).

---

## 📁 Project Structure

```text
JARVIS/
├── agent.py                 # LiveKit Voice Assistant worker & tool definitions
├── api.py                   # Inbound webhook & SIP dispatch API server
├── dashboard_server.py       # Web dashboard backend
├── db_driver.py             # Database access layer for SQLite (calls, transcripts, appointments)
├── prompts.py               # AI receptionist system instructions & persona
├── setup_google_calendar.py # Script for Google Calendar OAuth authentication
├── requirements.txt         # Python dependencies
├── templates/               # Dashboard HTML templates
├── static/                  # CSS stylesheets and client-side JavaScript
├── .env.example             # Template for required environment variables
└── .gitignore               # Git ignore rules for secrets, DB, and virtual environment
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- A [LiveKit Cloud](https://livekit.io/) account
- A [Google Gemini API Key](https://aistudio.google.com/)
- (Optional) Google Cloud Console project with Calendar API enabled for calendar booking

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/<your-username>/JARVIS.git
cd JARVIS

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the sample environment file and fill in your credentials:
```bash
cp .env.example .env
```
Edit `.env`:
```env
LIVEKIT_URL="wss://your-project.livekit.cloud"
LIVEKIT_API_KEY="your_api_key_here"
LIVEKIT_API_SECRET="your_api_secret_here"
GOOGLE_API_KEY="your_google_api_key_here"
```

### 4. Google Calendar Setup (Optional)
Place your `credentials.json` from Google Cloud Console in the root folder, then run:
```bash
python setup_google_calendar.py
```
This generates `token.json` for authorized calendar management.

### 5. Running the Application
- **LiveKit Agent**:
  ```bash
  python agent.py dev
  ```
- **SIP Dispatch API**:
  ```bash
  python api.py
  ```
- **Web Dashboard**:
  ```bash
  python dashboard_server.py
  ```
