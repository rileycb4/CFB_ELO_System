import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime

from src.main import (
    get_available_years, calculate_multi_year_elo,
    get_poll_comparison, calculate_playoff_picture
)
from src.data_fetcher import update_latest_data, fetch_full_historical_data

st.set_page_config(page_title="NCAA Advanced Team System", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for rich aesthetics and hover tooltips
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E3C72 0%, #2A5298 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid #1E3C72;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .tooltip-box {
        position: relative;
        display: inline-block;
        border-bottom: 1px dashed #666;
        cursor: help;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🏈 NCAA College Football Advanced ELO System</div>', unsafe_allow_html=True)

# Top Bar / Controls
years_list = get_available_years()
current_yr = datetime.now().year
default_idx = years_list.index(current_yr) if current_yr in years_list else len(years_list) - 1

col_year, col_sync, col_backfill = st.columns([2, 1.5, 2])

with col_year:
    selected_year = st.selectbox("📅 Select Season Year", options=years_list, index=default_idx)

with col_sync:
    st.write("")
    st.write("")
    if st.button("🔄 Sync Latest Data"):
        with st.spinner("Updating recent scores and games..."):
            update_latest_data()
            st.cache_data.clear()
            st.success("Sync completed!")
            st.rerun()

with col_backfill:
    st.write("")
    st.write("")
    if st.button("📥 Run Full Historical Backfill"):
        with st.spinner("Backfilling 2001-present historical data across all divisions..."):
            fetch_full_historical_data()
            st.cache_data.clear()
            st.success("Historical backfill completed!")
            st.rerun()

# Cache calculation per year
@st.cache_data(show_spinner="Calculating ELO rankings & Strength of Schedule...")
def get_season_data(year):
    return calculate_multi_year_elo(year)

season_data = get_season_data(selected_year)
teams = season_data['teams']
final_elos = season_data['final_elos']
final_ranks = season_data['final_ranks']
power_elos = season_data['power_elos']
sos_ranks = season_data['sos_ranks']
sos_values = season_data['sos_values']
sos_adjs = season_data['sos_adjs']
weekly_deltas = season_data['weekly_deltas']
weekly_opps = season_data['weekly_opponents']
weekly_opp_elos = season_data['weekly_opp_elos']
preseason_ranks = season_data['preseason_ranks']
all_histories = season_data['all_histories']

# Create 8 Web Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏆 Top 25 (Home)",
    "📊 Full Power ELO Rankings",
    "💪 Strength of Schedule",
    "🔍 Team Schedule Detail",
    "⚖️ Poll Comparison",
    "🏟️ Playoff Picture",
    "📖 About & Formulas",
    "📜 Legal & Disclaimers"
])

# TAB 1: HOME (TOP 25)
with tab1:
    st.subheader(f"Top 25 ELO Rankings - {selected_year} Season")
    
    top25_data = []
    fbs_teams = [t for t in teams if t.division == 'FBS']
    sorted_fbs = sorted(fbs_teams, key=lambda t: final_elos.get(t.team_name, 0.0), reverse=True)[:25]
    
    for r, t in enumerate(sorted_fbs, start=1):
        name = t.team_name
        wins, losses = 0, 0
        for gdata in t.schedule:
            if gdata['outcome'] == 'W': wins += 1
            elif gdata['outcome'] == 'L': losses += 1

        pre_r = preseason_ranks.get(name, "N/A")
        top25_data.append({
            "Rank": r,
            "Team": name,
            "Conference": t.conference,
            "Record": f"{wins}-{losses}",
            "Current ELO": round(final_elos.get(name, 1500.0), 2),
            "Power ELO": round(power_elos.get(name, 1500.0), 2),
            "Preseason Rank": pre_r
        })

    df_top25 = pd.DataFrame(top25_data)
    st.dataframe(df_top25, width="stretch", hide_index=True)

# TAB 2: FULL POWER ELO RANKINGS
with tab2:
    st.subheader(f"Full Power ELO Rankings - All Teams ({selected_year})")
    
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        div_filter = st.selectbox("Filter Division", ["All", "FBS", "FCS"])
    with c2:
        all_confs = ["All"] + sorted(list(set(t.conference for t in teams)))
        conf_filter = st.selectbox("Filter Conference", all_confs)
    with c3:
        search_query = st.text_input("Search Team Name")

    full_rank_data = []
    for t in teams:
        if div_filter != "All" and t.division != div_filter:
            continue
        if conf_filter != "All" and t.conference != conf_filter:
            continue
        if search_query and search_query.lower() not in t.team_name.lower():
            continue

        name = t.team_name
        wins, losses = 0, 0
        for gdata in t.schedule:
            if gdata['outcome'] == 'W': wins += 1
            elif gdata['outcome'] == 'L': losses += 1

        full_rank_data.append({
            "Power Rank": 0, # Will set after sort
            "Team": name,
            "Division": t.division,
            "Conference": t.conference,
            "W-L": f"{wins}-{losses}",
            "Power ELO": round(power_elos.get(name, 1500.0), 2),
            "End ELO": round(final_elos.get(name, 1500.0), 2),
            "SoS Rating": round(sos_values.get(name, 1300.0), 2),
            "SoS Adj": round(sos_adjs.get(name, 0.0), 2),
            "Preseason Rank": preseason_ranks.get(name, "N/A")
        })

    df_full = pd.DataFrame(full_rank_data).sort_values(by="Power ELO", ascending=False)
    df_full["Power Rank"] = range(1, len(df_full) + 1)
    
    st.dataframe(df_full, width="stretch", hide_index=True)

# TAB 3: STRENGTH OF SCHEDULE
with tab3:
    st.subheader(f"Strength of Schedule Metrics & Opponent ELO Details ({selected_year})")
    
    sos_table_data = []
    for t in teams:
        if t.division != 'FBS': continue
        name = t.team_name
        
        row = {
            "Team": name,
            "SoS Rank": sos_ranks.get(name, 999),
            "SoS Rating": round(sos_values.get(name, 1300.0), 2),
            "Wk17 ELO": round(final_elos.get(name, 1500.0), 2),
            "SoS Adj": round(sos_adjs.get(name, 0.0), 2),
            "Power ELO": round(power_elos.get(name, 1500.0), 2)
        }

        # Add columns W1..W16 with opponent name and ELO
        opps = weekly_opps.get(name, [None]*16)
        opp_elos = weekly_opp_elos.get(name, [None]*16)

        for i in range(16):
            opp = opps[i] if i < len(opps) else None
            o_elo = opp_elos[i] if i < len(opp_elos) else None

            if opp and o_elo is not None:
                # Rank lookup for opponent
                opp_r = final_ranks.get(opp, "N/A")
                row[f"W{i+1}"] = f"{opp} (#{opp_r} | {o_elo:.1f})"
            elif opp:
                row[f"W{i+1}"] = f"{opp} (1300.0)"
            else:
                row[f"W{i+1}"] = "BYE"

        sos_table_data.append(row)

    df_sos = pd.DataFrame(sos_table_data).sort_values(by="Power ELO", ascending=False)
    cols = ["Team", "SoS Rank", "SoS Rating", "Wk17 ELO", "SoS Adj", "Power ELO"] + [f"W{i}" for i in range(1, 17)]
    
    st.caption("💡 Hover over or expand table cells under W1-W16 to inspect opponent names, game ELO ratings, and opponent rankings.")
    st.dataframe(df_sos[cols], width="stretch", hide_index=True)

# TAB 4: TEAM SCHEDULE DETAIL
with tab4:
    st.subheader(f"Team Schedule Detail Search ({selected_year})")
    
    team_names = sorted([t.team_name for t in teams if 'tbd' not in t.team_name.lower()])
    if team_names:
        sel_team_name = st.selectbox("Select Team", team_names)
        sel_team = next((t for t in teams if t.team_name == sel_team_name), None)
        
        if sel_team:
            pre_rank = preseason_ranks.get(sel_team_name, "N/A")
            pre_elo = season_data['preseason_elos'].get(sel_team_name, 1500.0 if sel_team.division == 'FBS' else 1100.0)

            st.info(f"**{sel_team_name}** | Conference: **{sel_team.conference}** | Division: **{sel_team.division}** | Preseason Rank: **#{pre_rank}** | Preseason ELO: **{pre_elo:.2f}** | End ELO: **{final_elos.get(sel_team_name, 1500.0):.2f}**")

            sched_rows = []
            for gdata in sel_team.schedule:
                delta_val = gdata.get('delta', 0.0)
                delta_str = f"{delta_val:+.3f}"
                new_elo_str = f"{gdata.get('new_elo', 0.0):.3f}"
                new_rank_str = str(gdata.get('new_rank', "-"))

                sched_rows.append({
                    "Date": gdata.get('date', ''),
                    "Week": gdata.get('display_week', gdata.get('week', '')),
                    "Opponent": gdata['opponent_name'],
                    "Outcome": gdata['outcome'],
                    "Score": gdata.get('score_str', f"{gdata.get('team_score', '')}-{gdata.get('opp_score', '')}"),
                    "Delta ELO": delta_str,
                    "New ELO": new_elo_str,
                    "New Rank": new_rank_str,
                    "Game Type": gdata.get('game_type', 'Regular')
                })

            if sched_rows:
                st.dataframe(pd.DataFrame(sched_rows), width="stretch", hide_index=True)
            else:
                st.write("No played games recorded for this team in this season.")

# TAB 5: POLL COMPARISON
with tab5:
    st.subheader(f"Side-by-Side Poll Comparison Top 25 ({selected_year})")
    
    poll_week = st.slider("Select Week", min_value=1, max_value=16, value=16)
    poll_comp_data = get_poll_comparison(selected_year, week=poll_week)

    st.caption("Note: If a poll (such as CFP Committee rankings prior to November) was unreleased for the selected week, '-' is displayed.")
    st.dataframe(pd.DataFrame(poll_comp_data), width="stretch", hide_index=True)

# TAB 6: PLAYOFF PICTURE
with tab6:
    st.subheader(f"12-Team College Football Playoff Picture ({selected_year})")
    
    ranking_source = st.selectbox("Select Playoff Ranking Metric Source", ["ELO", "AP", "Coaches", "CFP"])
    playoff_table, matchups = calculate_playoff_picture(selected_year, ranking_source)

    st.markdown("### 🥇 Official 12-Team Playoff Seeding")
    st.caption("Rules: 5 highest-ranked conference champions receive automatic bids. Top 4 conference champions receive Top 4 Seeds and 1st-Round BYEs.")
    st.dataframe(pd.DataFrame(playoff_table), width="stretch", hide_index=True)

    st.markdown("### 🏆 Playoff Bracket Matchups")
    st.dataframe(pd.DataFrame(matchups), width="stretch", hide_index=True)

# TAB 7: ABOUT & FORMULAS
with tab7:
    st.subheader("About the CFB Advanced ELO System & Mathematical Formula")
    
    st.markdown("""
    ### Purpose
    This system models NCAA College Football team strength using an advanced, non-linear ELO rating algorithm. It dynamically accounts for opponent strength, margin of victory, upset magnitude, schedule difficulty, and year-over-year rating carryover.

    ---

    ### Core ELO Formula & Calculations

    #### 1. Effective K-Factor ($K_{eff}$)
    Calculates week-by-week decay factor for ratings volatility:
    $$K_{eff} = \\max\\left(K_{min}, K_0 \\times 0.95^{\\text{Week} - 1}\\right)$$

    #### 2. Expected Outcome ($E_t$)
    Standard logistic expected win probability:
    $$E_t = \\frac{1}{1 + 10^{\\frac{\\text{ELO}_{opp} - \\text{ELO}_t}{C}}}$$
    *(where $C = 400$)*

    #### 3. Margin of Victory Factor ($m$)
    Logarithmic dampening factor for point differentials:
    $$m = \\ln\\left(1 + \\frac{|\\text{Score}_t - \\text{Score}_{opp}|}{C}\\right)$$

    #### 4. Upset Boost ($U$)
    Non-linear reward multiplier for lower-ranked teams defeating higher-ranked opponents:
    $$U = \\min\\left(1 + \\beta \\left(\\frac{|\\text{Rank}_t - \\text{Rank}_{opp}|}{N - 1}\\right)^\\rho, 1 + \\beta_{max}\\right)$$

    #### 5. Rating Delta ($\Delta ELO$)
    $$\Delta ELO = K_{eff} \\times (S_t - E_t) \\times (1 + \\gamma \\cdot m) \\times U$$

    #### 6. Strength of Schedule ($SoS$) & Power ELO
    $$SoS = \\frac{1}{n} \\sum_{i=1}^{n} \\text{ELO}_{opp, i}$$
    $$SoS_{Adj} = (SoS - 1500) \\times \\omega$$
    $$\\text{Power ELO} = \\text{ELO}_{end} + SoS_{Adj}$$
    """)

# TAB 8: LEGAL & DISCLAIMERS
with tab8:
    st.subheader("Legal Disclaimers & Usage Policy")
    st.markdown("""
    > [!NOTE]
    > **Experimental Non-Commercial Use Only**
    > 
    > This application and its underlying rating calculations are strictly for experimental, educational, and analytical purposes. 
    > 
    > - **Free to Use**: This tool is provided free of charge under an open experimental license.
    > - **Data Attribution**: Schedule, score, team, and poll ranking data are sourced via ESPN's public endpoints. All team names, logos, and trademarks belong to their respective university rights holders and NCAA.
    > - **No Commercial Warranty**: Provided "as is" without warranty of any kind.
    """)