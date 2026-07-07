"""
Department routing + notification dispatch.
Maps each grievance category to a responsible department/authority and
sends a notification when a grievance is filed. Uses real SMTP email if
credentials are configured via environment variables, otherwise falls
back to a simulated (logged) notification so the demo always works.
"""
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

DEPARTMENTS = {
    "Roads & Traffic": {
        "name": "Public Works Department (PWD)",
        "email": "roads.grievance@pwd.gov.in",
        "icon": "🚧",
    },
    "Water & Sewage": {
        "name": "Municipal Water & Sewage Board",
        "email": "water.grievance@municipal.gov.in",
        "icon": "💧",
    },
    "Electricity & Power": {
        "name": "State Power Distribution Utility",
        "email": "power.grievance@discom.gov.in",
        "icon": "⚡",
    },
    "Public Health": {
        "name": "District Health & Sanitation Office",
        "email": "health.grievance@nrhm.gov.in",
        "icon": "🏥",
    },
}


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Attempt real email delivery via SMTP. Returns True if sent."""
    host = os.environ.get("SMTP_HOST")
    port = os.environ.get("SMTP_PORT")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")

    if not all([host, port, user, password]):
        return False  # not configured — caller will simulate instead

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email

    with smtplib.SMTP(host, int(port)) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [to_email], msg.as_string())
    return True


def notify_department(record: dict) -> dict:
    """
    Route a grievance record to the right department and notify them.
    Returns a notification log entry describing what happened.
    Uses .get() throughout so a record missing/renaming a field (e.g. across
    schema changes) never raises a KeyError.
    """
    category = record.get("category", "Public Health")
    urgency = record.get("urgency", 5)
    landmark = record.get("landmark") or record.get("area", "Unspecified")
    lat = record.get("lat", "")
    lon = record.get("lon", "")
    translated_text = record.get("translated_text", record.get("raw_text", ""))
    timestamp = record.get("timestamp", datetime.now().isoformat())
    grievance_id = record.get("id", "unknown")

    dept = DEPARTMENTS.get(category, {
        "name": "General Administration", "email": "grievance@nic.in", "icon": "📮"
    })

    subject = f"[Civic Pulse] New {category} grievance — Urgency {urgency}/10"
    body = (
        f"A new citizen grievance has been filed.\n\n"
        f"Category: {category}\n"
        f"Urgency: {urgency}/10\n"
        f"Landmark: {landmark}\n"
        f"Location: {lat}, {lon}\n"
        f"Details: {translated_text}\n"
        f"Filed at: {timestamp}\n"
    )

    sent_live = False
    try:
        sent_live = _send_email(dept["email"], subject, body)
    except Exception:
        sent_live = False

    return {
        "grievance_id": grievance_id,
        "department": dept["name"],
        "department_email": dept["email"],
        "icon": dept["icon"],
        "status": "sent" if sent_live else "simulated",
        "notified_at": datetime.now().isoformat(),
    }
