from __future__ import annotations

import os
from io import StringIO

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

from dashboard.components.api_client import APIClient
from dashboard.components.theme import hero_banner, inject_theme, metric_card


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))
DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Blind Navigation Assistant",
    page_icon="BN",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()
st_autorefresh(interval=3000, key="blind_nav_autorefresh")


def _client() -> APIClient:
    return APIClient(st.session_state.get("api_url", DEFAULT_API_URL))


def _snapshot() -> dict:
    try:
        return _client().get("/api/dashboard")
    except Exception as exc:
        st.error(f"Unable to reach backend API: {exc}")
        return {
            "assistant": {
                "running": False,
                "message": "API unavailable",
                "backend": "unknown",
                "language": "en",
                "voice_rate": 175,
                "guidance": "Unavailable",
                "guidance_confidence": 0.0,
                "priority": "normal",
                "path_direction": "center",
                "path_confidence": 0.0,
                "detections": [],
                "tts_available": False,
                "last_voice_message": "",
                "fps": 0.0,
                "last_updated_at": None,
            },
            "summary": {"total_events": 0, "emergency_events": 0, "hazard_events": 0, "latest_event": None},
            "events": [],
        }


def _post(path: str, payload: dict | None = None, success_message: str | None = None) -> None:
    try:
        _client().post(path, payload)
        if success_message:
            st.success(success_message)
    except Exception as exc:
        st.error(f"Request failed: {exc}")


def _render_feed(api_url: str, running: bool) -> None:
    if not running:
        st.info("Start the assistant to show the live camera feed with guidance arrows and hazard overlays.")
        return

    components.html(
        f"""
        <div class="stream-shell">
            <img id="live-feed" src="{api_url}/api/assistant/frame?tick={os.urandom(4).hex()}"
                 style="width:100%;height:520px;object-fit:cover;display:block;" />
        </div>
        <script>
            const feed = document.getElementById("live-feed");
            setInterval(() => {{
                feed.src = "{api_url}/api/assistant/frame?tick=" + Date.now();
            }}, 900);
        </script>
        """,
        height=540,
    )


if "api_url" not in st.session_state:
    st.session_state["api_url"] = DEFAULT_API_URL

with st.sidebar:
    st.header("Assistant Controls")
    st.session_state["api_url"] = st.text_input("FastAPI base URL", value=st.session_state["api_url"])
    camera_index = st.number_input("Camera index", min_value=0, max_value=10, value=0, step=1)
    detection_backend = st.selectbox("Detection backend", ["auto", "yolo", "opencv"], index=0)
    language = st.selectbox("Voice language", ["en", "hi", "es"], index=0, format_func=lambda item: {"en": "English", "hi": "Hindi", "es": "Spanish"}[item])
    voice_rate = st.slider("Voice speed", min_value=120, max_value=240, value=175)

    start_col, stop_col = st.columns(2)
    with start_col:
        if st.button("Start Assistant", use_container_width=True):
            _post(
                "/api/assistant/start",
                {
                    "camera_index": int(camera_index),
                    "detection_backend": detection_backend,
                    "language": language,
                    "voice_rate": int(voice_rate),
                },
                "Navigation assistant started.",
            )
    with stop_col:
        if st.button("Stop Assistant", use_container_width=True):
            _post("/api/assistant/stop", success_message="Navigation assistant stopped.")

    st.divider()
    st.subheader("Voice Test")
    custom_prompt = st.text_input("Test phrase", value="Path clear, move straight")
    if st.button("Speak Prompt", use_container_width=True):
        _post("/api/assistant/speak", {"text": custom_prompt, "language": language}, "Voice prompt sent.")

    st.divider()
    st.subheader("Safety Tools")
    if st.button("Share Location", use_container_width=True):
        _post("/api/assistant/share-location", success_message="Location sharing simulated.")

    emergency_reason = st.text_input("Emergency reason", value="Immediate assistance required")
    st.markdown('<div class="big-alert">', unsafe_allow_html=True)
    if st.button("Emergency Alert", use_container_width=True, type="primary"):
        _post("/api/assistant/emergency", {"reason": emergency_reason}, "Emergency alert triggered.")
    st.markdown("</div>", unsafe_allow_html=True)

snapshot = _snapshot()
assistant = snapshot["assistant"]
summary = snapshot["summary"]
events_df = pd.DataFrame(snapshot["events"])
detections_df = pd.DataFrame(assistant.get("detections", []))

st.markdown(hero_banner(assistant["running"], assistant["message"]), unsafe_allow_html=True)

metric_markup = "".join(
    [
        metric_card("Guidance", assistant["guidance"]),
        metric_card("Priority", assistant["priority"].title()),
        metric_card("Guide Confidence", f"{assistant['guidance_confidence']:.2f}"),
        metric_card("FPS", f"{assistant['fps']:.1f}"),
        metric_card("Backend", assistant["backend"].upper()),
        metric_card("Path Direction", assistant["path_direction"].title()),
        metric_card("Hazard Events", str(summary["hazard_events"])),
        metric_card("Emergency Events", str(summary["emergency_events"])),
    ]
)
st.markdown(f'<div class="metric-grid">{metric_markup}</div>', unsafe_allow_html=True)

left, right = st.columns([1.4, 1], gap="large")

with left:
    st.subheader("Live Navigation Feed")
    _render_feed(st.session_state["api_url"], assistant["running"])

with right:
    st.subheader("Navigation Snapshot")
    st.markdown(
        f"""
        <div class="panel-card">
            <p><strong>Language:</strong> {assistant['language']}</p>
            <p><strong>Voice engine ready:</strong> {assistant['tts_available']}</p>
            <p><strong>Last voice message:</strong> {assistant['last_voice_message'] or 'None yet'}</p>
            <p><strong>Path confidence:</strong> {assistant['path_confidence']:.2f}</p>
            <p><strong>Last update:</strong> {assistant['last_updated_at'] or 'Not available'}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not detections_df.empty:
        st.subheader("Hazard Confidence Scores")
        chart_df = detections_df[["label", "hazard_score"]].copy().head(8)
        chart_df.columns = ["Object", "Hazard Score"]
        st.bar_chart(chart_df.set_index("Object"))
    else:
        st.info("Detected hazards and landmarks will appear here once the camera is active.")

st.subheader("Detected Objects")
if detections_df.empty:
    st.info("No live detections yet.")
else:
    st.dataframe(detections_df, use_container_width=True, hide_index=True)

st.subheader("Navigation Event Log")
if events_df.empty:
    st.info("Event history is empty. Alerts, hazard detections, and location shares will appear here.")
else:
    st.dataframe(events_df, use_container_width=True, hide_index=True)
    csv_buffer = StringIO()
    events_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Download event history CSV",
        data=csv_buffer.getvalue(),
        file_name="blind_navigation_events.csv",
        mime="text/csv",
    )
