import sqlite3
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "resources" / "cfb_elo.db"
XML_PATH = Path(__file__).parent.parent / "resources" / "FBS_list.xml"

CONFERENCE_MAP = {
    '1': 'ACC',
    '4': 'BIG12',
    '5': 'BIG10',
    '8': 'SEC',
    '9': 'PAC12',
    '12': 'CUSA',
    '15': 'MAC',
    '17': 'MWC',
    '18': 'SBC',
    '20': 'BIGSKY',
    '21': 'MVFC',
    '24': 'MEAC',
    '25': 'NEC',
    '27': 'PATRIOT',
    '29': 'SOCON',
    '31': 'SWAC',
    '37': 'IND',
    '48': 'CAA',
    '99': 'IND',
    '151': 'AAC',
    '175': 'UAC',
    '177': 'UAC',
    '179': 'OVC'
}

def resolve_conference_name(raw_conf):
    if not raw_conf:
        return 'IND'
    raw_str = str(raw_conf).strip()
    if raw_str.startswith('Conf_'):
        cid = raw_str.replace('Conf_', '')
        return CONFERENCE_MAP.get(cid, 'IND')
    if raw_str in CONFERENCE_MAP:
        return CONFERENCE_MAP[raw_str]
    if 'independent' in raw_str.lower() or 'independant' in raw_str.lower():
        return 'IND'
    return raw_str

def get_connection(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Core teams table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        espn_id TEXT PRIMARY KEY,
        team_name TEXT NOT NULL,
        alt_name TEXT,
        abbreviation TEXT,
        logo_url TEXT
    )
    """)

    # Team season status (tracking division, conference, and team name year-by-year)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_season_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        espn_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        division TEXT NOT NULL,
        conference TEXT NOT NULL,
        team_name TEXT NOT NULL,
        abbreviation TEXT,
        FOREIGN KEY(espn_id) REFERENCES teams(espn_id),
        UNIQUE(espn_id, year)
    )
    """)

    # Games table (scores and schedules)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS games (
        game_id TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        season_type INTEGER NOT NULL,
        week INTEGER NOT NULL,
        game_date TEXT,
        home_team_id TEXT NOT NULL,
        away_team_id TEXT NOT NULL,
        home_score INTEGER,
        away_score INTEGER,
        status TEXT,
        is_champ INTEGER DEFAULT 0,
        neutral_site INTEGER DEFAULT 0
    )
    """)

    # Weekly poll rankings (AP, Coaches, CFP, ELO)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS polls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        week INTEGER NOT NULL,
        poll_type TEXT NOT NULL,
        espn_id TEXT NOT NULL,
        rank INTEGER NOT NULL,
        rating REAL,
        UNIQUE(year, week, poll_type, espn_id)
    )
    """)

    # System sync metadata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meta_sync (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()

def clean_database_records():
    """Remove TBD teams and standardize conference abbreviations in SQLite DB"""
    conn = get_connection()
    cursor = conn.cursor()

    # Delete TBD or dummy teams from DB
    cursor.execute("DELETE FROM teams WHERE LOWER(team_name) LIKE '%tbd%' OR team_name = '' OR team_name IS NULL")
    cursor.execute("DELETE FROM team_season_status WHERE LOWER(team_name) LIKE '%tbd%' OR team_name = '' OR team_name IS NULL")

    # Update conference names in team_season_status
    cursor.execute("SELECT id, conference FROM team_season_status")
    rows = cursor.fetchall()
    for r in rows:
        c_id = r['id']
        raw_conf = r['conference']
        clean_conf = resolve_conference_name(raw_conf)
        cursor.execute("UPDATE team_season_status SET conference=? WHERE id=?", (clean_conf, c_id))

    conn.commit()
    conn.close()

def save_teams(team_records):
    conn = get_connection()
    cursor = conn.cursor()
    for t in team_records:
        tname = t['team_name']
        if not tname or 'tbd' in tname.lower():
            continue
        cursor.execute("""
        INSERT INTO teams (espn_id, team_name, alt_name, abbreviation, logo_url)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(espn_id) DO UPDATE SET
            team_name=excluded.team_name,
            alt_name=excluded.alt_name,
            abbreviation=excluded.abbreviation,
            logo_url=excluded.logo_url
        """, (t['espn_id'], tname, t.get('alt_name'), t.get('abbreviation'), t.get('logo_url')))
    conn.commit()
    conn.close()

def save_team_season_status(status_records):
    conn = get_connection()
    cursor = conn.cursor()
    for s in status_records:
        tname = s['team_name']
        if not tname or 'tbd' in tname.lower():
            continue
        conf_clean = resolve_conference_name(s['conference'])
        cursor.execute("""
        INSERT INTO team_season_status (espn_id, year, division, conference, team_name, abbreviation)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(espn_id, year) DO UPDATE SET
            division=CASE WHEN team_season_status.division = 'FBS' THEN 'FBS' ELSE excluded.division END,
            conference=excluded.conference,
            team_name=excluded.team_name,
            abbreviation=excluded.abbreviation
        """, (s['espn_id'], s['year'], s['division'], conf_clean, tname, s.get('abbreviation')))
    conn.commit()
    conn.close()

def save_games(game_records):
    conn = get_connection()
    cursor = conn.cursor()
    for g in game_records:
        cursor.execute("""
        INSERT INTO games (game_id, year, season_type, week, game_date, home_team_id, away_team_id, home_score, away_score, status, is_champ, neutral_site)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(game_id) DO UPDATE SET
            home_score=excluded.home_score,
            away_score=excluded.away_score,
            status=excluded.status,
            is_champ=excluded.is_champ
        """, (
            g['game_id'], g['year'], g['season_type'], g['week'], g.get('game_date'),
            g['home_team_id'], g['away_team_id'], g.get('home_score'), g.get('away_score'),
            g.get('status', 'STATUS_SCHEDULED'), g.get('is_champ', 0), g.get('neutral_site', 0)
        ))
    conn.commit()
    conn.close()

def save_polls(poll_records):
    conn = get_connection()
    cursor = conn.cursor()
    for p in poll_records:
        cursor.execute("""
        INSERT INTO polls (year, week, poll_type, espn_id, rank, rating)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(year, week, poll_type, espn_id) DO UPDATE SET
            rank=excluded.rank,
            rating=excluded.rating
        """, (p['year'], p['week'], p['poll_type'], p['espn_id'], p['rank'], p.get('rating')))
    conn.commit()
    conn.close()

def set_meta(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO meta_sync (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_meta(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM meta_sync WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def sync_xml_backup(year=None):
    """
    Export active FBS team list to resources/FBS_list.xml for offline redundancy.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if year is None:
        cursor.execute("SELECT MAX(year) as max_year FROM team_season_status")
        row = cursor.fetchone()
        year = row['max_year'] if row and row['max_year'] else 2025

    cursor.execute("""
    SELECT s.conference, s.team_name
    FROM team_season_status s
    WHERE s.year = ? AND s.division = 'FBS' AND LOWER(s.team_name) NOT LIKE '%tbd%'
    ORDER BY s.conference, s.team_name
    """, (year,))
    rows = cursor.fetchall()

    if not rows:
        cursor.execute("""
        SELECT s.conference, s.team_name
        FROM team_season_status s
        WHERE s.year = (SELECT MAX(year) FROM team_season_status) AND s.division = 'FBS' AND LOWER(s.team_name) NOT LIKE '%tbd%'
        ORDER BY s.conference, s.team_name
        """)
        rows = cursor.fetchall()
        
    conn.close()

    root = ET.Element("NCAA_FBS_Teams")
    conf_dict = {}
    for r in rows:
        c_name = resolve_conference_name(r['conference'])
        t_name = r['team_name']
        if c_name not in conf_dict:
            conf_elem = ET.SubElement(root, "Conference", name=c_name)
            conf_dict[c_name] = conf_elem
        t_elem = ET.SubElement(conf_dict[c_name], "Team")
        t_elem.text = t_name

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    XML_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(XML_PATH, "w", encoding="utf-8") as f:
        f.write(xml_str)

if __name__ == "__main__":
    init_db()
    clean_database_records()
    print("Database cleaned and initialized successfully.")
