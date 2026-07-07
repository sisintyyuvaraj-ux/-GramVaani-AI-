"""
Local file-based database layer for the Civic Grievance Dashboard.
Persists grievance records to database.json so data survives app reloads.
Scaled nationwide — seed data spans multiple major Indian cities.

Schema per grievance record:
  id, raw_text, translated_text, category, urgency, area, pincode, landmark,
  lat, lon, timestamp,
  status                : "Pending" | "In Progress" | "Resolved"
  deletion_state         : "None" | "Pending_Client_Approval" | "Approved"
  admin_proof            : str  — admin's action-taken text / proof image URL
  client_rejection_note  : str  — citizen's reason for rejecting a closure request
  resolved_at            : str | None — timestamp once status becomes "Resolved"
"""
import json
import os
import uuid
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "database.json")

CATEGORIES = ["Roads & Traffic", "Water & Sewage", "Electricity & Power", "Public Health"]


def _seed_data():
    """Realistic mock grievances spread across major Indian cities."""
    # (lat, lon, category, urgency, text, area/landmark, pincode)
    seed_points = [
        (28.6315, 77.2167, "Roads & Traffic", 8,
         "Major pothole cluster near Connaught Place causing traffic pileups",
         "Connaught Place, Delhi", "110001"),
        (19.1136, 72.8697, "Water & Sewage", 9,
         "Sewage overflow flooding the street near Andheri station for 3 days",
         "Andheri, Mumbai", "400053"),
        (20.3558, 85.8213, "Electricity & Power", 6,
         "Frequent power cuts in Patia IT corridor since last week",
         "Patia, Bhubaneswar", "751024"),
        (12.9716, 77.6412, "Public Health", 7,
         "Stagnant water breeding mosquitoes near Indiranagar market, dengue risk",
         "Indiranagar, Bengaluru", "560038"),
        (22.5726, 88.3639, "Roads & Traffic", 5,
         "Broken traffic signal at Park Street junction causing confusion",
         "Park Street, Kolkata", "700016"),
        (13.0827, 80.2707, "Water & Sewage", 4,
         "Low water pressure reported in T. Nagar residential blocks",
         "T. Nagar, Chennai", "600017"),
        (17.4239, 78.4738, "Electricity & Power", 9,
         "Transformer fire risk reported near Hitech City industrial estate",
         "Hitech City, Hyderabad", "500081"),
        (23.0225, 72.5714, "Public Health", 3,
         "Garbage collection delayed by 5 days in Navrangpura",
         "Navrangpura, Ahmedabad", "380009"),
        (26.9124, 75.7873, "Roads & Traffic", 6,
         "Unsafe pedestrian crossing near Malviya Nagar with no zebra markings",
         "Malviya Nagar, Jaipur", "302017"),
        (18.5204, 73.8567, "Water & Sewage", 8,
         "Contaminated drinking water complaints in Shivaji Nagar",
         "Shivaji Nagar, Pune", "411005"),
        (26.8467, 80.9462, "Electricity & Power", 5,
         "Streetlights non-functional along Hazratganj road at night",
         "Hazratganj, Lucknow", "226001"),
        (21.1702, 72.8311, "Public Health", 8,
         "Overflowing municipal dustbins causing foul smell near Adajan",
         "Adajan, Surat", "395009"),
    ]
    records = []
    now = datetime.now()
    statuses = ["Pending", "In Progress", "Resolved"]
    for i, (lat, lon, cat, urgency, text, area, pincode) in enumerate(seed_points):
        status = statuses[i % 3]
        records.append({
            "id": str(uuid.uuid4())[:8],
            "raw_text": text,
            "translated_text": text,
            "category": cat,
            "urgency": urgency,
            "area": area,
            "pincode": pincode,
            "landmark": area,
            "lat": lat,
            "lon": lon,
            "timestamp": (now - timedelta(hours=i * 3)).isoformat(),
            "status": status,
            "deletion_state": "None",
            "admin_proof": "",
            "client_rejection_note": "",
            "resolved_at": (now - timedelta(hours=i)).isoformat() if status == "Resolved" else None,
        })
    return records


def load_db():
    """Load the database, backfilling any missing keys on every record so
    older/partial data never crashes the app."""
    if not os.path.exists(DB_PATH):
        data = {"grievances": _seed_data(), "notifications": []}
        save_db(data)
        return data
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("notifications", [])
    for g in data.get("grievances", []):
        g.setdefault("status", "Pending")
        g.setdefault("deletion_state", "None")
        g.setdefault("admin_proof", "")
        g.setdefault("client_rejection_note", "")
        g.setdefault("resolved_at", None)
        g.setdefault("area", g.get("landmark", "Unspecified"))
        g.setdefault("pincode", "")
        g.setdefault("landmark", g.get("area", "Unspecified"))
    return data


def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_grievance(record):
    record.setdefault("status", "Pending")
    record.setdefault("deletion_state", "None")
    record.setdefault("admin_proof", "")
    record.setdefault("client_rejection_note", "")
    record.setdefault("resolved_at", None)
    record.setdefault("area", record.get("landmark", "Unspecified"))
    record.setdefault("pincode", "")
    record.setdefault("landmark", record.get("area", "Unspecified"))
    data = load_db()
    data["grievances"].append(record)
    save_db(data)
    return data


def get_all():
    """Always reads fresh from disk — no caching layer — so submissions filed
    in one role instantly appear when switching to the other role."""
    return load_db()["grievances"]


def get_export_data():
    """
    Returns the full, unfiltered grievance list for governance/compliance
    export purposes (e.g. the Admin's CSV audit ledger download). This is
    intentionally a thin alias over get_all() — no schema changes — kept as
    a separate named entry point so export logic in app.py has a stable,
    self-documenting call site independent of internal data-access changes.
    """
    return get_all()


def update_status(grievance_id, new_status):
    """Manual status update by admin (Pending / In Progress only — Resolved is
    reached exclusively through the citizen-approved deletion workflow)."""
    data = load_db()
    for g in data["grievances"]:
        if g["id"] == grievance_id:
            g["status"] = new_status
            break
    save_db(data)
    return data


def update_deletion_workflow(grievance_id, deletion_state, admin_proof="", status=None, rejection_note=""):
    """
    Re-reads the JSON file, updates the target grievance's workflow fields,
    and writes it back immediately.

    Called by:
      - Admin, requesting closure: deletion_state="Pending_Client_Approval",
        admin_proof=<text>, status="In Progress"
      - Citizen, approving:        deletion_state="Approved", status="Resolved"
      - Citizen, rejecting:        deletion_state="None", status="Pending",
        rejection_note=<reason>

    status=None leaves the current status untouched. The record is NEVER
    erased from the database — only its state flags change.
    """
    data = load_db()
    for g in data["grievances"]:
        if g["id"] == grievance_id:
            g["deletion_state"] = deletion_state
            g["admin_proof"] = admin_proof
            if status is not None:
                g["status"] = status
            g["client_rejection_note"] = rejection_note
            if status == "Resolved":
                g["resolved_at"] = datetime.now().isoformat()
            break
    save_db(data)
    return data


def add_notification(log_entry):
    data = load_db()
    data["notifications"].append(log_entry)
    save_db(data)
    return data


def get_notifications():
    return load_db()["notifications"]
