"""Shared visual tokens for the rounded/bubble CFB interface."""

BG = "#0B0C10"
SURFACE = "#171920"
SURFACE_RAISED = "#20232C"
SURFACE_INNER = "#111319"
BORDER = "#2B2F3A"
TEXT = "#F5F6FA"
MUTED = "#A9ADBA"
CRIMSON = "#C8103E"
CRIMSON_DARK = "#650D29"
GREEN = "#43C58B"
RED = "#F06B7A"

# Streamlit CSS fragment. Import and interpolate into component styles.
BUBBLE_CSS = f"""
.stApp {{
  background: radial-gradient(ellipse at 50% -15%, #25202A 0%, {BG} 52%);
  color: {TEXT};
}}
div[data-testid="stAppViewContainer"] {{ background: transparent; }}
div[data-testid="stHeader"] {{ background: transparent; }}
.stButton > button {{
  border-radius: 999px !important;
  border: 1px solid {BORDER} !important;
  background: linear-gradient(145deg, #242731, #171920) !important;
  color: {TEXT} !important;
  font-weight: 700 !important;
  min-height: 2.55rem;
  box-shadow: 0 5px 16px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.035);
  transition: all .15s ease;
}}
.stButton > button:hover {{
  border-color: {CRIMSON} !important;
  background: linear-gradient(145deg, #38202B, #20171E) !important;
  color: white !important;
}}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {{
  border-radius: 18px !important;
  background: {SURFACE} !important;
  border-color: {BORDER} !important;
}}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
  border-radius: 999px !important;
  background: #4A1729 !important;
}}
div[data-testid="stDialog"] > div {{
  border-radius: 28px !important;
  background: {SURFACE} !important;
  border: 1px solid {BORDER} !important;
}}
div[data-testid="stMetric"] {{
  background: linear-gradient(145deg, {SURFACE_RAISED}, {SURFACE});
  border: 1px solid {BORDER};
  border-radius: 22px;
  padding: 14px 16px;
}}
hr {{ border-color: {BORDER}; }}
"""
