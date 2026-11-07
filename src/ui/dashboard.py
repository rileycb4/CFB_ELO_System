"""Streamlit rankings landing page and modal navigation."""
from __future__ import annotations

from html import escape
from typing import Any, Dict, List

import streamlit as st

from .bubble_theme import BUBBLE_CSS
from .data_adapter import available_years, find_last_meeting, load_dashboard_data
from .head_to_head import render_streamlit as render_h2h
from .rankings import filter_teams, sort_teams, ranking_movement


APP_CSS = r"""
<style>
.cfb-page-title {
  background:radial-gradient(ellipse at 50% 0%,#30212B 0%,#171920 70%);
  border:1px solid #3A303B;border-radius:30px;padding:19px 23px;margin:4px 0 17px;
  box-shadow:0 14px 32px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.05);
  display:flex;align-items:center;gap:15px;color:#F5F6FA;font-size:25px;font-weight:850;
}
.cfb-page-title .ball {font-size:30px;border-right:1px solid #403743;padding-right:15px;}
.cfb-table-head {
  display:grid;grid-template-columns:58px minmax(160px,2fr) 90px 100px 76px 80px minmax(140px,1.5fr);
  gap:8px;color:#A9ADBA;font-size:11px;font-weight:850;padding:12px 13px;margin:12px 0 7px;
  background:linear-gradient(145deg,#20232C,#171920);border:1px solid #343844;border-radius:999px;
}
.cfb-rank {text-align:center;font-weight:900;font-size:17px;color:#F5F6FA;padding-top:8px;}
.cfb-cell {text-align:center;color:#E9EAF0;font-size:13px;padding-top:9px;}
.cfb-up {color:#43C58B;font-weight:850;text-align:center;padding-top:9px;}
.cfb-down {color:#F06B7A;font-weight:850;text-align:center;padding-top:9px;}
.cfb-flat {color:#A9ADBA;text-align:center;padding-top:9px;}
.cfb-bye {color:#A9ADBA;text-align:center;font-size:12px;font-weight:900;letter-spacing:1px;padding-top:10px;}
.cfb-row-rule {height:1px;background:#2D303A;margin:5px 0 8px;}
.cfb-footnote {color:#A9ADBA;font-size:12px;padding:14px 7px;}
.schedule-title {
  background:linear-gradient(145deg,#242631,#171920);border:1px solid #343844;
  border-radius:22px;padding:14px 18px;margin:6px 0 13px;color:#F5F6FA;
}
.schedule-head {
  display:grid;grid-template-columns:.45fr .55fr 1.55fr .72fr .82fr .9fr .75fr .75fr .85fr .8fr;
  gap:6px;padding:9px 10px;color:#A9ADBA;font-size:10px;font-weight:900;
  text-align:center;background:#111319;border:1px solid #30343D;border-radius:999px;margin-bottom:8px;
}
.schedule-row {
  display:grid;grid-template-columns:.45fr .55fr 1.55fr .72fr .82fr .9fr .75fr .75fr .85fr .8fr;
  gap:6px;align-items:center;padding:11px 10px;margin:6px 0;
  background:linear-gradient(145deg,#20232C,#171920);border:1px solid #343844;border-radius:18px;
  color:#F5F6FA;font-size:11px;text-align:center;
}
.schedule-row .opp {text-align:left;font-weight:800;font-size:12px;}
.schedule-row .muted {color:#A9ADBA;}
.schedule-row .positive {color:#43C58B;font-weight:800;}
.schedule-row .negative {color:#F06B7A;font-weight:800;}
.schedule-row .unplayed {color:#A9ADBA;font-style:italic;}
@media(max-width:900px) {
 .cfb-table-head {grid-template-columns:38px minmax(110px,1.4fr) 60px 72px 54px 60px minmax(100px,1.1fr);gap:3px;padding:10px 6px;}
 .schedule-head,.schedule-row {grid-template-columns: .4fr .45fr 1.2fr .6fr .65fr .75fr .65fr .65fr .7fr .65fr;gap:3px;padding:8px 5px;font-size:9px;}
}
</style>
"""


def _format_num(value, digits=1):
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _schedule_row(game: Dict[str, Any]):
    played = bool(game.get("played"))
    opp_elo = _format_num(game.get("opponent_elo"))
    delta_elo = f"{float(game['delta_elo']):+.1f}" if played and game.get("delta_elo") is not None else "—"
    delta_rank = f"{int(game['delta_rank']):+d}" if played and game.get("delta_rank") is not None else "—"
    new_elo = _format_num(game.get("new_elo")) if played else "No Elo"
    new_rank = str(game.get("new_rank")) if played and game.get("new_rank") is not None else "No Rank"
    delta_class = "positive" if (delta_elo.startswith("+") or delta_rank.startswith("+")) else "negative"
    unplayed_class = "" if played else "unplayed"
    cells = [
        str(game.get("week", "—")),
        game.get("location", "—"),
        escape(str(game.get("opponent_name", "—"))),
        escape(str(game.get("opponent_record", "—"))),
        opp_elo,
        escape(str(game.get("result", "—"))),
        delta_elo,
        delta_rank,
        new_elo,
        new_rank,
    ]
    return (
        f'<div class="schedule-row">'
        f'<div>{cells[0]}</div><div>{cells[1]}</div><div class="opp">{cells[2]}</div>'
        f'<div>{cells[3]}</div><div>{cells[4]}</div><div class="{unplayed_class}">{cells[5]}</div>'
        f'<div class="{delta_class if played else unplayed_class}">{cells[6]}</div>'
        f'<div class="{delta_class if played else unplayed_class}">{cells[7]}</div>'
        f'<div class="{unplayed_class}">{cells[8]}</div><div class="{unplayed_class}">{cells[9]}</div>'
        f'</div>'
    )


def render_schedule_dialog(team: Dict[str, Any]):
    st.markdown(
        f'<div class="schedule-title"><div style="font-size:21px;font-weight:850">{escape(team["name"])}</div>'
        f'<div style="color:#A9ADBA;font-size:12px;margin-top:5px">{escape(team.get("conference",""))} · '
        f'{escape(team.get("record","—"))} · Elo {_format_num(team.get("elo"))} · '
        f'Rank #{team.get("rank","—")}</div></div>',
        unsafe_allow_html=True,
    )
    headers = ["WK", "LOC", "OPPONENT", "OPP REC", "OPP ELO", "RESULT",
               "Δ ELO", "Δ RANK", "NEW ELO", "NEW RANK"]
    st.markdown(
        '<div class="schedule-head">' + "".join(f"<div>{h}</div>" for h in headers) + "</div>",
        unsafe_allow_html=True,
    )
    schedule = sorted(team.get("schedule", []), key=lambda g: (g.get("week", 0), g.get("date", "")))
    if not schedule:
        st.info("No schedule games are currently available for this team and season.")
        return
    for game in schedule:
        st.markdown(_schedule_row(game), unsafe_allow_html=True)
    st.caption("H = Home · N = Neutral site · A = Away. Unplayed games show No Elo / No Rank.")


def render_dashboard():
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown(f"<style>{BUBBLE_CSS}</style>", unsafe_allow_html=True)

    years = available_years()
    if not years:
        st.error("No seasons are available in the database.")
        return

    # Default to the latest year represented in the database.
    control_a, control_b = st.columns([1.2, 4.8])
    with control_a:
        year = st.selectbox("Season", years, index=len(years) - 1, key="cfb_season")
    with control_b:
        st.markdown(
            '<div style="color:#A9ADBA;text-align:right;padding-top:31px;font-size:12px">'
            'Rankings are calculated from the existing Elo engine</div>',
            unsafe_allow_html=True,
        )

    with st.spinner(f"Calculating {year} season ratings..."):
        data = load_dashboard_data(year)
    teams = data["teams"]
    if not teams:
        st.warning("No FBS/FCS teams were returned for this season.")
        return

    st.markdown(
        '<div class="cfb-page-title"><span class="ball">🏈</span>'
        f'<span>COLLEGE FOOTBALL RANKINGS</span><span style="margin-left:auto;font-size:13px;color:#A9ADBA">'
        f'{year} SEASON</span></div>',
        unsafe_allow_html=True,
    )

    filter_col, search_col, sort_col = st.columns([2.4, 1.2, 1.1])
    conferences = sorted({t.get("conference", "IND") for t in teams})
    with filter_col:
        selected = st.multiselect("Conferences", conferences, default=conferences,
                                  key=f"conf_filter_{year}")
    with search_col:
        search = st.text_input("Find team", placeholder="Team name", key=f"team_search_{year}")
    with sort_col:
        sort_choice = st.selectbox("Sort by", ["Rank / Elo", "Team A–Z", "Record"],
                                   key=f"rank_sort_{year}")

    filtered = filter_teams(teams, selected, search)
    sort_key = {"Rank / Elo": "rank", "Team A–Z": "team", "Record": "record"}[sort_choice]
    visible = sort_teams(filtered, sort_key)

    st.markdown(
        '<div class="cfb-table-head"><div>RANK</div><div>TEAM</div><div style="text-align:center">RECORD</div>'
        '<div style="text-align:center">ELO</div><div style="text-align:center">RANK Δ</div>'
        '<div style="text-align:center">ELO Δ</div><div style="text-align:center">NEXT OPPONENT</div></div>',
        unsafe_allow_html=True,
    )

    @st.dialog("Team Schedule")
    def schedule_dialog(team):
        render_schedule_dialog(team)

    @st.dialog("Head-to-Head")
    def h2h_dialog(home, away):
        meeting = find_last_meeting(home, away)
        render_h2h(st, home, away, meeting, title="Head to Head",
                    key_prefix=f"h2h_{home['espn_id']}_{away['espn_id']}")

    for idx, team in enumerate(visible):
        movement, direction = ranking_movement(team)
        movement_class = {"up": "cfb-up", "down": "cfb-down", "flat": "cfb-flat"}[direction]
        elo_delta = float(team.get("elo_change") or 0)
        elo_class = "cfb-up" if elo_delta > 0 else "cfb-down" if elo_delta < 0 else "cfb-flat"
        row = st.columns([0.48, 2.0, 0.82, 0.92, 0.72, 0.78, 1.55], gap="small")
        with row[0]:
            st.markdown(f'<div class="cfb-rank">{team["rank"]}</div>', unsafe_allow_html=True)
        with row[1]:
            if st.button(f"🏈  {team['name']}", key=f"team_{year}_{team['espn_id']}",
                         help="Open team schedule", use_container_width=True):
                schedule_dialog(team)
        with row[2]:
            st.markdown(f'<div class="cfb-cell">{escape(team["record"])}</div>', unsafe_allow_html=True)
        with row[3]:
            st.markdown(f'<div class="cfb-cell">{_format_num(team["elo"])}</div>', unsafe_allow_html=True)
        with row[4]:
            st.markdown(f'<div class="{movement_class}">{escape(movement)}</div>', unsafe_allow_html=True)
        with row[5]:
            st.markdown(f'<div class="{elo_class}">{elo_delta:+.1f}</div>', unsafe_allow_html=True)
        with row[6]:
            opponent_name = str(team.get("next_opponent") or "BYE")
            if opponent_name.strip().casefold() == "bye":
                st.markdown('<div class="cfb-bye">BYE</div>', unsafe_allow_html=True)
            else:
                opponent = data["teams_by_name"].get(opponent_name)
                if st.button(f"⚔  {opponent_name}", key=f"opp_{year}_{team['espn_id']}",
                             help="Open opponent head-to-head", use_container_width=True):
                    if opponent:
                        h2h_dialog(team, opponent)
                    else:
                        st.warning(f"{opponent_name} is not in the selected team data.")
        st.markdown('<div class="cfb-row-rule"></div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="cfb-footnote">Showing {len(visible)} of {len(teams)} teams · '
        'Rank is calculated from descending Elo. Click a team for its schedule or an opponent for Head-to-Head.</div>',
        unsafe_allow_html=True,
    )
