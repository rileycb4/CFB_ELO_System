"""College Football rankings UI for Tkinter and Streamlit.

Expected team data fields:
  name, conference, record ("8-1"), elo, previous_rank, elo_change,
  next_opponent (opponent team name or "BYE"), plus optional logo_text,
  primary, nickname, schedule, and the head-to-head statistics used by
  head_to_head.render_streamlit/render_tkinter.

Rank is derived from descending Elo so Rank and Elo sorting are identical.
"""

from __future__ import annotations

from html import escape
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .bubble_theme import (
        BG, SURFACE as PANEL, SURFACE_RAISED as PANEL_ALT,
        TEXT as FG, MUTED, BORDER, CRIMSON
    )
except ImportError:
    from ui.bubble_theme import (
        BG, SURFACE as PANEL, SURFACE_RAISED as PANEL_ALT,
        TEXT as FG, MUTED, BORDER, CRIMSON
    )

BG = "#101114"
PANEL = "#1B1D21"
PANEL_ALT = "#22252A"
FG = "#F4F5F7"
MUTED = "#AEB3BC"
BORDER = "#383C43"
ACCENT = "#B51232"


def sample_teams() -> List[Dict[str, Any]]:
    """Example data only; replace this list with rows from your database."""
    raw = [
        ("Alabama", "SEC", "7-0", 1876.3, 1, 12.4, "LSU", "A", "#B51232"),
        ("Georgia", "SEC", "7-0", 1842.1, 2, 8.7, "Kentucky", "G", "#BA0C2F"),
        ("Texas", "SEC", "6-1", 1825.7, 4, 15.2, "Oklahoma", "T", "#BF5700"),
        ("Ohio State", "Big Ten", "6-1", 1803.9, 3, -4.1, "Purdue", "O", "#BB0000"),
        ("Notre Dame", "Independent", "6-1", 1789.6, 5, 2.0, "Stanford", "ND", "#C99700"),
        ("Clemson", "ACC", "6-1", 1774.3, 8, 18.5, "SMU", "C", "#F56600"),
        ("Penn State", "Big Ten", "6-1", 1758.9, 6, 3.4, "Wisconsin", "PSU", "#1E407C"),
        ("Oregon", "Big Ten", "6-1", 1749.2, 10, 21.8, "Michigan", "O", "#00843D"),
        ("Miami", "ACC", "6-1", 1735.7, 9, -2.3, "Florida State", "U", "#F47321"),
        ("Michigan", "Big Ten", "6-1", 1728.3, 7, -9.5, "BYE", "M", "#FFCB05"),
        ("LSU", "SEC", "5-2", 1710.4, 12, 5.1, "Alabama", "LSU", "#461D7C"),
        ("Florida State", "ACC", "5-2", 1698.2, 11, -12.0, "Miami", "FSU", "#782F40"),
    ]
    teams = []
    for row in raw:
        name, conf, record, elo, previous_rank, elo_change, opponent, logo, color = row
        teams.append({
            "name": name, "conference": conf, "record": record, "elo": float(elo),
            "previous_rank": previous_rank, "elo_change": float(elo_change),
            "next_opponent": opponent, "logo_text": logo, "primary": color,
            "nickname": name,
            # Placeholder schedule; replace with real game records.
            "schedule": [],
        })
    # Give the demo data enough stats to open the existing H2H module.
    for team in teams:
        team.update({
            "rank": None,
            "points_for": 32.0, "points_against": 18.0,
            "offensive_efficiency": 85.0, "defensive_efficiency": 88.0,
            "strength_of_schedule": 80.0, "average_margin": 14.0,
        })
    return assign_ranks(teams)


def assign_ranks(teams: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return copied team dictionaries with rank assigned by Elo, high to low."""
    ordered = sorted(teams, key=lambda t: float(t.get("elo", 0)), reverse=True)
    result = []
    for rank, team in enumerate(ordered, start=1):
        item = dict(team)
        item["rank"] = rank
        result.append(item)
    return result


def parse_record(record: Any) -> Tuple[int, int]:
    cleaned = str(record or "").replace("–", "-").replace("—", "-").strip()
    try:
        wins, losses = cleaned.split("-", 1)
        return int(wins.strip()), int(losses.strip())
    except (ValueError, TypeError):
        return -1, -1


def record_percentage(record: Any) -> float:
    wins, losses = parse_record(record)
    total = wins + losses
    return wins / total if wins >= 0 and losses >= 0 and total else -1.0


def ranking_movement(team: Dict[str, Any]) -> Tuple[str, str]:
    """Return a display string and direction. Positive means moved up."""
    previous = team.get("previous_rank")
    current = team.get("rank")
    try:
        delta = int(previous) - int(current)
    except (TypeError, ValueError):
        return "—", "flat"
    if delta > 0:
        return f"↑ {delta}", "up"
    if delta < 0:
        return f"↓ {abs(delta)}", "down"
    return "—", "flat"


def elo_change_display(team: Dict[str, Any]) -> str:
    try:
        change = float(team.get("elo_change", 0))
    except (TypeError, ValueError):
        return "—"
    return f"{change:+.1f}"


def sort_teams(teams: Sequence[Dict[str, Any]], sort_by: str = "rank",
               descending: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Sort by rank/Elo, team name, or record.

    Rank and Elo deliberately share the same Elo-descending ordering.
    """
    key = sort_by.lower()
    if key in ("rank", "elo"):
        return sorted(teams, key=lambda t: float(t.get("elo", 0)), reverse=True)
    if key in ("team", "name", "alphabetical"):
        return sorted(teams, key=lambda t: str(t.get("name", "")).casefold(),
                      reverse=bool(descending))
    if key in ("record", "win percentage", "win_pct"):
        return sorted(teams, key=lambda t: (record_percentage(t.get("record")), 
                                             parse_record(t.get("record"))[0]),
                      reverse=True if descending is None else descending)
    return list(teams)


def filter_teams(teams: Sequence[Dict[str, Any]],
                 conferences: Optional[Sequence[str]] = None,
                 search: str = "") -> List[Dict[str, Any]]:
    selected = set(conferences or [])
    query = search.casefold().strip()
    output = []
    for team in teams:
        if selected and team.get("conference") not in selected:
            continue
        if query and query not in str(team.get("name", "")).casefold():
            continue
        output.append(team)
    return output


def _opponent_team(team: Dict[str, Any], teams: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    opponent = team.get("next_opponent")
    if not opponent or str(opponent).strip().casefold() == "bye":
        return None
    for candidate in teams:
        if str(candidate.get("name", "")).casefold() == str(opponent).casefold():
            return candidate
    return None


# ------------------------------- Tkinter ---------------------------------

def render_tkinter(parent, teams: Sequence[Dict[str, Any]], *,
                   title: str = "COLLEGE FOOTBALL RANKINGS"):
    """Render the rankings view inside an existing Tkinter parent.

    Click a team name to open its schedule placeholder. Click an opponent to
    open the previously built head_to_head renderer. BYE is intentionally inert.
    """
    import tkinter as tk
    from tkinter import ttk, messagebox

    all_teams = assign_ranks(teams)
    conferences = sorted({str(t.get("conference", "Independent")) for t in all_teams})
    selected_conferences = set(conferences)
    sort_state = {"by": "rank", "descending": False}

    style = ttk.Style(parent)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Rank.TFrame", background=BG)
    style.configure("RankCard.TFrame", background=PANEL, relief="flat")
    style.configure("Rank.TLabel", background=BG, foreground=FG, font=("Arial", 10))
    style.configure("RankTitle.TLabel", background=PANEL, foreground=FG, font=("Arial", 19, "bold"))
    style.configure("RankMuted.TLabel", background=PANEL, foreground=MUTED, font=("Arial", 9))
    style.configure("Rank.TCheckbutton", background=BG, foreground=FG)
    style.map("Rank.TCheckbutton", background=[("active", BG)], foreground=[("active", FG)])
    style.configure("Rank.Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=FG, rowheight=48, borderwidth=0,
                    font=("Arial", 10), relief="flat")
    style.configure("Rank.Treeview.Heading", background=PANEL_ALT,
                    foreground=MUTED, relief="flat", padding=(12, 11), font=("Arial", 9, "bold"))
    style.map("Rank.Treeview", background=[("selected", "#343943")],
              foreground=[("selected", FG)])

    outer = ttk.Frame(parent, style="Rank.TFrame", padding=12)
    outer.pack(fill="both", expand=True)

    header = ttk.Frame(outer, style="RankCard.TFrame", padding=(16, 14))
    header.pack(fill="x")
    ttk.Label(header, text="🏆", background=PANEL, foreground=FG,
              font=("Arial", 24)).pack(side="left", padx=(0, 14))
    ttk.Label(header, text=title, style="RankTitle.TLabel").pack(side="left")
    ttk.Label(header, text="WEEK 10", style="RankMuted.TLabel").pack(side="right")

    filter_card = ttk.Frame(outer, style="Rank.TFrame", padding=(2, 12))
    filter_card.pack(fill="x")
    ttk.Label(filter_card, text="CONFERENCES", style="Rank.TLabel").pack(side="left", padx=(0, 12))
    filter_vars = {}
    for conference in conferences:
        var = tk.BooleanVar(value=True)
        filter_vars[conference] = var
        ttk.Checkbutton(filter_card, text=conference, variable=var,
                        style="Rank.TCheckbutton",
                        command=lambda: refresh()).pack(side="left", padx=5)

    table_frame = ttk.Frame(outer, style="RankCard.TFrame", padding=8)
    table_frame.pack(fill="both", expand=True)

    columns = ("rank", "team", "record", "elo", "rank_change", "elo_change", "opponent")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                        style="Rank.Treeview", selectmode="browse")
    headings = {
        "rank": "RANK  ↕", "team": "TEAM  ↕", "record": "RECORD  ↕",
        "elo": "ELO  ↕", "rank_change": "RANK Δ", "elo_change": "ELO Δ",
        "opponent": "NEXT OPPONENT",
    }
    widths = {"rank": 65, "team": 220, "record": 100, "elo": 105,
              "rank_change": 90, "elo_change": 90, "opponent": 220}
    for col in columns:
        tree.heading(col, text=headings[col],
                     command=lambda c=col: sort_column(c))
        tree.column(col, width=widths[col], anchor="w" if col in ("team", "opponent") else "center")
    tree.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    tree.tag_configure("up", foreground="#48C78E")
    tree.tag_configure("down", foreground="#F06A75")
    tree.tag_configure("flat", foreground=FG)
    tree.tag_configure("bye", foreground=MUTED)

    visible_items: Dict[str, Dict[str, Any]] = {}

    def current_conferences():
        return [name for name, var in filter_vars.items() if var.get()]

    def refresh():
        for item in tree.get_children():
            tree.delete(item)
        visible = filter_teams(all_teams, current_conferences())
        visible = sort_teams(visible, sort_state["by"], sort_state["descending"])
        visible_items.clear()
        for team in visible:
            movement, direction = ranking_movement(team)
            opponent = str(team.get("next_opponent") or "BYE")
            is_bye = opponent.strip().casefold() == "bye"
            values = (
                team.get("rank", "—"), team.get("name", "—"),
                team.get("record", "—"), f"{float(team.get('elo', 0)):.1f}",
                movement, elo_change_display(team),
                "BYE" if is_bye else opponent,
            )
            iid = tree.insert("", "end", values=values,
                              tags=("bye",) if is_bye else (direction,))
            visible_items[iid] = team

    def sort_column(column):
        if column in ("rank", "elo"):
            sort_state.update(by="rank", descending=False)
        elif column == "team":
            if sort_state["by"] == "team":
                sort_state["descending"] = not sort_state["descending"]
            else:
                sort_state.update(by="team", descending=False)
        elif column == "record":
            if sort_state["by"] == "record":
                sort_state["descending"] = not sort_state["descending"]
            else:
                sort_state.update(by="record", descending=True)
        refresh()

    def open_schedule(team):
        win = tk.Toplevel(parent)
        win.title(f"{team.get('name')} Schedule")
        win.configure(bg=BG)
        win.geometry("520x420")
        box = ttk.Frame(win, style="RankCard.TFrame", padding=18)
        box.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(box, text=f"{team.get('name', 'Team')} SCHEDULE",
                  style="RankTitle.TLabel").pack(anchor="w", pady=(0, 10))
        schedule = team.get("schedule") or []
        if not schedule:
            ttk.Label(box, text="No schedule data available for this season.",
                      style="RankMuted.TLabel").pack(anchor="w")
        else:
            cols = ("week", "location", "opponent", "opp_record", "opp_elo",
                    "result", "delta_elo", "delta_rank", "new_elo", "new_rank")
            table = ttk.Treeview(box, columns=cols, show="headings", height=14)
            labels = {
                "week": "Wk", "location": "Loc.", "opponent": "Opponent",
                "opp_record": "Opp. Rec.", "opp_elo": "Opp. Elo", "result": "Result",
                "delta_elo": "Δ Elo", "delta_rank": "Δ Rank",
                "new_elo": "New Elo", "new_rank": "New Rank",
            }
            widths = {"week": 42, "location": 48, "opponent": 145, "opp_record": 68,
                      "opp_elo": 72, "result": 82, "delta_elo": 66, "delta_rank": 66,
                      "new_elo": 72, "new_rank": 70}
            for col in cols:
                table.heading(col, text=labels[col])
                table.column(col, width=widths[col], anchor="center")
            for game in schedule:
                played = game.get("played", False)
                table.insert("", "end", values=(
                    game.get("week", "—"), game.get("location", "—"),
                    game.get("opponent_name", "—"), game.get("opponent_record", "—"),
                    f"{game['opponent_elo']:.1f}" if game.get("opponent_elo") is not None else "—",
                    game.get("result", "—"),
                    f"{game['delta_elo']:+.1f}" if played and game.get("delta_elo") is not None else "—",
                    f"{game['delta_rank']:+d}" if played and game.get("delta_rank") is not None else "—",
                    f"{game['new_elo']:.1f}" if played and game.get("new_elo") is not None else "No Elo",
                    str(game.get("new_rank")) if played and game.get("new_rank") is not None else "No Rank",
                ))
            table.pack(fill="both", expand=True, pady=(8, 0))

    def open_head_to_head(team, opponent):
        try:
            from .head_to_head import render_tkinter
        except ImportError:
            messagebox.showerror("Missing module", "Place head_to_head.py beside rankings.py.")
            return
        win = tk.Toplevel(parent)
        win.title(f"{team.get('name')} vs {opponent.get('name')} | Head to Head")
        win.geometry("1040x850")
        win.minsize(760, 650)
        win.configure(bg=BG)
        try:
            from .data_adapter import find_last_meeting
            meeting = find_last_meeting(team, opponent)
        except Exception:
            meeting = {"home_score": "—", "away_score": "—",
                       "competition": "Previous meeting", "date": "—"}
        render_tkinter(win, team, opponent, meeting)

    def on_click(event):
        row_id = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)
        if not row_id or row_id not in visible_items:
            return
        team = visible_items[row_id]
        if col_id == "#2":
            open_schedule(team)
        elif col_id == "#7":
            opponent_name = str(team.get("next_opponent") or "BYE")
            if opponent_name.strip().casefold() == "bye":
                return
            opponent = _opponent_team(team, all_teams)
            if opponent:
                open_head_to_head(team, opponent)
            else:
                messagebox.showinfo("Opponent unavailable",
                                       f"{opponent_name} is not in the currently loaded team data.")

    tree.bind("<ButtonRelease-1>", on_click)
    refresh()
    return outer


def show_desktop(teams: Optional[Sequence[Dict[str, Any]]] = None):
    import tkinter as tk
    root = tk.Tk()
    root.title("College Football Rankings")
    root.geometry("1050x780")
    root.minsize(820, 600)
    root.configure(bg=BG)
    render_tkinter(root, teams or sample_teams())
    root.mainloop()


# ------------------------------ Streamlit --------------------------------

def render_streamlit(st, teams: Sequence[Dict[str, Any]], *,
                     title: str = "College Football Rankings",
                     key_prefix: str = "cfb_rankings"):
    """Render rankings in Streamlit with same-screen conference multi-filter.

    Team buttons open a schedule dialog placeholder. Opponent buttons open
    the reusable Head-to-Head dialog. BYE is displayed as inert text.
    """
    all_teams = assign_ranks(teams)
    conferences = sorted({str(t.get("conference", "Independent")) for t in all_teams})

    st.markdown(f"""
    <style>
    .rank-shell {{
      background:radial-gradient(ellipse at 50% 0%,#29212B 0%,#171920 68%);
      border:1px solid #34313C;border-radius:32px;padding:20px 22px;margin:4px 0 16px;
      box-shadow:0 15px 34px rgba(0,0,0,.27),inset 0 1px 0 rgba(255,255,255,.055);
    }}
    .rank-header {{display:flex;align-items:center;gap:14px;color:#F5F6FA;font-size:24px;font-weight:850;padding:4px 2px 5px;}}
    .rank-trophy {{font-size:30px;border-right:1px solid #3A3E49;padding-right:16px;}}
    .rank-sub {{color:#A9ADBA;font-size:11px;letter-spacing:1px;font-weight:800;}}
    .rank-table-head {{
      display:grid;grid-template-columns:58px minmax(160px,2fr) 90px 100px 76px 80px minmax(140px,1.5fr);gap:8px;
      color:#A9ADBA;font-size:11px;font-weight:850;padding:13px 13px;margin:12px 0 8px;
      background:linear-gradient(145deg,#20232C,#171920);border:1px solid #343844;border-radius:999px;
    }}
    .rank-num {{font-size:17px;font-weight:850;text-align:center;}}
    .rank-stat {{font-size:13px;text-align:center;font-weight:650;}}
    .rank-delta-up {{color:#43C58B;font-weight:850;text-align:center;}}
    .rank-delta-down {{color:#F06B7A;font-weight:850;text-align:center;}}
    .rank-delta-flat {{color:#A9ADBA;text-align:center;}}
    .rank-bye {{color:#A9ADBA;font-weight:850;text-align:center;letter-spacing:1px;}}
    .rank-footer {{color:#A9ADBA;font-size:12px;padding:14px 8px 2px;}}
    div[data-testid="stHorizontalBlock"] {{align-items:center;}}
    @media(max-width:760px) {{
      .rank-table-head {{grid-template-columns:36px minmax(112px,1.5fr) 58px 70px 54px 60px minmax(105px,1.2fr);gap:3px;padding-left:7px;padding-right:7px;}}
      .rank-stat {{font-size:11px;}} .rank-header {{font-size:19px;}}
    }}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"<style>{BUBBLE_CSS}</style>", unsafe_allow_html=True)

    st.markdown(f'<div class="rank-shell"><div class="rank-header"><span class="rank-trophy">🏆</span>{escape(title)}<span style="margin-left:auto;color:{MUTED};font-size:14px">WEEK 10</span></div></div>', unsafe_allow_html=True)

    # Filters and sort controls are kept on the rankings screen.
    filter_col, search_col, sort_col = st.columns([2.4, 1.2, 1.1])
    with filter_col:
        selected = st.multiselect("Conferences", conferences, default=conferences,
                                  key=f"{key_prefix}_conferences",
                                  help="Select one or more conferences to compare them together.")
    with search_col:
        search = st.text_input("Find team", key=f"{key_prefix}_search", placeholder="Team name")
    with sort_col:
        sort_choice = st.selectbox("Sort by", ["Rank / Elo", "Team A–Z", "Record"],
                                   key=f"{key_prefix}_sort")
    filtered = filter_teams(all_teams, selected, search)
    sort_key = {"Rank / Elo": "rank", "Team A–Z": "team", "Record": "record"}[sort_choice]
    visible = sort_teams(filtered, sort_key)

    st.markdown("""
    <div class="rank-table-head">
      <div>RANK</div><div>TEAM</div><div style="text-align:center">RECORD</div>
      <div style="text-align:center">ELO</div><div style="text-align:center">RANK Δ</div>
      <div style="text-align:center">ELO Δ</div><div style="text-align:center">NEXT OPPONENT</div>
    </div>
    """, unsafe_allow_html=True)

    # Dialogs are defined once per render; they are opened by the row buttons.
    @st.dialog("Team schedule")
    def schedule_dialog(team):
        st.subheader(f"{team.get('name', 'Team')} schedule")
        schedule = team.get("schedule") or []
        if not schedule:
            st.info("Schedule viewer placeholder. Connect this dialog to your game schedule data.")
        else:
            st.dataframe(schedule, use_container_width=True, hide_index=True)

    @st.dialog("Head-to-Head")
    def h2h_dialog(home, away):
        st.caption(f"{home.get('name')} vs {away.get('name')}")
        from ui.head_to_head import render_streamlit as render_h2h
        render_h2h(st, home, away, {
            "home_score": "—", "away_score": "—",
            "competition": "Previous meeting", "date": "Connect game history",
        }, title="Head to Head", key_prefix=f"{key_prefix}_h2h")

    for idx, team in enumerate(visible):
        movement, direction = ranking_movement(team)
        movement_class = {"up": "rank-delta-up", "down": "rank-delta-down", "flat": "rank-delta-flat"}[direction]
        elo_delta = elo_change_display(team)
        opponent_name = str(team.get("next_opponent") or "BYE")
        is_bye = opponent_name.strip().casefold() == "bye"

        # Layout columns line up with the visual header. Buttons provide the
        # actual click targets without making the whole row ambiguous.
        cells = st.columns([0.48, 2.0, 0.82, 0.92, 0.72, 0.78, 1.55], gap="small")
        with cells[0]:
            st.markdown(f'<div class="rank-num">{team.get("rank", "—")}</div>', unsafe_allow_html=True)
        with cells[1]:
            if st.button(f"🏈  {team.get('logo_text', str(team.get('name','?'))[:2])}  {team.get('name','—')}",
                         key=f"{key_prefix}_team_{idx}_{team.get('name')}",
                         help="Open team schedule", use_container_width=True):
                schedule_dialog(team)
        with cells[2]:
            st.markdown(f'<div class="rank-stat">{escape(str(team.get("record", "—")))}</div>', unsafe_allow_html=True)
        with cells[3]:
            try:
                elo_text = f"{float(team.get('elo', 0)):.1f}"
            except (TypeError, ValueError):
                elo_text = "—"
            st.markdown(f'<div class="rank-stat">{elo_text}</div>', unsafe_allow_html=True)
        with cells[4]:
            st.markdown(f'<div class="{movement_class}">{escape(movement)}</div>', unsafe_allow_html=True)
        with cells[5]:
            color = "#48C78E" if elo_delta.startswith("+") else "#F06A75" if elo_delta.startswith("-") else MUTED
            st.markdown(f'<div class="rank-stat" style="color:{color};font-weight:800">{escape(elo_delta)}</div>', unsafe_allow_html=True)
        with cells[6]:
            if is_bye:
                st.markdown('<div class="rank-bye">BYE</div>', unsafe_allow_html=True)
            else:
                opponent = _opponent_team(team, all_teams)
                if st.button(f"⚔  {opponent_name}", key=f"{key_prefix}_opp_{idx}_{team.get('name')}",
                             help="Open head-to-head comparison", use_container_width=True):
                    if opponent:
                        h2h_dialog(team, opponent)
                    else:
                        st.warning(f"{opponent_name} is not in the currently loaded team data.")

    st.markdown(f'<div class="rank-footer">Showing {len(visible)} of {len(all_teams)} teams · Rank is calculated from descending Elo rating.</div>', unsafe_allow_html=True)


__all__ = [
    "sample_teams", "assign_ranks", "parse_record", "record_percentage",
    "ranking_movement", "elo_change_display", "sort_teams", "filter_teams",
    "render_tkinter", "render_streamlit", "show_desktop",
]
