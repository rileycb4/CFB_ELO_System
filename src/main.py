import xml.etree.ElementTree as ET
import csv
from formula import calculate_delta_elo as dt_elo

class Team:
    def __init__(self, team_name, conference, ranking=None, ELO=None):
        self.team_name = team_name
        self.conference = conference
        self.ranking = ranking if ranking is not None else 137
        self.ELO = ELO if ELO is not None else 1500.0
        # MUST be curly braces for a dictionary
        self.schedule = {} 
        self.weekly_history = {} 

    def add_week(self, week, score_t, score_opp, outcome, rank_t, rating_t, rank_opp, rating_opp, opp_name, is_champ=False):
        self.schedule[week] = {
            "opponent_name": opp_name,
            "team": {"score": score_t, "rank": rank_t, "rating": rating_t},
            "opponent": {"score": score_opp, "rank": rank_opp, "rating": rating_opp},
            "outcome": outcome,
            "is_champ": is_champ # Re-added so the GUI can filter championship games
        }

def load_teams_from_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    teams = []
    for conference in root.findall('Conference'): # Matches your XML tag case
        conf_name = conference.get('name')
        for team in conference.findall('Team'):
            team_name = team.text
            teams.append(Team(team_name, conf_name))
            #print(f"Loaded team: {team_name} from conference: {conf_name}")
    return teams

def update_teams_with_rankings(teams, csv_file_path):
    try:
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')
            next(reader) 
            for row in reader:
                ELO = float(row[0].strip())
                ranking = int(row[1].strip())
                team_name = row[2].strip()
                for team in teams:
                    if team.team_name.strip() == team_name:
                        team.ELO = ELO
                        team.ranking = ranking
                        break
    except FileNotFoundError:
        print(f"Warning: {csv_file_path} not found.")

def load_results(teams, csv_file_path):
    is_champ_period = False
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader) 
        for row in reader:
            if any('Conference Championships' in str(cell) for cell in row):
                is_champ_period = True
                continue

            if not row or len(row) < 7: continue  # Skip malformed rows and ensure we have enough columns

            week = int(row[0])
            t1_n, t1_s, t2_n, t2_s = row[2].strip(), int(row[3]), row[5].strip(), int(row[6])

            # Find the teams (returns None if it's an FCS school)
            team1 = next((t for t in teams if t.team_name == t1_n), None)
            team2 = next((t for t in teams if t.team_name == t2_n), None)

            # Establish safe defaults for missing opponents (FCS schools)
            t1_rank = team1.ranking if team1 else 200
            t1_elo = team1.ELO if team1 else 1300.0
            
            t2_rank = team2.ranking if team2 else 200
            t2_elo = team2.ELO if team2 else 1300.0

            #print(f"Processing Week {week}: {t1_n} vs {t2_n} | Scores: {t1_s}-{t2_s} | Ranks: {t1_rank}-{t2_rank} | ELOs: {t1_elo:.1f}-{t2_elo:.1f}")

            # Add to Team 1's schedule if Team 1 is an FBS team
            if team1:
                out1 = "W" if t1_s > t2_s else "L"
                team1.add_week(week, t1_s, t2_s, out1, t1_rank, t1_elo, t2_rank, t2_elo, t2_n, is_champ_period)
            
            # Add to Team 2's schedule if Team 2 is an FBS team
            if team2:
                out2 = "W" if t2_s > t1_s else "L"
                team2.add_week(week, t2_s, t1_s, out2, t2_rank, t2_elo, t1_rank, t1_elo, t1_n, is_champ_period)

def generate_weekly_breakdown_csv(teams, output_filename="weekly_breakdown.csv"):
    """
    Simulates the season week-by-week and exports a detailed historical breakdown 
    to a CSV file.
    """
    # 1. Initialize Starting Values
    current_elos = {t.team_name: t.ELO for t in teams}
    current_ranks = {t.team_name: t.ranking for t in teams}
    
    # 2. Extract and Group all Games by Week
    max_week = 0
    games_by_week = {}
    seen_games = set()
    
    for team in teams:
        for week, data in team.schedule.items():
            max_week = max(max_week, week)
            opp_name = data["opponent_name"]
            game_id = tuple(sorted((team.team_name, opp_name)) + [week])
            
            if game_id not in seen_games:
                games_by_week.setdefault(week, []).append({
                    't1': team.team_name, 't2': opp_name,
                    's1': data["team"]["score"], 's2': data["opponent"]["score"]
                })
                seen_games.add(game_id)
                
    # 3. Setup the CSV Writer
    with open(output_filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write the Header
        writer.writerow(["Week", "Team", "Opponent", "Score", "Old Rank", "New Rank", "Old ELO", "New ELO"])
        
        # 4. Process Every Week
        for week in range(1, max_week + 1):
            week_games = games_by_week.get(week, [])
            
            # Snapshot the "Old" state before games are played
            old_elos = current_elos.copy()
            old_ranks = current_ranks.copy()
            
            played_this_week = {} # Tracks who played whom
            
            # --- CALCULATE DELTAS ---
            for g in week_games:
                t1, t2 = g['t1'], g['t2']
                s1, s2 = g['s1'], g['s2']
                
                t1_in = t1 in current_elos
                t2_in = t2 in current_elos
                
                # Fetch dynamically (Default to 1300/200 for FCS)
                e1 = current_elos[t1] if t1_in else 1300.0
                e2 = current_elos[t2] if t2_in else 1300.0
                r1 = current_ranks[t1] if t1_in else 200
                r2 = current_ranks[t2] if t2_in else 200
                
                d1 = dt_elo(e1, e2, r1, r2, "W" if s1 > s2 else "L", s1, s2, week)
                d2 = dt_elo(e2, e1, r2, r1, "W" if s2 > s1 else "L", s2, s1, week)
                
                if t1_in: current_elos[t1] += d1
                if t2_in: current_elos[t2] += d2
                
                # Record match details for the breakdown
                played_this_week[t1] = {"opp": t2, "score": f"{s1}-{s2}"}
                played_this_week[t2] = {"opp": t1, "score": f"{s2}-{s1}"}
                
            # --- DETERMINE "NEW" RANKS ---
            sorted_new = sorted(current_elos.items(), key=lambda x: x[1], reverse=True)
            current_ranks = {name: rank for rank, (name, _) in enumerate(sorted_new, start=1)}
            
            # --- WRITE ROWS TO CSV (Alphabetical Order) ---
            for team in sorted(teams, key=lambda t: t.team_name):
                t_name = team.team_name
                
                # Check if they had a game or a BYE
                if t_name in played_this_week:
                    opp = played_this_week[t_name]["opp"]
                    score = played_this_week[t_name]["score"]
                else:
                    opp = "BYE"
                    score = "N/A"
                    
                # [Week, Team, Opp, Score, Old Rank, New Rank, Old ELO, New ELO]
                writer.writerow([
                    week,
                    t_name,
                    opp,
                    score,
                    old_ranks[t_name],
                    current_ranks[t_name],
                    f"{old_elos[t_name]:.3f}",
                    f"{current_elos[t_name]:.3f}"
                ])
                
    print(f"Success: Weekly breakdown generated at '{output_filename}'")

def load_all_data():
    teams = load_teams_from_xml('resources/FBS_list.xml')
    update_teams_with_rankings(teams, 'resources/preseason_rankings/rankings_2025.csv')
    load_results(teams, 'resources/results/results_2025_cleaned.csv')
    return teams

if __name__ == "__main__":
    teams = load_all_data()
    print("Data loaded successfully.")