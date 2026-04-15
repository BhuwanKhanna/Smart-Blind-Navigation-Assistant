from __future__ import annotations

import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;500;700&family=Atkinson+Hyperlegible+Next:wght@400;700&display=swap');

            :root {
                --bg: #05070d;
                --bg-soft: #0d1320;
                --panel: rgba(12, 18, 30, 0.9);
                --panel-strong: rgba(7, 11, 20, 0.95);
                --border: rgba(112, 168, 255, 0.2);
                --text: #f8fbff;
                --muted: #a8b7cf;
                --accent: #7dd3fc;
                --safe: #6ee7b7;
                --warn: #fbbf24;
                --danger: #fb7185;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(125, 211, 252, 0.10), transparent 25%),
                    radial-gradient(circle at top right, rgba(110, 231, 183, 0.10), transparent 22%),
                    linear-gradient(180deg, #05070d 0%, #09111f 100%);
                color: var(--text);
                font-family: 'Atkinson Hyperlegible Next', sans-serif;
            }

            h1, h2, h3, h4 {
                font-family: 'Lexend', sans-serif;
                letter-spacing: -0.03em;
            }

            [data-testid="stSidebar"] {
                background: rgba(5, 8, 14, 0.98);
                border-right: 1px solid var(--border);
            }

            .hero-card,
            .metric-card,
            .panel-card {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 24px;
                box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
            }

            .hero-card {
                padding: 30px;
                margin-bottom: 18px;
            }

            .hero-eyebrow {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                border-radius: 999px;
                padding: 8px 16px;
                background: rgba(125, 211, 252, 0.12);
                border: 1px solid rgba(125, 211, 252, 0.28);
                font-size: 1rem;
            }

            .hero-eyebrow.danger {
                background: rgba(251, 113, 133, 0.12);
                border-color: rgba(251, 113, 133, 0.26);
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 14px;
                margin: 16px 0 22px 0;
            }

            .metric-card {
                padding: 20px;
            }

            .metric-label {
                color: var(--muted);
                font-size: 0.88rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 10px;
            }

            .metric-value {
                font-size: 1.6rem;
                font-weight: 700;
            }

            .copy {
                color: var(--muted);
                line-height: 1.7;
                font-size: 1rem;
            }

            .stream-shell {
                border-radius: 24px;
                overflow: hidden;
                border: 1px solid var(--border);
                background: var(--panel-strong);
                min-height: 520px;
            }

            .panel-card {
                padding: 20px;
            }

            .big-alert button {
                min-height: 68px !important;
                font-size: 1.15rem !important;
                font-weight: 700 !important;
            }

            @media (max-width: 900px) {
                .metric-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_banner(running: bool, message: str) -> str:
    eyebrow_class = "hero-eyebrow" if running else "hero-eyebrow danger"
    state = "Live camera guidance online" if running else "Assistant offline"
    return f"""
    <div class="hero-card">
        <div class="{eyebrow_class}">{state}</div>
        <h1 style="margin: 18px 0 12px 0;">Smart AI Blind Navigation Assistant</h1>
        <p class="copy">
            Real-time obstacle detection, path guidance, voice support, and emergency safety workflows
            designed for assistive navigation demos and practical internship portfolios.
        </p>
        <p class="copy" style="margin-top: 10px;"><strong>System note:</strong> {message}</p>
    </div>
    """


def metric_card(label: str, value: str) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """
