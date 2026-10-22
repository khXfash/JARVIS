"""Google Calendar Authorization Setup Helper.

Run this script to authorize access to your Google Calendar and generate token.json.
Make sure you have downloaded `credentials.json` from Google Cloud Console first.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def setup_calendar(credentials_file="credentials.json", token_file="token.json"):
    creds = None

    # Check if token already exists
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            print(f"Error reading {token_file}: {e}")
            creds = None

    # If there are no valid credentials available, ask the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed ({e}). Re-authorizing via browser...")
                creds = None

        if not creds or not creds.valid:
            if not os.path.exists(credentials_file):
                print(f"\n[ERROR] '{credentials_file}' not found!")
                print("Please download your OAuth client credentials JSON file from Google Cloud Console,")
                print(f"rename it to '{credentials_file}', place it in this folder, and run this script again.\n")
                return False

            print("\nStarting Google OAuth sign-in flow in your browser...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for future runs
        with open(token_file, "w") as token:
            token.write(creds.to_json())
        print(f"\n[SUCCESS] Successfully authenticated and saved '{token_file}'!")

    # Test the connection by fetching primary calendar info
    try:
        service = build("calendar", "v3", credentials=creds)
        calendar = service.calendars().get(calendarId="primary").execute()
        print(f"Connected to Google Calendar: {calendar.get('summary', 'Primary Calendar')} ({calendar.get('id')})")
        
        # Sync any appointments that were created while offline
        from db_driver import DatabaseDriver
        db = DatabaseDriver()
        synced = db.sync_unsynced_appointments()
        if synced:
            print(f"Synced {len(synced)} pending appointment(s) to Google Calendar!")
        
        print("Your receptionist agent is now ready to create and manage Google Calendar events!")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to query Google Calendar API: {e}")
        return False


if __name__ == "__main__":
    setup_calendar()
