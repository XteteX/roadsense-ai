"""RoadSense AI — Streamlit dashboard for city road services.

Run from the project root:  streamlit run src/dashboard.py
"""
import json
import os
import random
import sys

import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from PIL import Image
from streamlit_folium import st_folium

# Make `src` importable when Streamlit runs this file directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database import add_defect, delete_defect, get_defects, init_db  # noqa: E402
from src.engine import CATEGORIES, CRITICAL, HIGH, MEDIUM, RoadAnalyzer, normalize_category  # noqa: E402

ALMATY_CENTER = (43.2389, 76.8897)
DEMO_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "defects.json")

# Marker colour (folium) and list icon for each priority category.
CATEGORY_STYLE = {
    CRITICAL: ("red", "🔴"),
    HIGH: ("orange", "🟠"),
    MEDIUM: ("blue", "🔵"),
}
DEFAULT_STYLE = ("green", "🟢")

# Illustrative assumption for the pitch: repairing a defect early instead of after it
# has grown saves on average this much (KZT). Not based on official city data.
SAVINGS_PER_REPORT_KZT = 45_000

st.set_page_config(page_title="RoadSense AI Dashboard", layout="wide", page_icon="🛣️")
init_db()
analyzer = RoadAnalyzer()


@st.cache_resource(show_spinner="Loading the YOLOv8 pothole model…")
def get_detector():
    from src.detection import RoadDetector  # heavy import, load once per server

    return RoadDetector()


def load_defects() -> list[dict]:
    """Read all reports and make sure older (Russian) records display in English."""
    defects = get_defects()
    for d in defects:
        d["category"] = normalize_category(d["category"])
        if any("а" <= ch.lower() <= "я" for ch in (d.get("explanation") or "")):
            d["explanation"] = analyzer.explain(d["type"], d["size_cm"], d["traffic_level"],
                                                bool(d["is_near_social"]), d["score"])
    return defects


def import_demo_data() -> tuple[int, str | None]:
    """Fill an empty database with synthetic demo defects from data/defects.json."""
    if not os.path.exists(DEMO_DATA_PATH):
        return 0, "data/defects.json not found. Generate it with: python src/utils.py"
    with open(DEMO_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    for d in raw:
        analysis = analyzer.calculate_priority(d["type"], d["size_cm"], d["traffic_level"], d["is_near_social"])
        add_defect({**{k: d[k] for k in ("type", "lat", "lon", "size_cm", "traffic_level", "is_near_social")},
                    **analysis})
    return len(raw), None


st.session_state.setdefault("last_added_id", None)
st.session_state.setdefault("map_focus", ALMATY_CENTER)

defects = load_defects()
if not defects:
    with st.spinner("Loading demo data…"):
        _, err = import_demo_data()
    if err:
        st.warning(f"Demo data not found: {err}")
        st.stop()
    st.rerun()

# ---------------------------------------------------------------------------
# Header and KPIs
# ---------------------------------------------------------------------------
st.title("🛣️ RoadSense AI: Road Monitoring System for Almaty")
st.caption("Residents report potholes through a Telegram bot, a YOLOv8 model verifies each photo, "
           "and every confirmed report gets an explainable repair priority.")

df = pd.DataFrame(defects)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Open reports", len(df))
k2.metric("Critical", int((df["category"] == CRITICAL).sum()))
k3.metric("High priority", int((df["category"] == HIGH).sum()))
k4.metric("Average priority", f"{df['score'].mean():.0f} / 100")
st.divider()

col_map, col_list = st.columns([2, 1])

# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------
with col_map:
    st.subheader(f"Defect map ({len(defects)} reports)")
    show_heatmap = st.checkbox("Show heatmap (defect density weighted by priority)", value=True)

    last_id = st.session_state["last_added_id"]
    m = folium.Map(location=list(st.session_state["map_focus"]), zoom_start=14 if last_id else 12)

    for p in defects:
        is_new = p["id"] == last_id
        color, _ = CATEGORY_STYLE.get(p["category"], DEFAULT_STYLE)
        popup = f"Report #{p['id']}: {p['score']}/100 ({p['category']})"
        folium.Marker(
            [p["lat"], p["lon"]],
            popup=f"NEW → {popup}" if is_new else popup,
            tooltip="New report" if is_new else f"Report #{p['id']}",
            icon=folium.Icon(color="red" if is_new else color, icon="star" if is_new else "info-sign"),
        ).add_to(m)
        if is_new:
            folium.CircleMarker([p["lat"], p["lon"]], radius=14, color="red", fill=True,
                                fill_opacity=0.2, weight=3).add_to(m)

    if show_heatmap:
        HeatMap([[p["lat"], p["lon"], min(max(p["score"] / 100, 0), 1)] for p in defects],
                radius=15, blur=10, min_opacity=0.5, max_zoom=17).add_to(m)

    # returned_objects=[] stops the page from re-running on every pan or zoom.
    st_folium(m, height=600, use_container_width=True, returned_objects=[])
    if last_id:
        st.info("The most recently added report is marked with a red star and circle.")

# ---------------------------------------------------------------------------
# Prioritised list with explanations
# ---------------------------------------------------------------------------
with col_list:
    st.subheader("📊 Priorities and explanations")
    category_filter = st.selectbox("Show category:", ["All"] + CATEGORIES)

    ranked = df.sort_values("score", ascending=False).to_dict("records")
    if category_filter != "All":
        ranked = [d for d in ranked if d["category"] == category_filter]
    st.write(f"Showing {min(len(ranked), 15)} of {len(ranked)} reports, highest priority first")

    for p in ranked[:15]:
        _, icon = CATEGORY_STYLE.get(p["category"], DEFAULT_STYLE)
        with st.expander(f"{icon} Report #{p['id']} · priority {p['score']} · {p['category']}"):
            st.write(f"**Type:** {analyzer.type_labels.get(p['type'], p['type'])}")
            st.write(f"**Size:** {p['size_cm']:.1f} cm (estimate)")
            st.write(f"**Traffic level:** {['low', 'medium', 'high'][int(p['traffic_level']) - 1]}"
                     f"{' · near a school/hospital' if p['is_near_social'] else ''}")
            st.warning(f"**Why this priority:** {p['explanation']}")
            b1, b2 = st.columns(2)
            if b1.button("Dispatch crew", key=f"dispatch_{p['id']}"):
                st.success("Work order created (demo).")
            if b2.button("Delete report", key=f"delete_{p['id']}"):
                if delete_defect(p["id"]):
                    if st.session_state["last_added_id"] == p["id"]:
                        st.session_state["last_added_id"] = None
                        st.session_state["map_focus"] = ALMATY_CENTER
                    st.rerun()
                else:
                    st.error("Could not delete the report: record not found.")

# ---------------------------------------------------------------------------
# Sidebar: new report from a photo
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🛣️ RoadSense AI")
    st.caption("v1.0 MVP · Decentrathon 5.0")
    if st.button("Refresh map data"):
        st.rerun()
    st.divider()

    st.header("📸 New report")
    uploaded_file = st.file_uploader("Upload a photo of a road defect", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        with st.spinner("Running YOLOv8 pothole detection…"):
            result = get_detector().detect_and_process(image)
        detected = result["defect"]

        if detected:
            st.success(f"Detected: pothole, estimated size ~{detected['size_cm']} cm")
            st.info(f"Detection confidence: {detected['confidence'] * 100:.1f}%")
        else:
            st.warning("No potholes detected. Try a closer photo in good light.")
        st.image(result["image"], caption="YOLOv8 result (green boxes = detected potholes)",
                 width="stretch")

        if detected:
            with st.form("add_defect_form"):
                st.write("### Confirm the details")
                st.caption("The location is approximate until GPS support is added. You can edit it.")
                lat = st.number_input("Latitude", value=ALMATY_CENTER[0] + detected.get("lat_offset", random.uniform(-0.01, 0.01)), format="%.6f")
                lon = st.number_input("Longitude", value=ALMATY_CENTER[1] + detected.get("lon_offset", random.uniform(-0.01, 0.01)), format="%.6f")
                traffic = st.select_slider("Traffic level", options=[1, 2, 3], value=2,
                                           format_func=lambda v: {1: "Low", 2: "Medium", 3: "High"}[v])
                social = st.checkbox("School or hospital nearby?")

                if st.form_submit_button("Add to registry"):
                    analysis = analyzer.calculate_priority("pothole", detected["size_cm"], traffic, social)
                    new_id = add_defect({
                        "type": "pothole", "lat": lat, "lon": lon, "size_cm": detected["size_cm"],
                        "traffic_level": traffic, "is_near_social": social, **analysis,
                    })
                    st.session_state["last_added_id"] = new_id
                    st.session_state["map_focus"] = (lat, lon)
                    st.balloons()
                    st.rerun()

    st.divider()
    st.subheader("📈 Reports by priority")
    counts = df["category"].value_counts().reindex(CATEGORIES, fill_value=0)
    st.bar_chart(counts, horizontal=True, sort=False, height=180)

    st.subheader("💎 Economic impact")
    st.metric("Estimated budget savings", f"{len(df) * SAVINGS_PER_REPORT_KZT:,.0f} ₸")
    st.progress(min(len(df) / 100, 1.0), text=f"Reports processed: {len(df)}")
    st.caption(f"Illustrative estimate: {SAVINGS_PER_REPORT_KZT:,} ₸ saved per defect fixed early, "
               "before it grows into a costlier repair. Not based on official city data.")
