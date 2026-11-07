import sys
import statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from archive.src.database import get_connection, init_db, resolve_conference_name, clean_database_records
from cfb_integrated_app.src.data_fetcher import fetch_staged_data
from archive.src.formula import calculate_delta_elo as dt_elo, EloParameters, DEFAULT_PARAMS

def rank_to_initial_elo(rank, total_teams, division="FBS", base_elo=None, target_span=10.0):
    """
    Converts 1..N team rank to initial ELO rating using Gaussian z-score distribution.
    Matches formula: p = (N - r + 0.5)/N, z = Phi^-1(p), Elo = R0 + z * sigma.
    FBS teams start in range [1490.0, 1510.0] (centered at 1500.0).
    FCS teams start in range [1090.0, 1110.0] (centered at 1100.0).
    """
    if base_elo is None:
        div_str = str(division).strip().upper() if division else "FBS"
        if div_str == "FCS":
            base_elo = 1100.0
        elif div_str == "FBS":
            base_elo = 1500.0
        else:
            base_elo = 800.0

    N = int(total_teams)
    r = int(rank)
    if N <= 1:
        return base_elo

    p = (N - r + 0.5) / float(N)
    p = max(0.0001, min(0.9999, p))
    z = statistics.NormalDist(mu=0, sigma=1).inv_cdf(p)

    max_p = (N - 0.5) / float(N)
    max_z = statistics.NormalDist(mu=0, sigma=1).inv_cdf(max_p)
    sigma = target_span / max_z if max_z > 0 else 3.7313

    return base_elo + z * sigma

class Team:
    def __init__(self, espn_id, team_name, conference, division="FBS", ranking=None, ELO=None, logo_url=None):
        self.espn_id = espn_id
        self.team_name = team_name
        self.conference = resolve_conference_name(conference)
        self.division = division
        self.ranking = ranking if ranking is not None else 137
        self.ELO = ELO if ELO is not None else (1500.0 if division == 'FBS' else 1100.0)
        self.logo_url = logo_url or ""
        self.schedule = [] # List of game records in chronological order
        self.weekly_history = []

    def add_game(self, game_dict):
        self.schedule.append(game_dict)

def ensure_database_populated():
    init_db()
    clean_database_records()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM games")
    row = cursor.fetchone()
    cnt = row['cnt'] if row else 0
    conn.close()

    if cnt == 0:
        print("Database empty. Performing initial fast staged pull...")
        fetch_staged_data(start_year=2021, end_year=2026)

def get_available_years():
    ensure_database_populated()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT year FROM games WHERE year <= 2026 ORDER BY year ASC")
    rows = cursor.fetchall()
    conn.close()
    years = [r['year'] for r in rows if r['year'] <= 2026]
    if not years:
        years = [2021, 2022, 2023, 2024, 2025, 2026]
    return sorted(list(set(years)))

def load_teams_and_games_for_year(year):
    ensure_database_populated()
    conn = get_connection()
    cursor = conn.cursor()

    # Query only FBS and FCS teams for rankings (filter out TBD or dummy teams)
    cursor.execute("""
    SELECT * FROM teams
    WHERE division IN ('FBS', 'FCS')
    """)
    status_rows = cursor.fetchall()

    teams_dict = {}
    for r in status_rows:
        espn_id = r['espn_id']
        t_name = r['team_name']
        if not t_name or 'tbd' in t_name.lower():
            continue
        teams_dict[espn_id] = Team(
            espn_id=espn_id,
            team_name=t_name,
            conference=resolve_conference_name(r['conference']),
            division=r['division'] or "FBS",
            logo_url=r['logo_url']
        )

    # Query games for year ordered by exact game date and season type
    cursor.execute("""
    SELECT game_id, season_type, week, game_date, home_team_id, away_team_id, home_score, away_score, status, is_champ
    FROM games
    WHERE year = ? AND status = 'STATUS_FINAL' AND home_score IS NOT NULL AND away_score IS NOT NULL
    ORDER BY game_date ASC, season_type ASC, week ASC, game_id ASC
    """, (year,))
    game_rows = cursor.fetchall()
    conn.close()

    return teams_dict, game_rows

def calculate_multi_year_elo(end_year, elo_params=None):
    """
    Computes ELO sequentially from start year (2021) to end_year.
    Preseason ELOs for EVERY season are scaled using rank_to_initial_elo:
    - FBS starts in range [1490.0, 1510.0]
    - FCS starts in range [1090.0, 1110.0]
    End-of-season ELOs expand naturally through game updates to [1250, 1750].
    For future/subsequent years, initial rankings are calculated off prior season Power ELOs.
    """
    if elo_params is None:
        elo_params = DEFAULT_PARAMS

    ensure_database_populated()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(year) as min_y FROM games")
    row = cursor.fetchone()
    min_y = row['min_y'] if row and row['min_y'] else 2021
    conn.close()

    start_year = min_y
    prior_season_power_ranks = {}
    season_results = {}

    end_year = min(end_year, 2026)

    for yr in range(start_year, end_year + 1):
        teams_dict, game_rows = load_teams_and_games_for_year(yr)
        
        # Separate teams by division for initial scale calculation
        fbs_teams_list = [t for t in teams_dict.values() if t.division == 'FBS']
        fcs_teams_list = [t for t in teams_dict.values() if t.division == 'FCS']

        # Determine initial ranks based on prior season Power ELO ranks or default order
        if prior_season_power_ranks:
            fbs_teams_list.sort(key=lambda t: prior_season_power_ranks.get(t.espn_id, 999))
            fcs_teams_list.sort(key=lambda t: prior_season_power_ranks.get(t.espn_id, 999))
        else:
            fbs_teams_list.sort(key=lambda t: t.team_name)
            fcs_teams_list.sort(key=lambda t: t.team_name)

        # Assign initial ELO ratings using Gaussian rank-to-ELO transformation formula
        n_fbs = len(fbs_teams_list)
        for r, team in enumerate(fbs_teams_list, start=1):
            team.ELO = rank_to_initial_elo(r, n_fbs, division=team.division, target_span=10.0)
            team.ranking = r

        n_fcs = len(fcs_teams_list)
        for r, team in enumerate(fcs_teams_list, start=1):
            team.ELO = rank_to_initial_elo(r, n_fcs, division=team.division, target_span=10.0)
            team.ranking = r

        # Snapshot Preseason ELOs & Preseason Ranks
        sorted_pre = sorted(teams_dict.values(), key=lambda t: t.ELO, reverse=True)
        preseason_ranks = {}
        preseason_elos = {}
        for rank, team in enumerate(sorted_pre, start=1):
            #print(f"Preseason Rank: {rank}, Team: {team.team_name}, Division: {team.division}, ELO: {team.ELO}")
            preseason_ranks[team.team_name] = rank
            preseason_elos[team.team_name] = team.ELO

        # Chronological Game Processing
        working_elos = {t.espn_id: t.ELO for t in teams_dict.values()}
        working_ranks = {t.espn_id: t.ranking for t in teams_dict.values()}
        
        # Schedules & Game History
        weekly_deltas = {t.team_name: [0.0] * 16 for t in teams_dict.values()}
        weekly_opp_names = {t.team_name: [None] * 16 for t in teams_dict.values()}
        weekly_opp_elos = {t.team_name: [None] * 16 for t in teams_dict.values()}
        all_histories = {t.team_name: [] for t in teams_dict.values()}

        def update_current_ranks():
            sorted_curr = sorted(working_elos.items(), key=lambda x: x[1], reverse=True)
            for curr_r, (t_id, _) in enumerate(sorted_curr, start=1):
                working_ranks[t_id] = curr_r

        update_current_ranks()

        # Process games in exact date order
        for g_idx, g in enumerate(game_rows, start=1):
            stype = g['season_type']
            raw_wk = g['week']
            gdate = g['game_date'][:10] if g['game_date'] else ""
            h_id = g['home_team_id']
            a_id = g['away_team_id']
            hs = g['home_score']
            ascore = g['away_score']
            is_champ = bool(g['is_champ'])

            h_team = teams_dict.get(h_id)
            a_team = teams_dict.get(a_id)

            h_name = h_team.team_name if h_team else None
            a_name = a_team.team_name if a_team else None

            if not h_name or not a_name:
                continue

            e1 = working_elos.get(h_id, 1100.0)
            e2 = working_elos.get(a_id, 1100.0)
            r1 = working_ranks.get(h_id, 200)
            r2 = working_ranks.get(a_id, 200)

            g_type = "Regular"
            if is_champ:
                g_type = "Championship"
            elif stype == 3:
                g_type = "Postseason / Playoff"

            grid_wk = raw_wk if stype == 2 else min(16, 14 + raw_wk)

            if 0 < grid_wk <= 16:
                if h_name in weekly_opp_names and weekly_opp_names[h_name][grid_wk - 1] is None:
                    weekly_opp_names[h_name][grid_wk - 1] = a_name
                    weekly_opp_elos[h_name][grid_wk - 1] = e2

                if a_name in weekly_opp_names and weekly_opp_names[a_name][grid_wk - 1] is None:
                    weekly_opp_names[a_name][grid_wk - 1] = h_name
                    weekly_opp_elos[a_name][grid_wk - 1] = e1

            # Delta ELO Math
            d1 = dt_elo(e1, e2, r1, r2, "W" if hs > ascore else "L", hs, ascore, grid_wk, elo_params)
            d2 = dt_elo(e2, e1, r2, r1, "W" if ascore > hs else "L", ascore, hs, grid_wk, elo_params)

            if h_id in working_elos:
                working_elos[h_id] += d1
                if 0 < grid_wk <= 16 and h_name in weekly_deltas:
                    weekly_deltas[h_name][grid_wk - 1] += d1
            if a_id in working_elos:
                working_elos[a_id] += d2
                if 0 < grid_wk <= 16 and a_name in weekly_deltas:
                    weekly_deltas[a_name][grid_wk - 1] += d2

            update_current_ranks()

            # Record schedule game entries
            if h_team:
                out_h = "W" if hs > ascore else "L"
                h_game_info = {
                    "game_id": g['game_id'],
                    "date": gdate,
                    "week": raw_wk,
                    "display_week": grid_wk,
                    "opponent_name": a_name,
                    "outcome": out_h,
                    "team_score": hs,
                    "opp_score": ascore,
                    "score_str": f"{hs}-{ascore}",
                    "delta": d1,
                    "new_elo": working_elos[h_id],
                    "new_rank": working_ranks[h_id],
                    "is_champ": is_champ,
                    "game_type": g_type
                }
                h_team.add_game(h_game_info)
                all_histories[h_name].append(h_game_info)

            if a_team:
                out_a = "W" if ascore > hs else "L"
                a_game_info = {
                    "game_id": g['game_id'],
                    "date": gdate,
                    "week": raw_wk,
                    "display_week": grid_wk,
                    "opponent_name": h_name,
                    "outcome": out_a,
                    "team_score": ascore,
                    "opp_score": hs,
                    "score_str": f"{ascore}-{hs}",
                    "delta": d2,
                    "new_elo": working_elos[a_id],
                    "new_rank": working_ranks[a_id],
                    "is_champ": is_champ,
                    "game_type": g_type
                }
                a_team.add_game(a_game_info)
                all_histories[a_name].append(a_game_info)

        # Calculate Final ELOs, Ranks, SoS, and Power ELOs
        sorted_by_elo = sorted(working_elos.items(), key=lambda x: x[1], reverse=True)
        final_ranks = {}
        final_elos = {}
        for r, (t_id, elo_val) in enumerate(sorted_by_elo, start=1):
            team_obj = teams_dict[t_id]
            final_ranks[team_obj.team_name] = r
            final_elos[team_obj.team_name] = elo_val
            team_obj.ranking = r
            team_obj.ELO = elo_val

        # Strength of Schedule Calculation
        sos_values = {}
        sos_adjs = {}
        power_elos = {}
        for espn_id, team in teams_dict.items():
            name = team.team_name
            opp_names = [g['opponent_name'] for g in team.schedule if g.get('opponent_name')]
            played_elos = []
            for opp in opp_names:
                if opp and opp in final_elos:
                    played_elos.append(final_elos[opp])
                elif opp:
                    played_elos.append(1100.0)

            sos = sum(played_elos) / len(played_elos) if played_elos else 1100.0
            sos_adj = (sos - 1500.0) * elo_params.OMEGA
            power_elo = final_elos[name] + sos_adj

            sos_values[name] = sos
            sos_adjs[name] = sos_adj
            power_elos[name] = power_elo

        # Store Power ELO ranks for carryover to next season
        sorted_power = sorted(power_elos.items(), key=lambda x: x[1], reverse=True)
        prior_season_power_ranks = {
            next(t.espn_id for t in teams_dict.values() if t.team_name == name): r
            for r, (name, _) in enumerate(sorted_power, start=1)
        }

        # SoS Rankings
        sorted_sos = sorted(sos_values.items(), key=lambda x: x[1], reverse=True)
        sos_ranks = {name: r for r, (name, _) in enumerate(sorted_sos, start=1)}

        season_results[yr] = {
            'teams': [t for t in teams_dict.values() if t.division in ('FBS', 'FCS')],
            'teams_by_name': {t.team_name: t for t in teams_dict.values() if t.division in ('FBS', 'FCS')},
            'final_elos': final_elos,
            'final_ranks': final_ranks,
            'power_elos': power_elos,
            'sos_ranks': sos_ranks,
            'sos_values': sos_values,
            'sos_adjs': sos_adjs,
            'weekly_deltas': weekly_deltas,
            'weekly_opponents': weekly_opp_names,
            'weekly_opp_elos': weekly_opp_elos,
            'preseason_ranks': preseason_ranks,
            'preseason_elos': preseason_elos,
            'all_histories': all_histories
        }

    return season_results[end_year]

def get_poll_comparison(year, week=1):
    """
    Returns side-by-side poll rankings (AP, Coaches, CFP, ELO) for FBS & FCS.
    Missing polls default to '-' placeholders.
    """
    year = min(year, 2026)
    season_data = calculate_multi_year_elo(year)
    elo_ranks = season_data['final_ranks']

    conn = get_connection()
    cursor = conn.cursor()
    
    # Query polls for FBS & FCS only
    cursor.execute("""
    SELECT p.poll_type, p.rank, s.team_name
    FROM polls p
    JOIN team_season_status s ON p.espn_id = s.espn_id AND p.year = s.year
    WHERE p.year = ? AND p.week = ? AND s.division IN ('FBS', 'FCS') AND LOWER(s.team_name) NOT LIKE '%tbd%'
    ORDER BY p.rank ASC
    """, (year, week))
    poll_rows = cursor.fetchall()
    conn.close()

    polls_dict = {'AP': {}, 'Coaches': {}, 'CFP': {}}
    for r in poll_rows:
        ptype = r['poll_type']
        if ptype in polls_dict:
            polls_dict[ptype][r['rank']] = r['team_name']

    # Get ELO Top 25
    sorted_elo = sorted(elo_ranks.items(), key=lambda x: x[1])[:25]
    elo_top25 = {rank: name for rank, (name, _) in enumerate(sorted_elo, start=1)}

    comparison_data = []
    for rank in range(1, 26):
        ap_team = polls_dict['AP'].get(rank, "-")
        coaches_team = polls_dict['Coaches'].get(rank, "-")
        cfp_team = polls_dict['CFP'].get(rank, "-")
        elo_team = elo_top25.get(rank, "-")

        comparison_data.append({
            "Rank": rank,
            "AP Poll": ap_team,
            "Coaches Poll": coaches_team,
            "CFP Committee": cfp_team,
            "ELO Top 25": elo_team
        })

    return comparison_data

def calculate_playoff_picture(year, ranking_source="ELO"):
    """
    Calculates 12-Team College Football Playoff Picture (FBS only).
    """
    year = min(year, 2026)
    season_data = calculate_multi_year_elo(year)
    teams_by_name = season_data['teams_by_name']
    
    # Determine team rankings source
    rankings_map = {}
    if ranking_source == "ELO":
        rankings_map = season_data['final_ranks']
    elif ranking_source in ["AP", "Coaches", "CFP"]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.rank, s.team_name
        FROM polls p
        JOIN team_season_status s ON p.espn_id = s.espn_id AND p.year = s.year
        WHERE p.year = ? AND p.poll_type = ? AND p.week = (SELECT MAX(week) FROM polls WHERE year=? AND poll_type=?)
          AND s.division = 'FBS' AND LOWER(s.team_name) NOT LIKE '%tbd%'
        """, (year, ranking_source, year, ranking_source))
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            rankings_map[r['team_name']] = r['rank']
        
        # Fill missing with ELO rank
        for tname, elo_r in season_data['final_ranks'].items():
            if tname not in rankings_map:
                rankings_map[tname] = elo_r + 50

    # Find conference champions among FBS teams
    conf_teams = {}
    for tname, team in teams_by_name.items():
        if team.division == 'FBS' and 'tbd' not in tname.lower():
            conf_teams.setdefault(team.conference, []).append(team)

    conf_champs = []
    for conf, t_list in conf_teams.items():
        if conf in ["IND", "Independent", "None", "Conf_None"]:
            continue
        # Highest ranked team in conference is designated champ
        sorted_conf = sorted(t_list, key=lambda t: rankings_map.get(t.team_name, 999))
        if sorted_conf:
            conf_champs.append(sorted_conf[0])

    # Rank conference champions
    sorted_champs = sorted(conf_champs, key=lambda t: rankings_map.get(t.team_name, 999))
    top_5_champs = sorted_champs[:5]

    # Top 4 champs get seeds 1-4
    seeds = {}
    byes = []
    for seed, champ in enumerate(top_5_champs[:4], start=1):
        seeds[seed] = champ.team_name
        byes.append(champ.team_name)

    # Remaining candidates for seeds 5-12 (5th champ + remaining top teams)
    remaining_teams = [t for t in teams_by_name.values() if t.division == 'FBS' and t.team_name not in byes and 'tbd' not in t.team_name.lower()]
    sorted_remaining = sorted(remaining_teams, key=lambda t: rankings_map.get(t.team_name, 999))

    for seed, team in enumerate(sorted_remaining[:8], start=5):
        seeds[seed] = team.team_name

    playoff_table = []
    for seed in range(1, 13):
        t_name = seeds.get(seed, f"Seed_{seed}")
        team_obj = teams_by_name.get(t_name)
        conf = team_obj.conference if team_obj else "N/A"
        rank_val = rankings_map.get(t_name, "N/A")
        status = "First-Round BYE (Host Quarterfinal)" if seed <= 4 else ("Home Game (Seeds 5-8)" if seed <= 8 else "Road Game (Seeds 9-12)")
        
        playoff_table.append({
            "Seed": seed,
            "Team": t_name,
            "Conference": conf,
            "Poll Rank": str(rank_val),
            "Playoff Status": status
        })

    matchups = [
        {"Matchup": "First Round", "Game": f"#8 {seeds.get(8, '')} vs #9 {seeds.get(9, '')}", "Location": f"At #8 {seeds.get(8, '')}"},
        {"Matchup": "First Round", "Game": f"#5 {seeds.get(5, '')} vs #12 {seeds.get(12, '')}", "Location": f"At #5 {seeds.get(5, '')}"},
        {"Matchup": "First Round", "Game": f"#6 {seeds.get(6, '')} vs #11 {seeds.get(11, '')}", "Location": f"At #6 {seeds.get(6, '')}"},
        {"Matchup": "First Round", "Game": f"#7 {seeds.get(7, '')} vs #10 {seeds.get(10, '')}", "Location": f"At #7 {seeds.get(7, '')}"},
        {"Matchup": "Quarterfinal", "Game": f"#1 {seeds.get(1, '')} vs Winner (#8/#9)", "Location": "Neutral Bowl Site"},
        {"Matchup": "Quarterfinal", "Game": f"#4 {seeds.get(4, '')} vs Winner (#5/#12)", "Location": "Neutral Bowl Site"},
        {"Matchup": "Quarterfinal", "Game": f"#3 {seeds.get(3, '')} vs Winner (#6/#11)", "Location": "Neutral Bowl Site"},
        {"Matchup": "Quarterfinal", "Game": f"#2 {seeds.get(2, '')} vs Winner (#7/#10)", "Location": "Neutral Bowl Site"}
    ]

    return playoff_table, matchups

if __name__ == "__main__":
    from archive.src.gui import start_gui
    print("Launching NCAA CFB System Local Desktop GUI...")
    start_gui()