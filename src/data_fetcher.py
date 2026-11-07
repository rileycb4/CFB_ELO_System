import sys
import time
import json
import urllib.request
import argparse
from datetime import datetime
import threading
from pathlib import Path

from archive.src.database import (
    init_db, save_teams, save_team_season_status,
    save_games, save_polls, set_meta, get_meta, sync_xml_backup,
    resolve_conference_name, resolve_conference_id
)

BASE_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
BASE_TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams?limit=1000"
BASE_RANKINGS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"

# Group IDs: 80 = FBS, 81 = FCS, 82 = Div II, 83 = Div III
GROUP_MAP = {
    '80': 'FBS',
    '81': 'FCS',
    '82': 'D2',
    '83': 'D3'
}

def http_get_json(url, retries=3, delay=1.0):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as res:
                if res.status == 200:
                    return json.loads(res.read().decode('utf-8'))
        except Exception as e:
            if attempt == retries - 1:
                print(f"[Warning] Failed to fetch {url}: {e}")
                return None
            time.sleep(delay)
    return None

def fetch_teams_conference_map():
    """
    Fetch current FBS and FCS standings to build a map of {team_id: {'conference': conf_abbr, 'conference_id': conf_id, 'division': div, 'division_id': did}}
    """
    conf_map = {}
    for group_param in ['', '?group=81']:
        url = f"https://site.api.espn.com/apis/v2/sports/football/college-football/standings{group_param}"
        data = http_get_json(url)
        if not data:
            continue
        div_label = 'FBS' if group_param == '' else 'FCS'
        div_id = '80' if group_param == '' else '81'
        for conf in data.get('children', []):
            cid = str(conf.get('id', ''))
            cabbr = conf.get('abbreviation', '')
            entries = []
            if 'standings' in conf and 'entries' in conf['standings']:
                entries.extend(conf['standings']['entries'])
            for sub in conf.get('children', []):
                if 'standings' in sub and 'entries' in sub['standings']:
                    entries.extend(sub['standings']['entries'])
            
            clean_conf = resolve_conference_name(cabbr or cid)
            clean_cid = cid or resolve_conference_id(clean_conf)
            for ent in entries:
                t = ent.get('team', {})
                tid = str(t.get('id', ''))
                if tid:
                    conf_map[tid] = {
                        'conference': clean_conf,
                        'conference_id': clean_cid,
                        'division': div_label,
                        'division_id': div_id
                    }
    return conf_map

def fetch_and_store_all_teams():
    print("Fetching global team metadata from ESPN...")
    conf_map = fetch_teams_conference_map()
    data = http_get_json(BASE_TEAMS_URL)
    if not data:
        return []
    
    team_records = []
    try:
        raw_teams = data['sports'][0]['leagues'][0]['teams']
        for item in raw_teams:
            t = item.get('team', {})
            espn_id = str(t.get('id'))
            if not espn_id:
                continue
            
            logo_url = ""
            logos = t.get('logos', [])
            if logos:
                logo_url = logos[0].get('href', '')
                
            c_info = conf_map.get(espn_id, {})
            conf_abbr = c_info.get('conference')
            conf_id = c_info.get('conference_id')
            div_name = c_info.get('division')
            div_id = c_info.get('division_id')

            team_records.append({
                'espn_id': espn_id,
                'team_name': t.get('displayName', t.get('location', '')),
                'alt_name': t.get('shortDisplayName', t.get('nickname', '')),
                'abbreviation': t.get('abbreviation', ''),
                'division': div_name,
                'division_id': div_id,
                'conference': conf_abbr,
                'conference_id': conf_id,
                'logo_url': logo_url
            })
        
        save_teams(team_records)
        print(f"Saved {len(team_records)} team records.")
    except Exception as e:
        print(f"Error parsing team metadata: {e}")
    return team_records

def parse_scoreboard_data(data, year, group_id):
    if not data or 'events' not in data:
        return [], [], []

    team_records = []
    status_records = []
    game_records = []

    division_label = GROUP_MAP.get(str(group_id), 'Other')
    division_id_str = str(group_id)

    for ev in data.get('events', []):
        game_id = str(ev.get('id'))
        game_date = ev.get('date', '')
        
        season_type = ev.get('season', {}).get('type', 2)
        week_num = ev.get('week', {}).get('number', 1)

        competitions = ev.get('competitions', [])
        if not competitions:
            continue
        
        comp = competitions[0]
        neutral_site = 1 if comp.get('neutralSite', False) else 0
        
        notes = comp.get('notes', [])
        is_champ = 0
        for note in notes:
            headline = note.get('headline', '').lower()
            if 'championship' in headline or 'title' in headline:
                is_champ = 1

        status_type = comp.get('status', {}).get('type', {}).get('name', 'STATUS_SCHEDULED')

        competitors = comp.get('competitors', [])
        if len(competitors) < 2:
            continue

        home_comp = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
        away_comp = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])

        h_team = home_comp.get('team', {})
        a_team = away_comp.get('team', {})

        h_id = str(h_team.get('id'))
        a_id = str(a_team.get('id'))

        if not h_id or not a_id:
            continue

        # Extract team metadata
        h_name = h_team.get('displayName', h_team.get('location', ''))
        a_name = a_team.get('displayName', a_team.get('location', ''))

        if not h_name or not a_name or 'tbd' in h_name.lower() or 'tbd' in a_name.lower():
            continue

        h_abbrev = h_team.get('abbreviation', '')
        a_abbrev = a_team.get('abbreviation', '')

        # Scores
        h_score = int(home_comp['score']) if 'score' in home_comp and home_comp['score'] != "" else None
        a_score = int(away_comp['score']) if 'score' in away_comp and away_comp['score'] != "" else None

        # Add to teams & status
        for t_info in [(h_id, h_name, h_abbrev, h_team), (a_id, a_name, a_abbrev, a_team)]:
            tid, tname, tabbr, team_dict = t_info
            
            # Conference
            conf_id = team_dict.get('conferenceId')
            conf_name = resolve_conference_name(conf_id)
            conf_id_str = str(conf_id) if conf_id else resolve_conference_id(conf_name)

            team_records.append({
                'espn_id': tid,
                'team_name': tname,
                'alt_name': tname,
                'abbreviation': tabbr,
                'division': division_label,
                'division_id': division_id_str,
                'conference': conf_name,
                'conference_id': conf_id_str,
                'logo_url': f"https://a.espncdn.com/i/teamlogos/ncaa/500/{tid}.png"
            })

            status_records.append({
                'espn_id': tid,
                'year': year,
                'division': division_label,
                'conference': conf_name,
                'team_name': tname,
                'abbreviation': tabbr
            })

        game_records.append({
            'game_id': game_id,
            'year': year,
            'season_type': season_type,
            'week': week_num,
            'game_date': game_date,
            'home_team_id': h_id,
            'away_team_id': a_id,
            'home_score': h_score,
            'away_score': a_score,
            'status': status_type,
            'is_champ': is_champ,
            'neutral_site': neutral_site
        })

    return team_records, status_records, game_records

def fetch_season_games(year, groups=['80', '81']):
    """
    Fetch all regular season & postseason games for given year and group IDs
    """
    print(f"Fetching games for year {year} (Groups: {groups})...")
    all_teams = []
    all_status = []
    all_games = []

    for group_id in groups:
        # Regular Season (seasontype=2)
        for week in range(1, 17):
            url = f"{BASE_SCOREBOARD_URL}?dates={year}&seasontype=2&week={week}&groups={group_id}"
            data = http_get_json(url)
            t_rec, s_rec, g_rec = parse_scoreboard_data(data, year, group_id)
            all_teams.extend(t_rec)
            all_status.extend(s_rec)
            all_games.extend(g_rec)

        # Postseason (seasontype=3)
        for week in range(1, 5):
            url = f"{BASE_SCOREBOARD_URL}?dates={year}&seasontype=3&week={week}&groups={group_id}"
            data = http_get_json(url)
            t_rec, s_rec, g_rec = parse_scoreboard_data(data, year, group_id)
            all_teams.extend(t_rec)
            all_status.extend(s_rec)
            all_games.extend(g_rec)

    if all_teams:
        save_teams(all_teams)
    if all_status:
        save_team_season_status(all_status)
    if all_games:
        save_games(all_games)

    print(f"Year {year} complete: {len(all_games)} games saved.")

def fetch_poll_rankings_for_year(year):
    """
    Fetch AP Poll, Coaches Poll, and CFP rankings for given year across weeks.
    """
    print(f"Fetching poll rankings for {year}...")
    poll_records = []
    
    for week in range(1, 17):
        url = f"{BASE_RANKINGS_URL}?dates={year}&seasontype=2&week={week}"
        data = http_get_json(url)
        if not data or 'rankings' not in data:
            continue

        for poll in data.get('rankings', []):
            raw_name = poll.get('name', '').lower()
            poll_type = None
            if 'ap' in raw_name or 'associated press' in raw_name:
                poll_type = 'AP'
            elif 'coaches' in raw_name or 'afca' in raw_name or 'usa' in raw_name:
                poll_type = 'Coaches'
            elif 'playoff' in raw_name or 'cfp' in raw_name or 'committee' in raw_name:
                poll_type = 'CFP'
            
            if not poll_type:
                continue

            for rank_item in poll.get('ranks', []):
                curr_rank = rank_item.get('current')
                t_obj = rank_item.get('team', {})
                espn_id = str(t_obj.get('id'))
                if curr_rank and espn_id:
                    poll_records.append({
                        'year': year,
                        'week': week,
                        'poll_type': poll_type,
                        'espn_id': espn_id,
                        'rank': int(curr_rank),
                        'rating': None
                    })

    if poll_records:
        save_polls(poll_records)
        print(f"Saved {len(poll_records)} poll rank entries for {year}.")

def fetch_staged_data(start_year=2021, end_year=2026):
    """
    Fast initial pull: FBS (80) & FCS (81) from 2021 to current year.
    """
    init_db()
    fetch_and_store_all_teams()

    current_yr = datetime.now().year
    end_year = min(end_year, current_yr)

    print(f"Starting staged data pull ({start_year} - {end_year})...")
    for yr in range(start_year, end_year + 1):
        fetch_season_games(yr, groups=['80', '81'])
        fetch_poll_rankings_for_year(yr)

    sync_xml_backup(end_year)
    set_meta("last_staged_pull", datetime.now().isoformat())
    print("Staged data pull completed successfully!")

def fetch_full_historical_data(start_year=2001, end_year=2026):
    """
    Complete historical backfill (2001 - present day, all groups).
    """
    init_db()
    fetch_and_store_all_teams()

    current_yr = datetime.now().year
    end_year = min(end_year, current_yr)

    print(f"Starting FULL historical data backfill ({start_year} - {end_year})...")
    for yr in range(start_year, end_year + 1):
        fetch_season_games(yr, groups=['80', '81', '82', '83'])
        fetch_poll_rankings_for_year(yr)

    sync_xml_backup(end_year)
    set_meta("full_backfill_complete", "true")
    set_meta("last_full_pull", datetime.now().isoformat())
    print("FULL historical backfill completed successfully!")

def update_latest_data():
    """
    Delta update: refreshes current season and previous season games/polls.
    """
    init_db()
    current_yr = datetime.now().year
    print(f"Running delta update for {current_yr-1} and {current_yr}...")
    fetch_season_games(current_yr - 1, groups=['80', '81'])
    fetch_season_games(current_yr, groups=['80', '81'])
    fetch_poll_rankings_for_year(current_yr)
    sync_xml_backup(current_yr)
    set_meta("last_delta_update", datetime.now().isoformat())
    print("Delta update completed!")

def start_background_scheduler(interval_hours=24):
    def daemon_loop():
        while True:
            time.sleep(interval_hours * 3600)
            try:
                print(f"[{datetime.now()}] Automated scheduled update starting...")
                update_latest_data()
            except Exception as e:
                print(f"[Error in scheduled update]: {e}")
    
    t = threading.Thread(target=daemon_loop, daemon=True)
    t.start()
    print("Background update daemon started.")

def main():
    parser = argparse.ArgumentParser(description="CFB ELO Data Fetcher CLI")
    parser.add_argument("--staged", action="store_true", help="Pull fast staged data (2021-present, FBS/FCS)")
    parser.add_argument("--full", action="store_true", help="Pull complete historical data (2001-present, all divisions)")
    parser.add_argument("--update", action="store_true", help="Run delta update for active/recent games")
    
    args = parser.parse_args()

    if args.full:
        fetch_full_historical_data()
    elif args.update:
        update_latest_data()
    else:
        # Default to staged pull if no flag specified
        fetch_staged_data()

if __name__ == "__main__":
    main()
