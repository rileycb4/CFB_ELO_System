import xml.etree.ElementTree as ET
import csv
from viewing_gui import start_gui

class Game:
    def __init__(self, week_num, opponent, outcome, score_us, score_them):
        self.week_num = week_num
        self.opponent = opponent
        self.outcome = outcome  # 'W', 'L', or 'T'
        self.score_us = score_us
        self.score_them = score_them

class Team:
    def __init__(self, team_name, conference, ranking=None, ELO=None):
        self.team_name = team_name
        self.conference = conference
        self.ranking = ranking if ranking is not None else 134 # Default to bottom rank
        self.ELO = ELO if ELO is not None else 1500.0
        self.games = []  # Array of Game objects

    def get_game_by_week(self, week_num):
        return next((g for g in self.games if g.week_num == week_num), None)

def load_teams_from_xml(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        teams = []
        for conference in root.findall('conference'):
            conf_name = conference.get('name')
            for team in conference.findall('team'):
                teams.append(Team(team.text.strip(), conf_name))
        return teams
    except Exception as e:
        print(f"Error loading XML: {e}")
        return []

def update_teams_with_rankings(teams, csv_file_path):
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            # Detects if file is Tab or Comma delimited
            content = csvfile.read(1024)
            csvfile.seek(0)
            dialect = csv.Sniffer().sniff(content) if (',' in content or '\t' in content) else 'excel-tab'
            
            reader = csv.reader(csvfile, dialect=dialect)
            next(reader) 
            for row in reader:
                if len(row) < 3: continue
                elo = float(row[0].strip())
                rank = int(row[1].strip())
                name = row[2].strip()
                
                for team in teams:
                    if team.team_name.lower() == name.lower():
                        team.ELO = elo
                        team.ranking = rank
                        break
    except Exception as e:
        print(f"Ranking update error: {e}")

def update_teams_with_schedule_and_results(teams, csv_file_path):
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader) # Skip header
            for row in reader:
                # Row structure: [Date, Week, Day, Date, Time, Network, Team1, T1Score, Team2, T2Score, ...]
                if len(row) < 10: continue
                
                week_num = int(row[1])
                t1_name = row[6].strip()
                t1_score = int(row[7])
                t2_name = row[8].strip()
                t2_score = int(row[9])

                for team in teams:
                    curr_name = team.team_name.lower()
                    
                    if curr_name == t1_name.lower():
                        outcome = "W" if t1_score > t2_score else ("L" if t1_score < t2_score else "T")
                        team.games.append(Game(week_num, t2_name, outcome, t1_score, t2_score))
                    
                    elif curr_name == t2_name.lower():
                        outcome = "W" if t2_score > t1_score else ("L" if t2_score < t1_score else "T")
                        team.games.append(Game(week_num, t1_name, outcome, t2_score, t1_score))
                
        # Sort games by week_num for every team just in case CSV was out of order
        for team in teams:
            team.games.sort(key=lambda x: x.week_num)
            
    except Exception as e:
        print(f"Schedule update error: {e}")

def main():
    # File Paths
    xml_path = 'resources/FBS_list.xml'
    rank_path = 'resources/preseason_rankings/rankings_2025.csv'
    results_path = 'resources/results/results_2025.csv'

    # 1. Load Base Teams
    print("Loading XML data...")
    teams = load_teams_from_xml(xml_path)

    # 2. Update with Preseason Rankings/ELO
    print("Applying rankings...")
    update_teams_with_rankings(teams, rank_path)

    # 3. Process Weekly Games
    print("Processing weekly results...")
    update_teams_with_schedule_and_results(teams, results_path)

    # 4. Launch GUI
    print(f"Successfully loaded {len(teams)} teams. Launching GUI...")
    start_gui(teams)

if __name__ == "__main__":
    main()