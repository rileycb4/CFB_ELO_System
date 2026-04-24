import streamlit as st
import pandas as pd
from main import load_all_data
from formula import calculate_delta_elo as dt_elo

st.set_page_config(page_title="NCAA Advanced Team System", layout="wide")

# Cache the data loading so it doesn't reload the CSVs on every button click
@st.cache_data
def get_data():
    return load_all_data()

teams = get_data()

# --- Shared Calculation Logic (Ported from your gui.py) ---
@st.cache_data
def calculate_season_data(_teams):
    working_elos = {t.team_name: t.ELO for t in _teams}
    working_ranks = {t.team_name: t.ranking for t in _teams}
    weekly_deltas = {t.team_name: [0.0] * 16 for t in _teams}
    weekly_opp_names = {t.team_name: [None] * 16 for t in _teams}
    
    # NEW: A dedicated dictionary to hold our histories so Streamlit doesn't erase them
    all_histories = {t.team_name: {} for t in _teams}
    
    seen_games = set()
    games_by_week = {}
    
    for team in _teams:
        for week, data in team.schedule.items():
            opp_name = data["opponent_name"]
            game_id = tuple(sorted((team.team_name, opp_name)) + [week])
            if game_id not in seen_games:
                games_by_week.setdefault(week, []).append({
                    'week': week, 't1': team.team_name, 't2': opp_name,
                    's1': data["team"]["score"], 's2': data["opponent"]["score"]
                })
                seen_games.add(game_id)
                
    for week in sorted(games_by_week.keys()):
        sorted_by_elo = sorted(working_elos.items(), key=lambda item: item[1], reverse=True)
        for current_rank, (team_name, _) in enumerate(sorted_by_elo, start=1):
            working_ranks[team_name] = current_rank
        
        current_week_deltas = {}
        for g in games_by_week[week]:
            t1_name, t2_name = g['t1'], g['t2']
            t1_in = t1_name in working_elos
            t2_in = t2_name in working_elos

            e1 = working_elos[t1_name] if t1_in else 1300.0
            e2 = working_elos[t2_name] if t2_in else 1300.0
            r1 = working_ranks[t1_name] if t1_in else 200
            r2 = working_ranks[t2_name] if t2_in else 200
            
            if t1_in and 0 < g['week'] <= 16: weekly_opp_names[t1_name][g['week']-1] = t2_name
            if t2_in and 0 < g['week'] <= 16: weekly_opp_names[t2_name][g['week']-1] = t1_name

            d1 = dt_elo(e1, e2, r1, r2, "W" if g['s1'] > g['s2'] else "L", g['s1'], g['s2'], g['week'])
            d2 = dt_elo(e2, e1, r2, r1, "W" if g['s2'] > g['s1'] else "L", g['s2'], g['s1'], g['week'])
            
            if t1_in:
                working_elos[t1_name] += d1
                current_week_deltas[t1_name] = current_week_deltas.get(t1_name, 0.0) + d1
                if 0 < g['week'] <= 16: weekly_deltas[t1_name][g['week']-1] += d1
            if t2_in:
                working_elos[t2_name] += d2
                current_week_deltas[t2_name] = current_week_deltas.get(t2_name, 0.0) + d2
                if 0 < g['week'] <= 16: weekly_deltas[t2_name][g['week']-1] += d2

        sorted_by_elo = sorted(working_elos.items(), key=lambda item: item[1], reverse=True)
        end_ranks = {name: rank for rank, (name, _) in enumerate(sorted_by_elo, start=1)}

        # CHANGED: Save to our dictionary instead of the team object directly
        for t_name, total_delta in current_week_deltas.items():
            all_histories[t_name][week] = {'delta': total_delta, 'new_elo': working_elos[t_name], 'new_rank': end_ranks[t_name]}

    sorted_by_elo = sorted(working_elos.items(), key=lambda item: item[1], reverse=True)
    for final_rank, (team_name, _) in enumerate(sorted_by_elo, start=1):
        working_ranks[team_name] = final_rank
        
    # CHANGED: Return our new all_histories dictionary
    return working_elos, working_ranks, weekly_deltas, weekly_opp_names, all_histories

# Run Calculations (Now unpacking all_histories)
final_elos, final_ranks, weekly_deltas, weekly_opp_names, all_histories = calculate_season_data(teams)

st.title("NCAA Advanced Team System")

# Create Web Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Team Viewer", "Standings", "Rankings", "Strength of Schedule", "Schedule Detail Search"])

with tab1:
    st.subheader("Team Viewer")
    search = st.text_input("Search Team or Conference:")
    viewer_data = [{"Rank": t.ranking or "N/A", "Team": t.team_name, "Conference": t.conference, "Initial ELO": round(t.ELO, 3)} for t in teams]
    df_viewer = pd.DataFrame(viewer_data)
    if search:
        df_viewer = df_viewer[df_viewer['Team'].str.contains(search, case=False) | df_viewer['Conference'].str.contains(search, case=False)]
    st.dataframe(df_viewer, width='stretch', hide_index=True)

with tab2:
    st.subheader("Standings")
    confs = sorted(list(set(t.conference for t in teams)))
    selected_conf = st.selectbox("Select Conference", confs)
    
    standings_data = []
    for t in [team for team in teams if team.conference == selected_conf]:
        w, l = 0, 0
        for week, data in t.schedule.items():
            if not data.get("is_champ", False):
                if data["outcome"] == 'W': w += 1
                elif data["outcome"] == 'L': l += 1
        pct = w / (w + l) if (w + l) > 0 else 0
        standings_data.append({"Team": t.team_name, "W": w, "L": l, "Pct": round(pct, 3)})
    
    st.dataframe(pd.DataFrame(standings_data).sort_values(by=["Pct", "W"], ascending=[False, False]), width='stretch', hide_index=True)

with tab3:
    st.subheader("Rankings")
    rank_data = []
    for t in teams:
        row = {"Team": t.team_name, "Rank": final_ranks[t.team_name], "ELO": round(final_elos[t.team_name], 3)}
        for i in range(16):
            val = weekly_deltas[t.team_name][i]
            row[f"W{i+1}"] = f"{val:+.1f}" if val != 0 else ""
        rank_data.append(row)
    
    st.dataframe(pd.DataFrame(rank_data).sort_values(by="ELO", ascending=False), width='stretch', hide_index=True)

with tab4:
    st.subheader("Strength of Schedule")
    sos_data = []
    for t in teams:
        name = t.team_name
        opp_final_elos = [final_elos.get(opp_name, 1300.0) if opp_name else None for opp_name in weekly_opp_names[name]]
        played_elos = [elo for elo in opp_final_elos if elo is not None]
        
        sos = sum(played_elos) / len(played_elos) if played_elos else 1300.0
        sos_adj = (sos - 1500) * 0.5
        power_elo = final_elos[name] + sos_adj
        
        row = {"Team": name, "SoS": round(sos, 2), "Wk17 ELO": round(final_elos[name], 2), "SoS Adj": round(sos_adj, 2), "Power ELO": round(power_elo, 2)}
        
        # FIXED: Ensure everything in the W1-W16 columns is a string
        for i, elo in enumerate(opp_final_elos):
            row[f"W{i+1}"] = f"{elo:.1f}" if elo is not None else ""
            
        sos_data.append(row)
        
    df_sos = pd.DataFrame(sos_data)
    df_sos['SoS Rank'] = df_sos['SoS'].rank(ascending=False).astype(int)
    # Reorder columns to put SoS Rank next to SoS
    cols = ['Team', 'SoS', 'SoS Rank', 'Wk17 ELO', 'SoS Adj', 'Power ELO'] + [f'W{i}' for i in range(1, 17)]
    st.dataframe(df_sos[cols].sort_values(by="Power ELO", ascending=False), width='stretch', hide_index=True)

with tab5:
    st.subheader("Team Schedule Detail")
    
    team_list = sorted([t.team_name for t in teams])
    selected_team = st.selectbox("Select a Team to view their historical schedule:", team_list)
    
    team = next(t for t in teams if t.team_name == selected_team)
    
    st.write(f"**Preseason Ranking/ELO:** {team.ranking or 200} | {team.ELO:.3f}")
    
    sched_data = []
    
    # NEW: Fetch the actual history from our returned dictionary
    team_history = all_histories.get(selected_team, {})
    
    for week in sorted(team.schedule.keys()):
        data = team.schedule[week]
        history = team_history.get(week, {})
        sched_data.append({
            "Week": week,
            "Opponent": data['opponent_name'],
            "Outcome": data['outcome'],
            "Score": f"{data['team']['score']}-{data['opponent']['score']}",
            
            # Formatted as strings to appease PyArrow!
            "Delta ELO": f"{history.get('delta', 0.0):+.3f}" if history else "-",
            "New ELO": f"{history.get('new_elo', 0.0):.3f}" if history else "-",
            "New Rank": str(history.get('new_rank', "-"))
        })
        
    st.dataframe(pd.DataFrame(sched_data), width='stretch', hide_index=True)