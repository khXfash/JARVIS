"""JARVIS Front-Desk Receptionist - Meetings & Schedule Dashboard Server.

Provides a rich web dashboard and REST API for monitoring, scheduling,
and managing meetings, synchronizing with Google Calendar, and reviewing
receptionist call activity.
"""

from __future__ import annotations

import datetime
import math
import os
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

from db_driver import DatabaseDriver

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.json.ensure_ascii = False
CORS(app)


@app.after_request
def add_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

db = DatabaseDriver()


def parse_iso_datetime(dt_str: str, default_tz: Optional[datetime.tzinfo] = None) -> Optional[datetime.datetime]:
    """Safely parses ISO datetime string into timezone-aware datetime."""
    if not dt_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(dt_str.strip())
        if dt.tzinfo is None:
            now_tz = default_tz or datetime.datetime.now().astimezone().tzinfo
            dt = dt.replace(tzinfo=now_tz)
        return dt
    except Exception:
        return None


def format_meeting_payload(meeting: Dict[str, Any], now: datetime.datetime) -> Dict[str, Any]:
    """Enriches a raw appointment dict with human-readable timestamps and visual badges."""
    m = dict(meeting)
    st = m.get("start_time", "")
    et = m.get("end_time", "")
    status = m.get("status", "confirmed")

    dt_start = parse_iso_datetime(st, now.tzinfo)
    dt_end = parse_iso_datetime(et, now.tzinfo)

    today_date = now.date()
    start_date = dt_start.date() if dt_start else None

    is_today = (start_date == today_date) if start_date else False
    is_tomorrow = (start_date == (today_date + datetime.timedelta(days=1))) if start_date else False
    is_yesterday = (start_date == (today_date - datetime.timedelta(days=1))) if start_date else False

    is_in_progress = False
    is_upcoming = False
    is_past = False
    timing_status = "past"
    relative_time = ""

    if dt_start and dt_end:
        duration_minutes = max(0, int((dt_end - dt_start).total_seconds() // 60))
        hours = duration_minutes // 60
        mins = duration_minutes % 60
        if hours > 0 and mins > 0:
            duration_str = f"{hours}h {mins}m"
        elif hours > 0:
            duration_str = f"{hours}h"
        else:
            duration_str = f"{mins}m"
    else:
        duration_str = "1h"

    if status == "cancelled":
        timing_status = "cancelled"
        relative_time = "Cancelled"
    elif dt_start:
        if dt_end and dt_start <= now <= dt_end:
            is_in_progress = True
            timing_status = "in_progress"
            remaining = int((dt_end - now).total_seconds() // 60)
            if remaining > 60:
                relative_time = f"In Progress • Ends in {remaining // 60}h {remaining % 60}m"
            else:
                relative_time = f"In Progress • Ends in {remaining}m"
        elif dt_start > now:
            is_upcoming = True
            timing_status = "upcoming"
            delta = dt_start - now
            total_seconds = delta.total_seconds()
            hours_away = total_seconds / 3600
            days_away = delta.days

            if total_seconds < 3600:
                mins_away = max(1, int(total_seconds // 60))
                relative_time = f"Starts in {mins_away} min"
            elif hours_away < 24 and is_today:
                relative_time = f"Today in {math.floor(hours_away)}h {int((total_seconds % 3600) // 60)}m"
            elif is_tomorrow:
                relative_time = f"Tomorrow at {dt_start.strftime('%I:%M %p')}"
            elif days_away < 7:
                relative_time = f"{dt_start.strftime('%A')} ({days_away}d away)"
            else:
                relative_time = f"In {days_away} days"
        else:
            is_past = True
            timing_status = "past"
            delta = now - dt_start
            days_ago = delta.days
            if is_today:
                relative_time = "Concluded earlier today"
            elif is_yesterday:
                relative_time = "Yesterday"
            elif days_ago < 7:
                relative_time = f"{days_ago} days ago"
            else:
                relative_time = f"{days_ago} days ago"
    else:
        is_past = True
        timing_status = "past"
        relative_time = "Recorded"

    # Client initials for visual avatar
    client_name = m.get("client_name", "Guest").strip()
    words = client_name.split()
    if len(words) >= 2:
        initials = (words[0][0] + words[1][0]).upper()
    elif len(words) == 1 and words[0]:
        initials = words[0][:2].upper()
    else:
        initials = "ME"

    # Day badge string
    if is_today:
        day_badge = "TODAY"
    elif is_tomorrow:
        day_badge = "TOMORROW"
    elif is_yesterday:
        day_badge = "YESTERDAY"
    elif dt_start:
        day_badge = dt_start.strftime("%b %d").upper()
    else:
        day_badge = "DATE"

    m.update({
        "dt_start": dt_start.isoformat() if dt_start else st,
        "dt_end": dt_end.isoformat() if dt_end else et,
        "formatted_date": dt_start.strftime("%A, %b %d, %Y") if dt_start else st,
        "short_date": dt_start.strftime("%b %d, %Y") if dt_start else st,
        "day_of_week": dt_start.strftime("%A") if dt_start else "",
        "day_badge": day_badge,
        "start_time_label": dt_start.strftime("%I:%M %p") if dt_start else "",
        "end_time_label": dt_end.strftime("%I:%M %p") if dt_end else "",
        "time_range": f"{dt_start.strftime('%I:%M %p')} – {dt_end.strftime('%I:%M %p')}" if (dt_start and dt_end) else "",
        "duration_str": duration_str,
        "timing_status": timing_status,
        "relative_time": relative_time,
        "client_initials": initials,
        "is_today": is_today,
        "is_upcoming": is_upcoming,
        "is_in_progress": is_in_progress,
        "is_past": is_past,
        "is_synced": bool(m.get("google_event_id")),
    })
    return m


@app.route("/")
def index():
    """Serves the main dashboard page."""
    return render_template("index.html")


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Returns aggregated metrics for the dashboard KPI cards."""
    now = datetime.datetime.now().astimezone()
    raw_stats = db.get_dashboard_stats()

    # Format next / active meetings if present
    next_m = raw_stats.get("next_meeting")
    if next_m:
        raw_stats["next_meeting"] = format_meeting_payload(next_m, now)

    active_m = raw_stats.get("active_meeting")
    if active_m:
        raw_stats["active_meeting"] = format_meeting_payload(active_m, now)

    return jsonify({
        "status": "success",
        "data": raw_stats,
    })


@app.route("/api/meetings", methods=["GET"])
def get_meetings():
    """Returns list of meetings with optional filters, search, and date constraints."""
    now = datetime.datetime.now().astimezone()
    filter_type = request.args.get("filter", "all").lower()
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date", "").strip()
    sort_order = request.args.get("sort", "desc").upper()

    status_filter = None
    if filter_type == "cancelled":
        status_filter = "cancelled"

    # Fetch rows from DB
    raw_meetings = db.get_all_appointments(
        status=status_filter,
        date_filter=date_filter if date_filter else None,
        search_query=search if search else None,
        order=sort_order,
        limit=200,
    )

    enriched: List[Dict[str, Any]] = []
    for r in raw_meetings:
        item = format_meeting_payload(r, now)

        # Apply in-memory timing filters if requested
        if filter_type == "today" and not item["is_today"]:
            continue
        if filter_type == "upcoming" and not (item["is_upcoming"] or item["is_in_progress"]):
            continue
        if filter_type == "past" and not item["is_past"]:
            continue
        if filter_type == "in_progress" and not item["is_in_progress"]:
            continue

        enriched.append(item)

    # Sort upcoming / today in chronological order by default if filter is upcoming/today
    if filter_type in ("upcoming", "today"):
        enriched.sort(key=lambda x: x.get("start_time", ""))

    return jsonify({
        "status": "success",
        "count": len(enriched),
        "data": enriched,
    })


@app.route("/api/meetings", methods=["POST"])
def schedule_meeting():
    """Manual scheduling endpoint is disabled to ensure dashboard remains strictly a telemetry monitor."""
    return jsonify({
        "status": "error",
        "message": "Manual scheduling is disabled. Meetings are scheduled exclusively and autonomously by the AI voice receptionist agent.",
    }), 403


@app.route("/api/meetings/<int:meeting_id>", methods=["DELETE"])
def cancel_meeting(meeting_id: int):
    """Manual cancellation endpoint is disabled."""
    return jsonify({
        "status": "error",
        "message": "Manual cancellation from the dashboard is disabled.",
    }), 403


@app.route("/api/meetings/sync", methods=["POST"])
def sync_meetings():
    """Forces sync of unsynced appointments to Google Calendar."""
    try:
        synced = db.sync_unsynced_appointments()
        return jsonify({
            "status": "success",
            "synced_count": len(synced),
            "synced": synced,
            "message": f"Successfully synchronized {len(synced)} appointment(s) with Google Calendar.",
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/call-logs", methods=["GET"])
def get_call_logs():
    """Returns recent front-desk receptionist calls."""
    logs = db.get_call_logs(limit=25)
    return jsonify({
        "status": "success",
        "count": len(logs),
        "data": logs,
    })


@app.route("/api/notes", methods=["GET"])
def get_notes():
    """Returns recorded front-desk notes."""
    notes = db.get_notes(unread_only=False, limit=25)
    return jsonify({
        "status": "success",
        "count": len(notes),
        "data": notes,
    })


@app.route("/api/health", methods=["GET"])
def health():
    """Server health status."""
    return jsonify({
        "status": "ok",
        "agent": "Nova / JARVIS Receptionist",
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  JARVIS Receptionist Meetings Dashboard Starting")
    print(f"  URL: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
