from __future__ import annotations

import streamlit as st


# Central stylesheet controlling the visual appearance of the CampusCare Streamlit app.
CSS = """
<style>
:root {
    --cc-blue-50: #f4faff;
    --cc-blue-100: #e8f5ff;
    --cc-blue-200: #cdeaff;
    --cc-blue-400: #62b9ee;
    --cc-blue-500: #3aa7e8;
    --cc-blue-600: #208aca;
    --cc-blue-700: #176b9e;
    --cc-navy: #17324d;
    --cc-text: #24384a;
    --cc-muted: #6d8295;
    --cc-border: #d7e8f4;
    --cc-white: #ffffff;
}

.stApp {
    background: linear-gradient(180deg, #f5fbff 0%, #ffffff 45%, #f8fcff 100%);
    color: var(--cc-text);
}

/* Keep CampusCare content below Streamlit's fixed top toolbar. */
header[data-testid="stHeader"] {
    background: rgba(245, 251, 255, 0.94);
    border-bottom: 1px solid rgba(215, 232, 244, 0.85);
    backdrop-filter: blur(10px);
}

[data-testid="stDecoration"] {
    display: none;
}

.block-container {
    max-width: 1180px;
    padding-top: 5rem;
    padding-bottom: 4rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #eef8ff 0%, #ffffff 100%);
    border-right: 1px solid var(--cc-border);
}

[data-testid="stSidebar"] .block-container {
    padding-top: 4.4rem;
}

h1, h2, h3 {
    color: var(--cc-navy);
    letter-spacing: -0.02em;
}

.cc-brand {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 0.7rem;
}

.cc-logo-frame {
    width: 70px;
    height: 48px;
    flex: 0 0 70px;
    overflow: hidden;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    filter: drop-shadow(0 8px 14px rgba(48, 157, 221, 0.20));
}

.cc-logo-image {
    width: 70px;
    height: 70px;
    max-width: none;
    object-fit: contain;
    transform: translateY(-10px);
    display: block;
}

.cc-brand-copy {
    min-width: 0;
}

.cc-brand-name {
    font-size: 1.55rem;
    line-height: 1;
    font-weight: 800;
    color: var(--cc-navy);
}

.cc-brand-subtitle {
    font-size: 0.78rem;
    color: var(--cc-muted);
    margin-top: 0.3rem;
}

.cc-hero {
    border: 1px solid var(--cc-border);
    border-radius: 26px;
    padding: 2.1rem 2.2rem;
    margin-bottom: 1.4rem;
    background:
        radial-gradient(circle at 95% 10%, rgba(122, 201, 245, 0.34), transparent 32%),
        linear-gradient(135deg, #ffffff 0%, #edf8ff 100%);
    box-shadow: 0 16px 45px rgba(42, 112, 156, 0.09);
}

.cc-eyebrow {
    display: inline-block;
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    background: #dff2ff;
    color: #176b9e;
    font-size: 0.74rem;
    font-weight: 750;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
}

.cc-hero h1 {
    margin: 0;
    font-size: clamp(2rem, 4vw, 3.35rem);
    line-height: 1.06;
}

.cc-hero p {
    color: var(--cc-muted);
    font-size: 1.05rem;
    max-width: 720px;
    margin: 0.9rem 0 0;
}

.cc-card {
    background: rgba(255,255,255,0.96);
    border: 1px solid var(--cc-border);
    border-radius: 18px;
    padding: 1.1rem;
    box-shadow: 0 8px 24px rgba(40, 102, 143, 0.07);
    min-height: 100%;
}

.cc-item-title {
    font-size: 1.05rem;
    font-weight: 760;
    color: var(--cc-navy);
    margin-bottom: 0.25rem;
}

.cc-muted {
    color: var(--cc-muted);
    font-size: 0.88rem;
}

.cc-pill {
    display: inline-block;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    border: 1px solid #c9e8fb;
    background: #edf8ff;
    color: #176b9e;
    font-size: 0.74rem;
    font-weight: 700;
    margin: 0 0.25rem 0.3rem 0;
}

.cc-status-available { background: #edfdf5; color: #177149; border-color: #c6efdb; }
.cc-status-reserved { background: #fff8e7; color: #8a6112; border-color: #f3dfae; }
.cc-status-completed { background: #f1f0ff; color: #5542a8; border-color: #dcd7ff; }
.cc-status-withdrawn { background: #f5f6f8; color: #66717c; border-color: #dce1e6; }

.cc-profile-banner {
    padding: 1.35rem;
    border-radius: 20px;
    background: linear-gradient(135deg, #dff3ff 0%, #ffffff 75%);
    border: 1px solid var(--cc-border);
}

.cc-score {
    font-size: 2.1rem;
    font-weight: 850;
    color: var(--cc-blue-700);
    line-height: 1;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid var(--cc-border);
    padding: 0.75rem 0.95rem;
    border-radius: 16px;
    box-shadow: 0 7px 22px rgba(40, 102, 143, 0.06);
}

.stButton > button, .stFormSubmitButton > button {
    border-radius: 11px;
    border: 1px solid #68bceb;
    min-height: 2.7rem;
    font-weight: 700;
}

.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #58b4e9 0%, #258fce 100%);
    color: white;
    border: none;
    box-shadow: 0 7px 18px rgba(37, 143, 206, 0.20);
}

.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 11px;
}

[data-testid="stAlert"] {
    border-radius: 14px;
}

@media (max-width: 768px) {
    .block-container {
        padding-top: 4.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 4.2rem;
    }
}

footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
"""


def apply_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
