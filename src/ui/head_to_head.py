"""
Reusable College Football Head-to-Head comparison module.

Works in two environments:
  1. Tkinter desktop: launch desktop_app.py
  2. Streamlit: import render_streamlit from head_to_head.py

No third-party dependencies are required for the Tkinter desktop app.
Streamlit is required only when running the Streamlit example.
"""

from __future__ import annotations

from html import escape
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .bubble_theme import BG, SURFACE as PANEL, SURFACE_RAISED as PANEL2, TEXT as FG, MUTED, BORDER as LINE, CRIMSON, CRIMSON_DARK, BUBBLE_CSS
except ImportError:
    from ui.bubble_theme import BG, SURFACE as PANEL, SURFACE_RAISED as PANEL2, TEXT as FG, MUTED, BORDER as LINE, CRIMSON, CRIMSON_DARK, BUBBLE_CSS


DEFAULT_HOME = {
    "name": "Alabama",
    "nickname": "Crimson Tide",
    "rank": 4,
    "record": "8–1",
    "logo_text": "A",
    "primary": "#B51232",
    "elo": 1876,
    "points_for": 38.4,
    "points_against": 15.2,
    "offensive_efficiency": 91.3,
    "defensive_efficiency": 94.1,
    "strength_of_schedule": 82.6,
    "average_margin": 23.2,
}
DEFAULT_AWAY = {
    "name": "Georgia",
    "nickname": "Bulldogs",
    "rank": 7,
    "record": "7–2",
    "logo_text": "G",
    "primary": "#BA0C2F",
    "elo": 1842,
    "points_for": 34.1,
    "points_against": 18.7,
    "offensive_efficiency": 87.6,
    "defensive_efficiency": 89.8,
    "strength_of_schedule": 79.4,
    "average_margin": 15.4,
}

METRICS = [
    ("Current Rank", "rank", "number", False),
    ("Elo Rating", "elo", "number", True),
    ("Record", "record", "record", None),
    ("Points Per Game", "points_for", "decimal", True),
    ("Points Allowed Per Game", "points_against", "decimal", False),
    ("Offensive Efficiency", "offensive_efficiency", "decimal", True),
    ("Defensive Efficiency", "defensive_efficiency", "decimal", True),
    ("Strength of Schedule", "strength_of_schedule", "decimal", True),
    ("Average Margin", "average_margin", "decimal", True),
]


def sample_data() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Return editable example teams and last-meeting information."""
    home, away = dict(DEFAULT_HOME), dict(DEFAULT_AWAY)
    meeting = {
        "home_score": 27,
        "away_score": 24,
        "competition": "SEC Championship",
        "date": "December 6, 2025",
    }
    return home, away, meeting


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_display(team: Dict[str, Any], key: str, kind: str) -> str:
    value = team.get(key, "—")
    if value is None or value == "":
        return "—"
    if kind == "decimal":
        number = _as_float(value)
        return f"{number:.1f}" if number is not None else str(value)
    return str(value)


def _metric_score(team: Dict[str, Any], key: str, kind: str) -> Optional[float]:
    value = team.get(key)
    if kind == "record":
        # Supports records such as 8-1, 8–1, or 8/1.
        cleaned = str(value).replace("–", "-").replace("—", "-").replace("/", "-")
        try:
            wins, losses = cleaned.split("-", 1)
            w, l = float(wins.strip()), float(losses.strip())
            return w / (w + l) if (w + l) else None
        except (ValueError, AttributeError):
            return None
    return _as_float(value)


def _winner(home: Dict[str, Any], away: Dict[str, Any], key: str, higher_is_better: Optional[bool], kind: str) -> Optional[str]:
    if higher_is_better is None:
        return None
    h = _metric_score(home, key, kind)
    a = _metric_score(away, key, kind)
    if h is None or a is None or h == a:
        return None
    if kind == "number" and key == "rank":
        # A lower poll/ranking number is better.
        return "home" if h < a else "away"
    return ("home" if h > a else "away") if higher_is_better else ("home" if h < a else "away")


def comparison_summary(home: Dict[str, Any], away: Dict[str, Any]) -> Dict[str, Any]:
    wins = {"home": 0, "away": 0}
    for label, key, kind, higher in METRICS:
        winner = _winner(home, away, key, higher, kind)
        if winner:
            wins[winner] += 1
    leader = "home" if wins["home"] > wins["away"] else "away" if wins["away"] > wins["home"] else "tie"
    return {"wins": wins, "leader": leader, "categories": len(METRICS)}


def _safe_color(value: Any, fallback: str) -> str:
    color = str(value or fallback)
    if len(color) == 7 and color.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in color[1:]):
        return color
    return fallback


# ------------------------------- Tkinter ---------------------------------

def render_tkinter(parent, home: Dict[str, Any], away: Dict[str, Any],
                   meeting: Optional[Dict[str, Any]] = None,
                   *, title: str = "HEAD TO HEAD"):
    """
    Render the comparison inside an existing Tkinter parent.

    Returns the outer ttk.Frame. The caller owns the Tk root/window.
    """
    import tkinter as tk
    from tkinter import ttk

    meeting = meeting or {}
    bg, panel, panel2 = BG, PANEL, PANEL2
    fg, muted, line = FG, MUTED, LINE
    home_color = _safe_color(home.get("primary"), "#B51232")
    away_color = _safe_color(away.get("primary"), "#BA0C2F")

    style = ttk.Style(parent)
    try:
        style.theme_use("clam")
    except tk.TclError:
        print("Warning: Unable to set Tkinter theme to 'clam'. Using default theme.")
        pass
    style.configure("H2H.TFrame", background=bg)
    style.configure("Card.TFrame", background=panel, relief="flat")
    style.configure("H2H.TLabel", background=bg, foreground=fg, font=("Arial", 10))
    style.configure("Muted.TLabel", background=panel, foreground=muted, font=("Arial", 9))
    style.configure("Card.TLabel", background=panel, foreground=fg, font=("Arial", 10))
    style.configure("Section.TLabel", background=panel, foreground=fg, font=("Arial", 14, "bold"), padding=(4, 3))
    style.configure("Team.TLabel", background=panel, foreground=fg, font=("Arial", 17, "bold"))
    style.configure("LogoHome.TLabel", background=panel, foreground=home_color, font=("Arial", 34, "bold"))
    style.configure("LogoAway.TLabel", background=panel, foreground=away_color, font=("Arial", 34, "bold"))
    style.configure("Metric.TLabel", background=panel, foreground=fg, font=("Arial", 9))
    style.configure("Value.TLabel", background=panel, foreground=fg, font=("Arial", 10, "bold"))
    style.configure("H2H.TNotebook", background=bg, borderwidth=0)
    style.configure("H2H.TNotebook.Tab", background=panel2, foreground=muted, padding=(18, 11), font=("Arial", 9, "bold"), borderwidth=0)
    style.map("H2H.TNotebook.Tab", background=[("selected", CRIMSON_DARK)], foreground=[("selected", fg)])
    style.configure("Home.Horizontal.TProgressbar", troughcolor="#34373D", background=home_color, bordercolor="#34373D", lightcolor=home_color, darkcolor=home_color)
    style.configure("Away.Horizontal.TProgressbar", troughcolor="#34373D", background=away_color, bordercolor="#34373D", lightcolor=away_color, darkcolor=away_color)

    outer = ttk.Frame(parent, style="H2H.TFrame", padding=12)
    outer.pack(fill="both", expand=True)

    header = ttk.Frame(outer, style="Card.TFrame", padding=(16, 14))
    header.pack(fill="x")
    ttk.Label(header, text="×", style="Team.TLabel").pack(side="left", padx=(0, 18))
    ttk.Label(header, text=title, style="Section.TLabel").pack(side="top")
    teams = ttk.Frame(header, style="Card.TFrame")
    teams.pack(fill="x", pady=(14, 2))
    left = ttk.Frame(teams, style="Card.TFrame")
    left.pack(side="left", expand=True, fill="x")
    ttk.Label(left, text=f"#{home.get('rank', '—')}", style="Muted.TLabel").pack(anchor="w")
    ttk.Label(left, text=home.get("logo_text", home.get("name", "?")[:1]), style="LogoHome.TLabel").pack(side="left", padx=(4, 12))
    namebox = ttk.Frame(left, style="Card.TFrame")
    namebox.pack(side="left", anchor="center")
    ttk.Label(namebox, text=str(home.get("name", "Home")).upper(), style="Team.TLabel").pack(anchor="w")
    ttk.Label(namebox, text=str(home.get("nickname", "")), style="Muted.TLabel").pack(anchor="w")

    vs = ttk.Label(teams, text="VS", style="Section.TLabel")
    vs.pack(side="left", padx=18)

    right = ttk.Frame(teams, style="Card.TFrame")
    right.pack(side="right", expand=True, fill="x")
    ttk.Label(right, text=f"#{away.get('rank', '—')}", style="Muted.TLabel").pack(anchor="e")
    ttk.Label(right, text=away.get("logo_text", away.get("name", "?")[:1]), style="LogoAway.TLabel").pack(side="right", padx=(12, 4))
    namebox2 = ttk.Frame(right, style="Card.TFrame")
    namebox2.pack(side="right", anchor="center")
    ttk.Label(namebox2, text=str(away.get("name", "Away")).upper(), style="Team.TLabel").pack(anchor="e")
    ttk.Label(namebox2, text=str(away.get("nickname", "")), style="Muted.TLabel").pack(anchor="e")

    notebook = ttk.Notebook(outer, style="H2H.TNotebook")
    notebook.pack(fill="both", expand=True, pady=(8, 0))
    comparison_tab = ttk.Frame(notebook, style="H2H.TFrame", padding=8)
    overview_tab = ttk.Frame(notebook, style="H2H.TFrame", padding=8)
    history_tab = ttk.Frame(notebook, style="H2H.TFrame", padding=8)
    ranking_tab = ttk.Frame(notebook, style="H2H.TFrame", padding=8)
    notebook.add(overview_tab, text="OVERVIEW")
    notebook.add(history_tab, text="MATCHUP HISTORY")
    notebook.add(comparison_tab, text="TEAM COMPARISON")
    notebook.add(ranking_tab, text="RANKINGS")

    # Last meeting card.
    last = ttk.Frame(comparison_tab, style="Card.TFrame", padding=12)
    last.pack(fill="x", pady=(0, 10))
    ttk.Label(last, text="LAST MEETING", style="Muted.TLabel").pack(anchor="w")
    score = ttk.Frame(last, style="Card.TFrame")
    score.pack(pady=(5, 0))
    ttk.Label(score, text=str(home.get("name", "Home")), style="Card.TLabel").pack(side="left", padx=8)
    ttk.Label(score, text=str(meeting.get("home_score", "—")), style="Section.TLabel").pack(side="left", padx=4)
    ttk.Label(score, text="–", style="Muted.TLabel").pack(side="left", padx=4)
    ttk.Label(score, text=str(meeting.get("away_score", "—")), style="Section.TLabel").pack(side="left", padx=4)
    ttk.Label(score, text=str(away.get("name", "Away")), style="Card.TLabel").pack(side="left", padx=8)
    ttk.Label(last, text=f"{meeting.get('competition', 'Previous meeting')}  •  {meeting.get('date', 'Date unavailable')}", style="Muted.TLabel").pack(pady=(4, 0))

    card = ttk.Frame(comparison_tab, style="Card.TFrame", padding=12)
    card.pack(fill="both", expand=True)
    ttk.Label(card, text="SEASON COMPARISON", style="Section.TLabel").pack(pady=(0, 12))
    ttk.Label(card, text=f"{home.get('name', 'Home')}  vs  {away.get('name', 'Away')}", style="Muted.TLabel").pack(pady=(0, 8))

    for label, key, kind, higher in METRICS:
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        winner = _winner(home, away, key, higher, kind)
        hv = _metric_display(home, key, kind)
        av = _metric_display(away, key, kind)
        ttk.Label(row, text=hv, style="Value.TLabel", width=8, anchor="w").pack(side="left")
        hb = ttk.Progressbar(row, style="Home.Horizontal.TProgressbar", maximum=100, length=105)
        ab = ttk.Progressbar(row, style="Away.Horizontal.TProgressbar", maximum=100, length=105)
        # Bars are relative within this pair; values remain the source of truth.
        hs, as_ = _metric_score(home, key, kind), _metric_score(away, key, kind)
        if hs is not None and as_ is not None:
            total = abs(hs) + abs(as_)
            hp = (abs(hs) / total * 100) if total else 50
            ap = (abs(as_) / total * 100) if total else 50
            hb["value"], ab["value"] = hp, ap
        else:
            hb["value"], ab["value"] = 50, 50
        hb.pack(side="left", fill="x", expand=True, padx=(2, 4))
        ttk.Label(row, text=label, style="Metric.TLabel", width=25, anchor="center").pack(side="left")
        ab.pack(side="left", fill="x", expand=True, padx=(4, 2))
        ttk.Label(row, text=av, style="Value.TLabel", width=8, anchor="e").pack(side="right")
        if winner:
            # Small indicator that doesn't depend on color alone.
            ttk.Label(row, text="●" if winner == "home" else "●", foreground=home_color if winner == "home" else away_color, background=panel).pack(side="right", padx=3)

    summary = comparison_summary(home, away)
    leader = summary["leader"]
    if leader == "tie":
        message = f"EVEN MATCHUP  •  {summary['wins']['home']}–{summary['wins']['away']} category split"
    else:
        leader_name = home["name"] if leader == "home" else away["name"]
        count = summary["wins"][leader]
        message = f"EDGE: {leader_name.upper()}  •  Leads in {count} of {summary['categories']} categories"
    ttk.Label(card, text=message, style="Section.TLabel").pack(anchor="w", pady=(14, 2))

    for tab, heading, body in [
        (overview_tab, "MATCHUP OVERVIEW", "Use this tab for matchup notes, team profiles, and your model's overall rating."),
        (history_tab, "HEAD-TO-HEAD HISTORY", "Add prior meetings here, including date, venue, score, and winner."),
        (ranking_tab, "RANKING BREAKDOWN", "Show each team's national rank, conference rank, Elo rating, and rating movement."),
    ]:
        box = ttk.Frame(tab, style="Card.TFrame", padding=18)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text=heading, style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(box, text=body, style="Muted.TLabel", wraplength=600).pack(anchor="w")

    return outer


# ------------------------------ Streamlit --------------------------------

def render_streamlit(st, home: Dict[str, Any], away: Dict[str, Any],
                     meeting: Optional[Dict[str, Any]] = None,
                     *, title: str = "Head to Head", key_prefix: str = "h2h"):
    """
    Render a Streamlit-friendly comparison module.

    Pass the imported `streamlit` module as the first argument:
        import streamlit as st
        from head_to_head import render_streamlit
        render_streamlit(st, home, away, meeting)
    """
    meeting = meeting or {}
    home_color = _safe_color(home.get("primary"), "#B51232")
    away_color = _safe_color(away.get("primary"), "#BA0C2F")

    st.markdown(f"""
    <style>
    .h2h-shell {{
      background: radial-gradient(ellipse at 50% 0%, #29212B 0%, #171920 65%);
      color:#F5F6FA; border:1px solid #34313C; border-radius:34px;
      padding:24px; margin:5px 0 18px;
      box-shadow:0 16px 36px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.055);
    }}
    .h2h-title {{ text-align:center; font-size:23px; font-weight:850; letter-spacing:1.3px; margin-bottom:22px; }}
    .h2h-teams {{ display:grid; grid-template-columns:1fr 76px 1fr; align-items:center; gap:12px; }}
    .h2h-team {{ display:flex; align-items:center; gap:13px; min-width:0; }}
    .h2h-team.right {{ justify-content:flex-end; text-align:right; }}
    .h2h-logo {{ font-size:48px; line-height:1; font-weight:900; min-width:50px; text-align:center; }}
    .h2h-name {{ font-size:21px; font-weight:850; line-height:1.15; }}
    .h2h-sub {{ color:#A9ADBA; font-size:13px; margin-top:5px; }}
    .h2h-rank {{ color:#A9ADBA; font-size:12px; }}
    .h2h-vs {{
      text-align:center; font-size:19px; font-weight:850; padding:17px 8px;
      border-radius:999px; background:linear-gradient(145deg,#2B2E39,#171920);
      border:1px solid #3A3E49; box-shadow:inset 0 1px 0 rgba(255,255,255,.06);
    }}
    .h2h-card {{
      background:linear-gradient(145deg,#20232C,#171920); border:1px solid #343844;
      border-radius:27px; padding:17px 20px; margin-top:16px;
      box-shadow:0 10px 24px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.035);
    }}
    .h2h-eyebrow {{ color:#A9ADBA; font-size:11px; font-weight:850; letter-spacing:1.1px; }}
    .h2h-score {{
      display:flex; justify-content:center; align-items:center; gap:13px;
      font-size:18px; font-weight:750; margin-top:9px;
      background:#111319; border:1px solid #292D36; border-radius:999px; padding:13px 15px;
    }}
    .h2h-score strong {{ font-size:29px; }}
    .h2h-meta {{ text-align:center; color:#A9ADBA; font-size:12px; margin-top:7px; }}
    .h2h-metric {{
      display:grid; grid-template-columns:65px minmax(50px,1fr) minmax(130px,1.2fr) minmax(50px,1fr) 65px;
      align-items:center; gap:9px; margin:12px 0;
      background:#111319; border:1px solid #252934; border-radius:999px; padding:7px 12px;
    }}
    .h2h-value {{ font-size:14px; font-weight:800; }}
    .h2h-value.right {{ text-align:right; }}
    .h2h-label {{ color:#E6E8ED; text-align:center; font-size:12px; }}
    .h2h-track {{ background:#30343F; height:10px; border-radius:999px; overflow:hidden; }}
    .h2h-fill {{ height:100%; border-radius:999px; }}
    .h2h-edge {{
      background:linear-gradient(105deg,#74102F 0%,#3B1729 45%,#211B27 100%);
      border:1px solid #8A2544; border-radius:25px; padding:17px 20px; margin-top:17px;
      font-weight:850; box-shadow:0 9px 25px rgba(111,13,45,.22);
    }}
    .h2h-edge small {{ display:block; color:#E0C9D1; font-weight:450; margin-top:4px; }}
    @media(max-width:650px) {{
      .h2h-shell {{ padding:14px; border-radius:25px; }}
      .h2h-name {{font-size:15px;}} .h2h-logo {{font-size:34px; min-width:34px;}}
      .h2h-metric {{grid-template-columns:42px minmax(20px,1fr) minmax(88px,1.3fr) minmax(20px,1fr) 42px;gap:4px;padding:7px 8px;}}
      .h2h-value {{font-size:11px;}} .h2h-label {{font-size:10px;}}
      .h2h-score {{gap:6px;font-size:13px;}} .h2h-score strong {{font-size:22px;}}
    }}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"<style>{BUBBLE_CSS}</style>", unsafe_allow_html=True)

    home_name, away_name = escape(str(home.get("name", "Home"))), escape(str(away.get("name", "Away")))
    home_nick, away_nick = escape(str(home.get("nickname", ""))), escape(str(away.get("nickname", "")))
    home_logo = escape(str(home.get("logo_text", home_name[:1])))
    away_logo = escape(str(away.get("logo_text", away_name[:1])))

    st.markdown(f"""
    <section class="h2h-shell">
      <div class="h2h-title">{escape(title.upper())}</div>
      <div class="h2h-teams">
        <div class="h2h-team">
          <div class="h2h-logo" style="color:{home_color}">{home_logo}</div>
          <div><div class="h2h-rank">#{escape(str(home.get('rank','—')))}</div>
            <div class="h2h-name">{home_name}</div><div class="h2h-sub">{home_nick}</div></div>
        </div>
        <div class="h2h-vs">VS</div>
        <div class="h2h-team right">
          <div><div class="h2h-rank">#{escape(str(away.get('rank','—')))}</div>
            <div class="h2h-name">{away_name}</div><div class="h2h-sub">{away_nick}</div></div>
          <div class="h2h-logo" style="color:{away_color}">{away_logo}</div>
        </div>
      </div>
    </section>
    """, unsafe_allow_html=True)

    overview, history, comparison, rankings = st.tabs(["Overview", "Matchup History", "Team Comparison", "Rankings"])
    with overview:
        st.subheader("Matchup overview")
        st.write(f"**{home_name}** ({home.get('record', '—')}) vs **{away_name}** ({away.get('record', '—')})")
        st.caption("Add model notes, team summaries, and matchup context here.")
    with history:
        st.subheader("Head-to-head history")
        st.caption("Connect your historical game records here to show previous meetings.")
    with comparison:
        st.markdown(f"""
        <div class="h2h-card">
          <div class="h2h-eyebrow">LAST MEETING</div>
          <div class="h2h-score"><span>{home_name}</span><strong>{escape(str(meeting.get('home_score','—')))}</strong>
          <span>–</span><strong>{escape(str(meeting.get('away_score','—')))}</strong><span>{away_name}</span></div>
          <div class="h2h-meta">{escape(str(meeting.get('competition','Previous meeting')))} · {escape(str(meeting.get('date','Date unavailable')))}</div>
        </div>
        <div class="h2h-card"><div class="h2h-title">SEASON COMPARISON</div>
        """, unsafe_allow_html=True)

        for label, key, kind, higher in METRICS:
            hv = _metric_display(home, key, kind)
            av = _metric_display(away, key, kind)
            hs, avn = _metric_score(home, key, kind), _metric_score(away, key, kind)
            if hs is not None and avn is not None:
                total = abs(hs) + abs(avn)
                hp = abs(hs) / total * 100 if total else 50
                ap = abs(avn) / total * 100 if total else 50
            else:
                hp = ap = 50
            st.markdown(f"""
            <div class="h2h-metric">
              <div class="h2h-value">{escape(hv)}</div>
              <div class="h2h-track"><div class="h2h-fill" style="width:{hp:.1f}%;background:{home_color}"></div></div>
              <div class="h2h-label">{escape(label)}</div>
              <div class="h2h-track"><div class="h2h-fill" style="width:{ap:.1f}%;background:{away_color}"></div></div>
              <div class="h2h-value right">{escape(av)}</div>
            </div>
            """, unsafe_allow_html=True)

        summary = comparison_summary(home, away)
        if summary["leader"] == "tie":
            edge = f"EVEN MATCHUP · {summary['wins']['home']}–{summary['wins']['away']} category split"
            detail = "Neither team leads the comparison."
        else:
            leader = home_name if summary["leader"] == "home" else away_name
            edge = f"EDGE: {leader.upper()}"
            detail = f"Leads in {summary['wins'][summary['leader']]} of {summary['categories']} categories."
        st.markdown(f'<div class="h2h-edge">🏆 {edge}<small>{detail}</small></div></div>', unsafe_allow_html=True)
    with rankings:
        st.subheader("Ranking breakdown")
        cols = st.columns(2)
        for col, team in zip(cols, (home, away)):
            with col:
                st.metric(f"{team.get('name', 'Team')} rank", f"#{team.get('rank', '—')}")
                st.metric("Elo rating", team.get("elo", "—"))
                st.metric("Record", team.get("record", "—"))


def show_desktop(home: Optional[Dict[str, Any]] = None,
                 away: Optional[Dict[str, Any]] = None,
                 meeting: Optional[Dict[str, Any]] = None):
    """Launch a standalone Tkinter window using the supplied or sample data."""
    import tkinter as tk
    h, a, m = (home, away, meeting)
    if h is None or a is None:
        dh, da, dm = sample_data()
        h, a, m = h or dh, a or da, m or dm
    root = tk.Tk()
    root.title(f"{h.get('name', 'Home')} vs {a.get('name', 'Away')} | Head to Head")
    root.geometry("1040x850")
    root.minsize(760, 650)
    root.configure(bg="#101114")
    render_tkinter(root, h, a, m)
    root.mainloop()


__all__ = [
    "METRICS", "sample_data", "comparison_summary",
    "render_tkinter", "render_streamlit", "show_desktop",
]
