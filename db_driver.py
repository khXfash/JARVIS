"""Database driver and Google Calendar integration for AI Receptionist.

Handles:
1. SQLite local persistence (notes, appointments, call logs, contacts).
2. Google Calendar / Google Schedule integration for creating, listing, and cancelling events.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

logger = logging.getLogger("receptionist_db")

# Google Calendar API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False


CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _format_datetime_for_google(dt_str: str) -> Dict[str, str]:
    """Formats string date or datetime into Google Calendar start/end object."""
    dt_str = dt_str.strip()
    # Date only format (YYYY-MM-DD)
    if len(dt_str) == 10 and dt_str.count("-") == 2 and "T" not in dt_str and " " not in dt_str:
        return {"date": dt_str}

    # Normalize space to T
    if " " in dt_str and "T" not in dt_str:
        dt_str = dt_str.replace(" ", "T")

    # If no timezone offset is provided, attach the local system timezone offset
    if not (dt_str.endswith("Z") or "+" in dt_str[10:] or "-" in dt_str[10:]):
        now = datetime.datetime.now().astimezone()
        tz_offset = now.strftime("%z")
        if len(tz_offset) == 5:
            formatted_offset = tz_offset[:3] + ":" + tz_offset[3:]
            return {"dateTime": dt_str + formatted_offset}
        return {"dateTime": dt_str + "Z", "timeZone": "UTC"}

    return {"dateTime": dt_str}


class DatabaseDriver:
    def __init__(
        self,
        db_path: str = "receptionist.db",
        google_credentials_file: str = "credentials.json",
        google_token_file: str = "token.json",
    ):
        self.db_path = db_path
        self.google_credentials_file = google_credentials_file
        self.google_token_file = google_token_file
        self._init_db()
        self._calendar_service = None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes tables for receptionist operations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Notes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_name TEXT NOT NULL,
                    phone_number TEXT DEFAULT '',
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    is_urgent INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'unread',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Appointments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL,
                    client_email TEXT DEFAULT '',
                    client_phone TEXT DEFAULT '',
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    google_event_id TEXT DEFAULT '',
                    google_html_link TEXT DEFAULT '',
                    status TEXT DEFAULT 'confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Call logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_name TEXT DEFAULT 'Unknown',
                    phone_number TEXT DEFAULT '',
                    summary TEXT NOT NULL,
                    action_items TEXT DEFAULT '',
                    duration_seconds INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Contacts / Staff directory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS directory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    notes TEXT DEFAULT ''
                )
            """)

            # Seed default directory if empty
            cursor.execute("SELECT COUNT(*) as count FROM directory")
            if cursor.fetchone()["count"] == 0:
                sample_contacts = [
                    ("د. أحمد سامي", "استشاري زراعة وجراحة الأسنان", "جراحة وزراعة الأسنان", "ahmed.sami@novadental.com", "01012345671", "متاح السبت والإثنين والأربعاء من 10 صباحاً إلى 4 عصراً"),
                    ("د. سارة منصور", "أخصائية تقويم وتجميل الأسنان", "التقويم وتجميل الأسنان", "sarah.mansour@novadental.com", "01012345672", "متاحة الأحد والثلاثاء والخميس من 12 ظهراً إلى 6 مساءً"),
                    ("د. يوسف إبراهيم", "أخصائي علاج الجذور وعصب الأسنان", "حشو وعلاج الجذور", "youssef.i@novadental.com", "01012345673", "متاح يومياً ما عدا الجمعة من 1 ظهراً إلى 7 مساءً"),
                    ("د. ليلى حسن", "أخصائية أسنان الأطفال وطب الأسنان الوقائي", "أسنان الأطفال", "laila.h@novadental.com", "01012345674", "متاحة طوال أيام الأسبوع صباحاً من 9 صباحاً إلى 2 ظهراً"),
                ]
                cursor.executemany("""
                    INSERT INTO directory (name, role, department, email, phone, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, sample_contacts)

            conn.commit()

    # ==========================================
    # Google Calendar Service Helper
    # ==========================================
    def get_google_calendar_service(self):
        """Authenticates and returns the Google Calendar API service instance if configured."""
        if not GOOGLE_CALENDAR_AVAILABLE:
            return None

        if self._calendar_service:
            return self._calendar_service

        creds = None
        if os.path.exists(self.google_token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.google_token_file, CALENDAR_SCOPES)
            except Exception as e:
                logger.warning(f"Could not load token file: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(self.google_token_file, "w") as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.warning(f"Could not refresh Google token: {e}")
                    creds = None
                    # Clean up expired/revoked token file so user can re-auth
                    if os.path.exists(self.google_token_file):
                        try:
                            os.remove(self.google_token_file)
                        except OSError:
                            pass

        if creds and creds.valid:
            try:
                self._calendar_service = build("calendar", "v3", credentials=creds)
                return self._calendar_service
            except Exception as e:
                logger.error(f"Failed to build calendar service: {e}")

        return None

    # ==========================================
    # Receptionist: Notes Management
    # ==========================================
    def add_note(
        self,
        caller_name: str,
        content: str,
        phone_number: str = "",
        category: str = "general",
        is_urgent: bool = False,
    ) -> Dict[str, Any]:
        """Saves a new note or message taken by the receptionist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (caller_name, phone_number, content, category, is_urgent)
                VALUES (?, ?, ?, ?, ?)
            """, (caller_name, phone_number, content, category, 1 if is_urgent else 0))
            note_id = cursor.lastrowid
            conn.commit()
            return {
                "status": "success",
                "note_id": note_id,
                "caller_name": caller_name,
                "content": content,
                "is_urgent": is_urgent,
                "message": f"Note #{note_id} from {caller_name} successfully recorded."
            }

    def get_notes(self, unread_only: bool = False, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recorded notes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM notes"
            params = []
            if unread_only:
                query += " WHERE status = 'unread'"
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # ==========================================
    # Receptionist: Appointments & Google Schedule
    # ==========================================
    def schedule_appointment(
        self,
        client_name: str,
        start_time: str,
        end_time: str,
        title: str = "",
        description: str = "",
        client_email: str = "",
        client_phone: str = "",
    ) -> Dict[str, Any]:
        """
        Schedules an appointment in local DB and syncs to Google Calendar.
        """
        if not title:
            title = f"Appointment with {client_name}"

        google_event_id = ""
        google_html_link = ""
        calendar_sync_status = "saved_locally"

        service = self.get_google_calendar_service()
        if service:
            try:
                event_body = {
                    "summary": title,
                    "description": f"{description}\n\nClient Phone: {client_phone}\nClient Email: {client_email}".strip(),
                    "start": _format_datetime_for_google(start_time),
                    "end": _format_datetime_for_google(end_time),
                }
                if client_email:
                    event_body["attendees"] = [{"email": client_email}]

                created_event = service.events().insert(calendarId="primary", body=event_body).execute()
                google_event_id = created_event.get("id", "")
                google_html_link = created_event.get("htmlLink", "")
                calendar_sync_status = "synced_to_google_calendar"
            except Exception as e:
                logger.error(f"Google Calendar scheduling error: {e}")
                calendar_sync_status = f"local_only (Google sync failed: {str(e)})"
        else:
            calendar_sync_status = "saved_locally (Google Calendar credentials not configured)"

        # Save in local SQLite
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO appointments (
                    client_name, client_email, client_phone, title, description,
                    start_time, end_time, google_event_id, google_html_link, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_name, client_email, client_phone, title, description,
                start_time, end_time, google_event_id, google_html_link, "confirmed"
            ))
            app_id = cursor.lastrowid
            conn.commit()

            return {
                "status": "success",
                "appointment_id": app_id,
                "title": title,
                "client_name": client_name,
                "start_time": start_time,
                "end_time": end_time,
                "google_event_id": google_event_id,
                "google_link": google_html_link,
                "calendar_sync_status": calendar_sync_status,
                "message": f"Appointment successfully scheduled for {client_name} from {start_time} to {end_time}."
            }

    def sync_unsynced_appointments(self) -> List[Dict[str, Any]]:
        """Syncs all appointments that were saved locally but not yet synced to Google Calendar."""
        service = self.get_google_calendar_service()
        if not service:
            return []

        synced = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM appointments WHERE (google_event_id IS NULL OR google_event_id = '') AND status = 'confirmed'")
            rows = cursor.fetchall()
            for row in rows:
                try:
                    event_body = {
                        "summary": row["title"],
                        "description": f"{row['description']}\n\nClient Phone: {row['client_phone']}\nClient Email: {row['client_email']}".strip(),
                        "start": _format_datetime_for_google(row["start_time"]),
                        "end": _format_datetime_for_google(row["end_time"]),
                    }
                    if row["client_email"]:
                        event_body["attendees"] = [{"email": row["client_email"]}]

                    created = service.events().insert(calendarId="primary", body=event_body).execute()
                    eid = created.get("id", "")
                    link = created.get("htmlLink", "")
                    cursor.execute("UPDATE appointments SET google_event_id = ?, google_html_link = ? WHERE id = ?", (eid, link, row["id"]))
                    synced.append({"id": row["id"], "title": row["title"], "google_event_id": eid, "google_link": link})
                except Exception as e:
                    logger.error(f"Failed to sync appointment #{row['id']}: {e}")
            conn.commit()
        return synced

    def list_appointments(self, limit: int = 10, date_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists upcoming appointments from local DB."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM appointments WHERE status = 'confirmed'"
            params = []
            if date_filter:
                query += " AND start_time LIKE ?"
                params.append(f"{date_filter}%")
            query += " ORDER BY start_time ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def cancel_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Cancels an appointment in local DB and Google Calendar."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "message": f"Appointment #{appointment_id} not found."}

            event_id = row["google_event_id"]
            if event_id:
                service = self.get_google_calendar_service()
                if service:
                    try:
                        service.events().delete(calendarId="primary", eventId=event_id).execute()
                    except Exception as e:
                        logger.warning(f"Failed to delete Google Calendar event {event_id}: {e}")

            cursor.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
            conn.commit()
            return {
                "status": "success",
                "appointment_id": appointment_id,
                "message": f"Appointment #{appointment_id} has been cancelled."
            }

    def get_all_appointments(
        self,
        status: Optional[str] = None,
        date_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        order: str = "DESC",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieves appointments with optional status, date, and keyword search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM appointments WHERE 1=1"
            params: List[Any] = []
            if status and status != "all":
                query += " AND status = ?"
                params.append(status)
            if date_filter:
                query += " AND start_time LIKE ?"
                params.append(f"{date_filter}%")
            if search_query:
                query += " AND (client_name LIKE ? OR title LIKE ? OR description LIKE ? OR client_phone LIKE ? OR client_email LIKE ?)"
                sp = f"%{search_query}%"
                params.extend([sp, sp, sp, sp, sp])
            sort_dir = "ASC" if order.upper() == "ASC" else "DESC"
            query += f" ORDER BY start_time {sort_dir} LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Calculates aggregated metrics for the receptionist meetings dashboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM appointments")
            total_meetings = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM appointments WHERE status = 'confirmed'")
            confirmed_meetings = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM appointments WHERE status = 'cancelled'")
            cancelled_meetings = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM appointments WHERE google_event_id IS NOT NULL AND google_event_id != ''")
            synced_count = cursor.fetchone()["count"]

            cursor.execute("SELECT * FROM appointments WHERE status = 'confirmed' ORDER BY start_time ASC")
            confirmed_rows = [dict(r) for r in cursor.fetchall()]

        now = datetime.datetime.now().astimezone()
        today_str = now.strftime("%Y-%m-%d")

        today_count = 0
        upcoming_count = 0
        in_progress_count = 0
        past_count = 0
        next_meeting = None
        active_meeting = None

        for app in confirmed_rows:
            st = app["start_time"]
            et = app["end_time"]
            try:
                dt_start = datetime.datetime.fromisoformat(st.strip())
                if dt_start.tzinfo is None:
                    dt_start = dt_start.replace(tzinfo=now.tzinfo)
            except Exception:
                dt_start = None

            try:
                dt_end = datetime.datetime.fromisoformat(et.strip()) if et else None
                if dt_end and dt_end.tzinfo is None:
                    dt_end = dt_end.replace(tzinfo=now.tzinfo)
            except Exception:
                dt_end = None

            if dt_start:
                if dt_start.strftime("%Y-%m-%d") == today_str:
                    today_count += 1

                # In progress check
                if dt_end and dt_start <= now <= dt_end:
                    in_progress_count += 1
                    if active_meeting is None:
                        active_meeting = app
                elif dt_start >= now:
                    upcoming_count += 1
                    if next_meeting is None:
                        next_meeting = app
                else:
                    past_count += 1
            else:
                past_count += 1

        return {
            "total_meetings": total_meetings,
            "confirmed_meetings": confirmed_meetings,
            "cancelled_meetings": cancelled_meetings,
            "synced_meetings": synced_count,
            "today_meetings": today_count,
            "upcoming_meetings": upcoming_count,
            "in_progress_meetings": in_progress_count,
            "past_meetings": past_count,
            "active_meeting": active_meeting,
            "next_meeting": next_meeting or active_meeting,
            "today_date": today_str,
            "current_time": now.isoformat(),
        }

    # ==========================================
    # Receptionist: Call Logging & Contact Directory
    # ==========================================
    def log_call(
        self,
        caller_name: str,
        phone_number: str = "",
        summary: str = "",
        action_items: str = "",
        duration_seconds: int = 0,
    ) -> Dict[str, Any]:
        """Records a summary and details of a completed or ongoing call."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO call_logs (caller_name, phone_number, summary, action_items, duration_seconds)
                VALUES (?, ?, ?, ?, ?)
            """, (caller_name, phone_number, summary, action_items, duration_seconds))
            log_id = cursor.lastrowid
            conn.commit()
            return {"status": "success", "call_log_id": log_id, "caller_name": caller_name}

    def search_directory(self, query: str) -> List[Dict[str, Any]]:
        """Looks up contacts, doctors, or staff members in the company directory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            search_param = f"%{query}%"
            cursor.execute("""
                SELECT * FROM directory
                WHERE name LIKE ? OR role LIKE ? OR department LIKE ? OR notes LIKE ?
            """, (search_param, search_param, search_param, search_param))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_call_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent call logs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM call_logs ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
