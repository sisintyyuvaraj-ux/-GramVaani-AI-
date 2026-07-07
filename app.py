"""
Civic Pulse — Real-Time People's Priorities Dashboard
Track 01: Civic & Governance — Nationwide India Edition (Cinematic Build)

Visual overhaul notes:
  - The immersive background is now the studio-rendered "Data Particles
    Flow Into Dashboard" cinematic clip, base64-embedded locally (no CDN
    fetch, zero network risk) and rendered via a fixed, hardware-accelerated
    <video> element sitting at z-index:-100 beneath a soft velvet scrim so
    on-screen text stays legible.
  - All backend logic, data models, and st.form closures are unchanged
    from the previous build — this revision is presentation-layer only.

Run with: streamlit run app.py
"""
from datetime import datetime
from pathlib import Path
import base64
import io
import uuid

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import database as db
from ai_engine import parse_grievance, CATEGORIES
from notify import notify_department, DEPARTMENTS

st.set_page_config(page_title="Civic Pulse | Nationwide Dashboard", layout="wide", page_icon="🏛️")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

INDIA_CENTER_LAT = 20.5937
INDIA_CENTER_LON = 78.9629
INDIA_DEFAULT_ZOOM = 4

# Neon aura category palette (color, glow, css-safe class suffix)
CATEGORY_META = {
    "Roads & Traffic": {"icon": "🚧", "color": "#FF9100", "glow": "rgba(255,145,0,0.3)"},
    "Water & Sewage": {"icon": "💧", "color": "#00E5FF", "glow": "rgba(0,229,255,0.3)"},
    "Electricity & Power": {"icon": "⚡", "color": "#FFEA00", "glow": "rgba(255,234,0,0.3)"},
    "Public Health": {"icon": "🏥", "color": "#FF1744", "glow": "rgba(255,23,68,0.3)"},
}

# Canned resolution log snippets for the admin's quick-fill pills
QUICK_LOG_SNIPPETS = [
    "Pothole filled and resurfaced.",
    "Streetlight repaired and tested.",
    "Sewage line cleared and flushed.",
    "Transformer inspected and secured.",
    "Garbage backlog cleared on-site.",
    "Water supply pressure restored.",
]


def urgency_color(u):
    if u >= 8:
        return "#FF1744"
    if u >= 5:
        return "#FFEA00"
    return "#00E5FF"


# =========================================================
# HYPER-PREMIUM CINEMATIC VIDEO BACKGROUND (local asset, zero CDN risk)
# =========================================================
@st.cache_resource
def _load_bg_video_b64():
    video_path = Path(__file__).parent / "assets" / "bg_video.mp4"
    with open(video_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def render_video_background():
    b64 = _load_bg_video_b64()
    st.markdown(f"""
    <video autoplay loop muted playsinline id="bg-video">
        <source src="data:video/mp4;base64,{b64}" type="video/mp4">
    </video>
    <div id="bg-scrim"></div>
    <style>
    #bg-video {{
        position: fixed; right: 0; bottom: 0; min-width: 100%; min-height: 100%;
        z-index: -100; object-fit: cover; background: #000000;
    }}
    /* Force native Streamlit layers transparent so the video plays through */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMainBlockContainer"] {{
        background-color: transparent !important;
    }}
    /* Velvet scrim: keeps typography legible over moving particles without
       flattening the cinematic depth of the clip */
    #bg-scrim {{
        position: fixed; inset: 0; z-index: -99; pointer-events: none;
        background:
            radial-gradient(ellipse at top, rgba(5,8,17,0.20) 0%, rgba(5,8,17,0.82) 68%, rgba(5,8,17,0.94) 100%);
    }}
    </style>
    """, unsafe_allow_html=True)


render_video_background()


# =========================================================
# GLOBAL GLASSMORPHISM CSS OVERRIDES — HYPER-PREMIUM CINEMATIC SYSTEM
# =========================================================
st.markdown(f"""
<style>
html, body, .stApp {{
    background: transparent !important;
}}
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background: transparent !important;
}}

/* Premium type rhythm — tighter tracking on headers, airy body copy */
h1, h2, h3, .section-title {{ letter-spacing: -0.01em; }}
body, p, span, div {{ font-feature-settings: "ss01"; }}

/* Floating translucent glass panels */
.todo-card, .metric-card, .handshake-box, .audit-block,
[data-testid="stExpander"], [data-testid="stForm"] {{
    background: linear-gradient(160deg, rgba(14,18,36,0.55), rgba(8,11,22,0.42)) !important;
    backdrop-filter: blur(26px) saturate(190%) !important;
    -webkit-backdrop-filter: blur(26px) saturate(190%) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 20px !important;
    padding: 16px 18px;
    margin-bottom: 14px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04);
    transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

/* Fluid hover trajectories */
.todo-card:hover, .metric-card:hover, [data-testid="stExpander"]:hover {{
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 24px 60px rgba(0, 229, 255, 0.16), inset 0 1px 0 rgba(255,255,255,0.06);
    border-color: rgba(0, 229, 255, 0.45) !important;
}}

.stButton>button {{
    border-radius: 14px !important;
    font-weight: 700 !important;
    background: linear-gradient(160deg, rgba(20,25,46,0.7), rgba(10,15,30,0.55)) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    color: #e5e9f5 !important;
    letter-spacing: 0.01em;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}
.stButton>button:hover {{
    transform: translateY(-4px) scale(1.03);
    box-shadow: 0 18px 44px rgba(0, 229, 255, 0.22);
    border-color: rgba(0, 229, 255, 0.55) !important;
}}
.stButton>button[kind="primary"] {{
    background: linear-gradient(135deg, rgba(0,229,255,0.22), rgba(157,78,221,0.22)) !important;
    border-color: rgba(157,78,221,0.5) !important;
}}

.metric-label {{color:#8b93ad;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;}}
.metric-value {{color:#f4f6fb;font-size:32px;font-weight:800;margin-top:4px;text-shadow:0 0 18px rgba(0,229,255,0.25);}}
.section-title {{
    font-size:22px;font-weight:800;color:#f4f6fb;margin:6px 0 10px 0;
    text-shadow:0 0 14px rgba(157,78,221,0.28);
    position: relative; padding-left: 14px;
}}
.section-title::before {{
    content: ""; position:absolute; left:0; top:4px; bottom:4px; width:4px;
    border-radius:4px; background: linear-gradient(180deg, #00E5FF, #9D4EDD);
    box-shadow: 0 0 10px rgba(0,229,255,0.6);
}}

/* Neon glass category badges */
.aura-badge {{
    display:inline-flex; align-items:center; gap:6px;
    padding: 5px 14px; border-radius: 999px; font-size: 12px; font-weight: 700;
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(8px);
}}

/* Horizontal progress pipeline */
.pipeline {{ display:flex; align-items:center; gap:6px; margin-top:10px; font-size:11px; }}
.pipeline .stage {{
    padding:4px 10px; border-radius:8px; color:#5b6478;
    border:1px solid rgba(255,255,255,0.07); white-space:nowrap;
}}
.pipeline .stage.active {{
    color:#050811; font-weight:800;
    background: linear-gradient(135deg, #00E5FF, #9D4EDD);
    box-shadow: 0 0 16px rgba(0,229,255,0.55);
    border: none;
}}
.pipeline .connector {{ color:#33394d; }}

/* Slim premium scrollbar to match the velvet aesthetic */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: linear-gradient(180deg, #00E5FF, #9D4EDD);
    border-radius: 10px; border: 2px solid rgba(5,8,17,0.9);
}}
</style>
""", unsafe_allow_html=True)

# =========================================================
# GLOBAL GLASSMORPHISM CSS OVERRIDES
# =========================================================
st.markdown(f"""
<style>
.stApp {{
    background: transparent !important;
}}
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background: transparent !important;
}}

/* Floating translucent glass panels */
.todo-card, .metric-card, .handshake-box, .audit-block,
[data-testid="stExpander"], [data-testid="stForm"] {{
    background: rgba(10, 15, 30, 0.4) !important;
    backdrop-filter: blur(24px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
    border: 1px solid rgba(255, 255, 255, 0.04) !important;
    border-radius: 20px !important;
    padding: 16px 18px;
    margin-bottom: 14px;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

/* Fluid hover trajectories */
.todo-card:hover, .metric-card:hover, [data-testid="stExpander"]:hover {{
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 20px 50px rgba(0, 229, 255, 0.12);
    border-color: rgba(0, 229, 255, 0.4) !important;
}}
.stButton>button {{
    border-radius: 14px !important;
    font-weight: 700 !important;
    background: rgba(10, 15, 30, 0.55) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #e5e9f5 !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}
.stButton>button:hover {{
    transform: translateY(-4px) scale(1.03);
    box-shadow: 0 16px 40px rgba(0, 229, 255, 0.18);
    border-color: rgba(0, 229, 255, 0.5) !important;
}}

.metric-label {{color:#8b93ad;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;}}
.metric-value {{color:#f4f6fb;font-size:32px;font-weight:800;margin-top:4px;text-shadow:0 0 18px rgba(0,229,255,0.25);}}
.section-title {{font-size:22px;font-weight:800;color:#f4f6fb;margin:6px 0 10px 0;text-shadow:0 0 12px rgba(157,78,221,0.25);}}

/* Neon glass category badges */
.aura-badge {{
    display:inline-flex; align-items:center; gap:6px;
    padding: 5px 14px; border-radius: 999px; font-size: 12px; font-weight: 700;
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(6px);
}}

/* Horizontal progress pipeline */
.pipeline {{ display:flex; align-items:center; gap:6px; margin-top:10px; font-size:11px; }}
.pipeline .stage {{
    padding:4px 10px; border-radius:8px; color:#5b6478;
    border:1px solid rgba(255,255,255,0.06); white-space:nowrap;
}}
.pipeline .stage.active {{
    color:#050811; font-weight:800;
    background: linear-gradient(135deg, #00E5FF, #9D4EDD);
    box-shadow: 0 0 14px rgba(0,229,255,0.5);
    border: none;
}}
.pipeline .connector {{ color:#33394d; }}
</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE / LOGIN GATE
# =========================================================
if "role" not in st.session_state:
    st.session_state.role = None  # None | "citizen" | "admin"


def login_gate():
    st.markdown("## 🏛️ Civic Pulse — Nationwide People's Priorities Dashboard")
    st.caption("Real-time geo-spatial grievance intelligence · Across India")
    st.write("")

    choice = st.selectbox(
        "Select portal", ["Citizen Portal", "Administrative Hub"], key="portal_choice"
    )

    if choice == "Citizen Portal":
        if st.button("Enter Citizen Portal", type="primary", use_container_width=True, key="enter_citizen_btn"):
            st.session_state.role = "citizen"
            st.rerun()
    else:
        with st.form(key="admin_login_form", clear_on_submit=False):
            u = st.text_input("Username", key="admin_login_user")
            p = st.text_input("Password", type="password", key="admin_login_pass")
            submit_login = st.form_submit_button("Log In", type="primary", use_container_width=True)
            if submit_login:
                if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error("Invalid admin credentials.")
        st.caption("Demo admin credentials: `admin` / `admin123`")


if st.session_state.role is None:
    login_gate()
    st.stop()

# ---------- Top bar with logout ----------
top_l, top_r = st.columns([5, 1])
with top_l:
    role_label = "🛡️ Administrative Hub" if st.session_state.role == "admin" else "🗣️ Citizen Portal"
    st.markdown(f"## 🏛️ Civic Pulse — {role_label}")
    st.caption("Real-time geo-spatial grievance intelligence · Across India")
with top_r:
    st.write("")
    if st.button("🚪 Log Out", use_container_width=True, key="logout_btn"):
        st.session_state.role = None
        st.rerun()

st.divider()


def render_aura_badge(category):
    meta = CATEGORY_META.get(category, {"icon": "📮", "color": "#9D4EDD", "glow": "rgba(157,78,221,0.3)"})
    return (
        f'<span class="aura-badge" style="color:{meta["color"]};'
        f'border:1px solid {meta["color"]};box-shadow:0 0 10px {meta["glow"]};">'
        f'{meta["icon"]} {category}</span>'
    )


def render_pipeline(status, deletion_state):
    if status == "Resolved":
        active_idx = 3
    elif deletion_state == "Pending_Client_Approval":
        active_idx = 2
    elif status == "In Progress":
        active_idx = 1
    else:
        active_idx = 0

    stages = ["📥 LOGGED", "✨ TRIAGE", "🔮 VERIFICATION", "🌌 RESOLVED"]
    parts = []
    for i, s in enumerate(stages):
        cls = "stage active" if i == active_idx else "stage"
        parts.append(f'<span class="{cls}">{s}</span>')
        if i < len(stages) - 1:
            parts.append('<span class="connector">───</span>')
    return f'<div class="pipeline">{"".join(parts)}</div>'


def render_dark_map(map_df, empty_caption=True):
    """Plotly scatter_mapbox on the free carto-darkmatter basemap — replaces
    the previous st.map for a cinematic, high-fidelity telemetry feel."""
    if map_df.empty:
        if empty_caption:
            st.info(f"No data in the current filter — map centered on India (zoom {INDIA_DEFAULT_ZOOM}).")
        fig = go.Figure(go.Scattermapbox(
            lat=[INDIA_CENTER_LAT], lon=[INDIA_CENTER_LON],
            mode="markers", marker=dict(size=10, color="#00E5FF"),
        ))
        fig.update_layout(
            mapbox=dict(style="carto-darkmatter", center=dict(lat=INDIA_CENTER_LAT, lon=INDIA_CENTER_LON),
                        zoom=INDIA_DEFAULT_ZOOM),
            margin=dict(t=0, b=0, l=0, r=0), height=440,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        return

    center_lat = map_df["lat"].mean()
    center_lon = map_df["lon"].mean()
    st.caption(f"📍 Viewport auto-focused near ({center_lat:.3f}, {center_lon:.3f}) — the mean of the active dataset.")

    color_map = {k: v["color"] for k, v in CATEGORY_META.items()}
    fig = go.Figure()
    for cat, sub in map_df.groupby("category"):
        fig.add_trace(go.Scattermapbox(
            lat=sub["lat"], lon=sub["lon"], mode="markers",
            marker=dict(size=sub["urgency"] * 2.4, color=color_map.get(cat, "#9D4EDD"), opacity=0.85),
            name=cat,
            text=sub.apply(lambda r: f"{r['landmark']} · Urgency {r['urgency']}/10", axis=1),
            hoverinfo="text",
        ))
    fig.update_layout(
        mapbox=dict(style="carto-darkmatter", center=dict(lat=center_lat, lon=center_lon), zoom=4.2),
        margin=dict(t=0, b=0, l=0, r=0), height=460,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(bgcolor="rgba(10,15,30,0.6)", font=dict(color="#e5e9f5")),
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# CITIZEN PORTAL
# =========================================================
def citizen_view():
    df = pd.DataFrame(db.get_all())  # fresh from disk at the very top of this view

    tab_submit, tab_feed = st.tabs(["📝 File a New Grievance", "📡 Recent Submissions & Active Triage"])

    # ---------- Filing form ----------
    with tab_submit:
        st.markdown('<div class="section-title">🗣️ Describe Your Issue</div>', unsafe_allow_html=True)
        st.caption("Speak or type in any Indian language / dialect — our AI understands.")

        raw_text = st.text_area(
            "Describe your grievance",
            placeholder="e.g. Yahan sadak me bada gadha hai... / রাস্তায় বড় গর্ত আছে... / ரோட்டில் பெரிய குழி இருக்கு...",
            height=150, key="new_grievance_text"
        )
        st.markdown("**📍 Your Location**")
        g1, g2 = st.columns(2)
        area = g1.text_input("Area / Locality Name", placeholder="e.g. Andheri, Mumbai", key="new_grievance_area")
        pincode = g2.text_input("6-Digit Postal Pincode", placeholder="e.g. 400053", max_chars=6, key="new_grievance_pincode")

        if st.button("🚀 Submit Grievance", use_container_width=True, type="primary", key="submit_grievance_btn"):
            if not raw_text.strip():
                st.warning("Please describe your issue before submitting.")
            elif not area.strip() or not pincode.strip():
                st.warning("Please enter both your Area/Locality name and 6-digit Pincode.")
            elif not (pincode.strip().isdigit() and len(pincode.strip()) == 6):
                st.warning("Pincode must be exactly 6 digits.")
            else:
                with st.spinner("AI is analyzing your grievance and locating your area..."):
                    try:
                        parsed = parse_grievance(raw_text, area, pincode)
                        record = {
                            "id": str(uuid.uuid4())[:8],
                            "raw_text": raw_text,
                            "translated_text": parsed["translated_text"],
                            "category": parsed["category"],
                            "urgency": parsed["urgency"],
                            "area": area,
                            "pincode": pincode,
                            "landmark": parsed["landmark"],
                            "lat": parsed["lat"],
                            "lon": parsed["lon"],
                            "timestamp": datetime.now().isoformat(),
                        }
                        db.add_grievance(record)
                        meta = CATEGORY_META.get(parsed["category"], {})
                        st.success(f"✅ Filed under **{meta.get('icon','')} {parsed['category']}** · Urgency **{parsed['urgency']}/10**")
                        st.info(parsed["summary"])

                        log = notify_department(record)
                        db.add_notification(log)
                        if log["status"] == "sent":
                            st.success(f"📧 Live email sent to **{log['department']}**")
                        else:
                            st.warning(f"📮 Notification routed to **{log['icon']} {log['department']}** (simulated).")
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI processing failed: {e}")

    # ---------- Public feed + verification handshake ----------
    with tab_feed:
        df = pd.DataFrame(db.get_all())  # re-fetch fresh in case admin acted in the meantime
        st.markdown('<div class="section-title">📡 Recent Submissions & Active Triage</div>', unsafe_allow_html=True)

        active_df = df[df["status"] != "Resolved"] if not df.empty else df

        if active_df.empty:
            st.info("No active issues right now.")
            return

        m1, m2, m3 = st.columns(3)
        m1.metric("Active Issues", len(active_df))
        m2.metric("Critical (≥8)", int((active_df["urgency"] >= 8).sum()))
        m3.metric("Awaiting Your Confirmation", int((active_df["deletion_state"] == "Pending_Client_Approval").sum()))

        st.write("")
        for _, row in active_df.sort_values("urgency", ascending=False).iterrows():
            toggle_key = f"show_original_{row['id']}"
            show_original = st.session_state.get(toggle_key, False)
            display_text = row["raw_text"] if show_original else row["translated_text"]
            lang_tag = "🌐 Original dialect" if show_original else "🇬🇧 Translated (English)"

            col_card, col_toggle = st.columns([5, 1])
            with col_card:
                st.markdown(f"""
                <div class="todo-card">
                  {render_aura_badge(row['category'])}
                  <span style="float:right;color:{urgency_color(row['urgency'])};font-weight:800;">{row['urgency']}/10</span>
                  <div style="color:#e5e9f5;margin-top:8px;">{display_text}</div>
                  <div style="color:#6b7280;font-size:11px;margin-top:4px;font-style:italic;">{lang_tag}</div>
                  <div style="color:#8b93ad;font-size:12px;margin-top:6px;">📍 {row['area']} ({row['pincode']})</div>
                  {render_pipeline(row['status'], row['deletion_state'])}
                </div>
                """, unsafe_allow_html=True)
            with col_toggle:
                st.write("")
                st.checkbox("🌐 Show Original Text", key=toggle_key)

            if row["deletion_state"] == "Pending_Client_Approval":
                with st.form(key=f"citizen_verify_{row['id']}", clear_on_submit=True):
                    st.markdown(f"**⚠️ Admin Resolution Proof:** {row.get('admin_proof')}")
                    decision = st.radio(
                        "Do you confirm this issue is resolved?",
                        ["Select Option", "Yes, Close Issue", "No, Keep Open (Reopen Task)"],
                        key=f"dec_{row['id']}"
                    )
                    draft_key = f"draft_rej_{row['id']}"
                    rejection_reason = st.text_input(
                        "If choice is 'No', explain why here:",
                        key=f"rej_text_{row['id']}",
                        value=st.session_state.setdefault(draft_key, ""),
                        placeholder="Reason for keeping issue open..."
                    )
                    submit_decision = st.form_submit_button("Submit Response", type="primary")

                    if submit_decision:
                        if decision == "Yes, Close Issue":
                            db.update_deletion_workflow(
                                row["id"], deletion_state="Approved",
                                admin_proof=row["admin_proof"], status="Resolved", rejection_note=""
                            )
                            st.session_state.pop(draft_key, None)
                            st.success("Issue closed successfully.")
                            st.rerun()
                        elif decision == "No, Keep Open (Reopen Task)":
                            if not rejection_reason.strip():
                                st.warning("Please provide a reason for reopening the task.")
                            else:
                                db.update_deletion_workflow(
                                    row["id"], deletion_state="None",
                                    admin_proof=row["admin_proof"], status="Pending", rejection_note=rejection_reason
                                )
                                st.session_state.pop(draft_key, None)
                                st.error("Rejection feedback logged for Admin review.")
                                st.rerun()
                        else:
                            st.warning("Please select Yes or No before submitting.")


# =========================================================
# ADMINISTRATIVE HUB
# =========================================================
def admin_view():
    df = pd.DataFrame(db.get_all())  # fresh from disk at the very top of this view

    # ---------- KPI metrics (always reflect the FULL, unfiltered dataset) ----------
    m1, m2, m3, m4, m5 = st.columns(5)
    critical_n = int((df["urgency"] >= 8).sum()) if not df.empty else 0
    top_cat = df["category"].mode()[0] if not df.empty else "—"
    avg_urgency = round(df["urgency"].mean(), 1) if not df.empty else 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    resolved_today = 0
    if not df.empty:
        resolved_today = int(df["resolved_at"].dropna().astype(str).str.startswith(today_str).sum())

    for col, label, value, icon in [
        (m1, "Total Grievances", len(df), "🗂️"),
        (m2, "Critical Priorities", critical_n, "🔥"),
        (m3, "Top Focus Area", f"{CATEGORY_META.get(top_cat,{}).get('icon','')} {top_cat.split(' ')[0]}", "🎯"),
        (m4, "Avg. Urgency", f"{avg_urgency}/10", "📈"),
        (m5, "Resolved Today", resolved_today, "✅"),
    ]:
        col.markdown(f"""<div class="metric-card"><div class="metric-label">{icon} {label}</div>
                     <div class="metric-value">{value}</div></div>""", unsafe_allow_html=True)

    # ---------- Advanced Registry Diagnostics (search + filter deck) ----------
    st.write("")
    with st.expander("🔍 Advanced Registry Diagnostics", expanded=False):
        f1, f2, f3 = st.columns([2, 2, 2])
        search_term = f1.text_input(
            "Search by ID, description, or Area",
            key="registry_search", placeholder="e.g. pothole, 7bdfaae9, Andheri..."
        )
        category_filter = f2.multiselect(
            "Categories", CATEGORIES, default=CATEGORIES, key="registry_cat_filter"
        )
        urgency_range = f3.slider(
            "Urgency range", min_value=1, max_value=10, value=(1, 10), key="registry_urgency_filter"
        )

    filtered_df = df.copy()
    if not filtered_df.empty:
        filtered_df = filtered_df[filtered_df["category"].isin(category_filter)]
        filtered_df = filtered_df[
            (filtered_df["urgency"] >= urgency_range[0]) & (filtered_df["urgency"] <= urgency_range[1])
        ]
        if search_term.strip():
            term = search_term.strip().lower()
            filtered_df = filtered_df[filtered_df.apply(
                lambda r: term in str(r.get("id", "")).lower()
                or term in str(r.get("raw_text", "")).lower()
                or term in str(r.get("translated_text", "")).lower()
                or term in str(r.get("area", "")).lower(),
                axis=1
            )]

    tab_dash, tab_todo = st.tabs(["📊 Command Hub", "✅ To-Do Checklist & Removal Requests"])

    # ---------- Command Hub ----------
    with tab_dash:
        st.markdown('<div class="section-title">🗺️ Live Issue Hotspot Map — Nationwide</div>', unsafe_allow_html=True)
        st.caption(f"Showing {len(filtered_df)} of {len(df)} grievances based on current registry filters.")
        render_dark_map(filtered_df)

        legend_cols = st.columns(len(CATEGORY_META))
        for c, (cat, meta) in zip(legend_cols, CATEGORY_META.items()):
            c.markdown(render_aura_badge(cat), unsafe_allow_html=True)

        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-title">📁 Category Split</div>', unsafe_allow_html=True)
            if not filtered_df.empty:
                cat_counts = filtered_df["category"].value_counts().reset_index()
                cat_counts.columns = ["Category", "Count"]
                fig = px.pie(cat_counts, names="Category", values="Count", hole=0.55, color="Category",
                             color_discrete_map={k: v["color"] for k, v in CATEGORY_META.items()})
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                   font_color="#e5e9f5", showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=260)
                fig.update_traces(textinfo="label+percent", textfont_size=11)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("No data matches the current filter.")
        with c2:
            st.markdown('<div class="section-title">📅 Resolution Trend (Last 7 Days)</div>', unsafe_allow_html=True)
            if not df.empty and df["resolved_at"].notna().any():
                resolved_df = df[df["resolved_at"].notna()].copy()
                resolved_df["resolved_date"] = pd.to_datetime(resolved_df["resolved_at"]).dt.date
                trend = resolved_df.groupby("resolved_date").size().reset_index(name="Resolved")
                fig3 = go.Figure(go.Bar(x=trend["resolved_date"].astype(str), y=trend["Resolved"], marker_color="#00E5FF"))
                fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e5e9f5",
                                     margin=dict(t=10, b=10, l=10, r=10), height=260,
                                     xaxis_title="Date", yaxis_title="Issues Resolved",
                                     xaxis=dict(gridcolor="#232a40"), yaxis=dict(gridcolor="#232a40"))
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.caption("No resolutions logged yet.")

        st.write("")
        st.markdown('<div class="section-title">📮 Department Notification Log</div>', unsafe_allow_html=True)
        notifications = db.get_notifications()
        if notifications:
            for log in sorted(notifications, key=lambda x: x["notified_at"], reverse=True)[:5]:
                status_color = "#00E5FF" if log["status"] == "sent" else "#FFEA00"
                status_text = "Live email sent" if log["status"] == "sent" else "Simulated"
                st.markdown(f"""<div class="todo-card" style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="color:#e5e9f5;font-size:13px;">{log['icon']} <b>{log['department']}</b> notified for <code>{log['grievance_id']}</code></div>
                    <span style="color:{status_color};font-size:12px;font-weight:700;">● {status_text}</span></div>""",
                            unsafe_allow_html=True)
        else:
            st.caption("No notifications sent yet.")

    # ---------- To-Do Checklist as a multi-column Kanban board ----------
    with tab_todo:
        st.markdown('<div class="section-title">✅ To-Do Checklist — Kanban Board</div>', unsafe_allow_html=True)
        st.caption("Active tasks only, subset by the Advanced Registry Diagnostics filters above. "
                   "Admin cannot delete a task directly — closure must be verified by the citizen who filed it.")

        if df.empty:
            st.info("No grievances filed yet.")
            return

        active_df = filtered_df[filtered_df["status"] != "Resolved"] if not filtered_df.empty else filtered_df
        active_df = active_df.sort_values("urgency", ascending=False).reset_index(drop=True)

        if active_df.empty:
            st.success("🎉 No active tasks match the current registry filters!")

        NUM_COLUMNS = 3 if len(active_df) >= 6 else 2
        kanban_cols = st.columns(NUM_COLUMNS)

        for i, row in active_df.iterrows():
            target_col = kanban_cols[i % NUM_COLUMNS]
            with target_col:
                st.markdown(f"""
                <div class="todo-card">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#8b93ad;font-size:11px;">ID: <code>{row['id']}</code></span>
                    {render_aura_badge(row['category'])}
                  </div>
                  <div style="color:#e5e9f5;margin-top:10px;font-size:14px;">{row['translated_text']}</div>
                  <div style="color:#8b93ad;font-size:12px;margin-top:8px;">📍 {row['area']} ({row['pincode']})</div>
                  <div style="color:{urgency_color(row['urgency'])};font-weight:800;font-size:12px;margin-top:4px;">Urgency {row['urgency']}/10</div>
                  {render_pipeline(row['status'], row['deletion_state'])}
                  {"<div style='color:#FF1744;font-size:11px;margin-top:6px;'>✋ " + row['client_rejection_note'] + "</div>" if row['client_rejection_note'] else ""}
                </div>
                """, unsafe_allow_html=True)

                with st.form(key=f"status_form_{row['id']}", clear_on_submit=False):
                    new_status = st.selectbox(
                        "Update status", ["Pending", "In Progress"],
                        index=["Pending", "In Progress"].index(row["status"]) if row["status"] in ["Pending", "In Progress"] else 0,
                        key=f"status_sel_{row['id']}"
                    )
                    submit_status = st.form_submit_button("Update Status")
                    if submit_status and new_status != row["status"]:
                        db.update_status(row["id"], new_status)
                        st.rerun()

                if row["deletion_state"] == "None":
                    with st.expander(f"⚙️ Closure Request — {row['id']}"):
                        draft_key = f"draft_{row['id']}"

                        # Quick-fill pills sit OUTSIDE the form: st.pills
                        # instantly reruns the script on selection (form
                        # widgets don't), letting us append canned log text
                        # into the draft BEFORE the form's text_area renders.
                        picked = st.pills(
                            "Quick-fill operational log",
                            QUICK_LOG_SNIPPETS, key=f"pill_{row['id']}", selection_mode="single"
                        )
                        if picked and picked not in st.session_state.setdefault(draft_key, ""):
                            existing = st.session_state[draft_key]
                            st.session_state[draft_key] = (existing + " " + picked).strip()

                        with st.form(key=f"form_{row['id']}", clear_on_submit=True):
                            proof_text = st.text_area(
                                "Describe Resolution Action & Provide Verification Image Link:",
                                key=f"p_{row['id']}",
                                value=st.session_state.setdefault(draft_key, ""),
                                placeholder="e.g. Pothole filled and resurfaced on 5 Jul 2026. Photo: https://..."
                            )
                            submit_removal = st.form_submit_button("Request Task Removal", type="primary")

                            if submit_removal:
                                if not proof_text.strip():
                                    st.warning("You must enter complete resolution proof logs.")
                                else:
                                    db.update_deletion_workflow(
                                        grievance_id=row["id"],
                                        deletion_state="Pending_Client_Approval",
                                        admin_proof=proof_text,
                                        status="In Progress",
                                        rejection_note=""
                                    )
                                    st.session_state.pop(draft_key, None)
                                    st.toast(f"Task {row['id']} flagged for review.")
                                    st.rerun()
                elif row["deletion_state"] == "Pending_Client_Approval":
                    st.info("⏳ Awaiting citizen confirmation.")

    # ---------- Exportable Governance Audit Ledger ----------
    st.markdown('<div class="audit-block">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📥 Governance Audit Export</div>', unsafe_allow_html=True)
    st.caption("Exports the complete, unfiltered database state for governmental transparency and compliance review.")

    export_records = db.get_export_data()
    if export_records:
        export_df = pd.DataFrame(export_records)
        export_columns = [
            "id", "category", "urgency", "status", "deletion_state",
            "area", "pincode", "landmark", "lat", "lon",
            "translated_text", "raw_text", "admin_proof", "client_rejection_note",
            "timestamp", "resolved_at",
        ]
        export_columns = [c for c in export_columns if c in export_df.columns]
        export_df = export_df[export_columns].rename(columns={
            "id": "Grievance ID", "category": "Category", "urgency": "Urgency Score",
            "status": "Status", "deletion_state": "Deletion State",
            "area": "Area", "pincode": "Pincode", "landmark": "Landmark",
            "lat": "Latitude", "lon": "Longitude",
            "translated_text": "Translated Description", "raw_text": "Original Description",
            "admin_proof": "Admin Resolution Proof", "client_rejection_note": "Citizen Rejection Note",
            "timestamp": "Filed Timestamp", "resolved_at": "Closed Timestamp",
        })

        csv_buffer = io.StringIO()
        export_df.to_csv(csv_buffer, index=False)

        st.download_button(
            label="📥 Export Compliance Audit Ledger (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"civic_pulse_audit_ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="export_audit_csv_btn",
        )
    else:
        st.caption("No records available to export yet.")
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# ROUTE
# =========================================================
if st.session_state.role == "citizen":
    citizen_view()
else:
    admin_view()
