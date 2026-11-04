import sqlite3
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "resources" / "cfb_elo.db"
XML_PATH = Path(__file__).parent.parent / "resources" / "all_team_list.xml"

CONFERENCE_MAP = {
    '1': 'ACC',
    '4': 'BIG12',
    '5': 'BIG10',
    '8': 'SEC',
    '9': 'PAC12',
    '12': 'CUSA',
    '15': 'MAC',
    '17': 'MWC',
    '18': 'IND',
    '20': 'BIGSKY',
    '21': 'MVFC',
    '22': 'IVY',
    '24': 'MEAC',
    '25': 'NEC',
    '27': 'PATRIOT',
    '28': 'PFL',
    '29': 'SOCON',
    '30': 'SOUTHLAND',
    '31': 'SWAC',
    '32': 'IND',
    '37': 'SBC',
    '48': 'CAA',
    '99': 'IND',
    '151': 'AAC',
    '167': 'SBC',
    '168': 'SBC',
    '175': 'UAC',
    '177': 'UAC',
    '179': 'OVC'
}

REVERSE_CONF_MAP = {
    'ACC': '1',
    'BIG12': '4',
    'BIG10': '5',
    'SEC': '8',
    'PAC12': '9',
    'CUSA': '12',
    'MAC': '15',
    'MWC': '17',
    'IND': '18',
    'FBS_IND': '18',
    'BIGSKY': '20',
    'MVFC': '21',
    'IVY': '22',
    'MEAC': '24',
    'NEC': '25',
    'PATRIOT': '27',
    'PFL': '28',
    'SOCON': '29',
    'SOUTHLAND': '30',
    'SWAC': '31',
    'FCS_IND': '32',
    'SBC': '37',
    'CAA': '48',
    'AAC': '151',
    'UAC': '177',
    'OVC': '179'
}

CONF_NAME_ALIASES = {
    'ACC': 'ACC',
    'ATLANTICCOASTCONFERENCE': 'ACC',
    'BIG12': 'BIG12',
    'BIG12CONFERENCE': 'BIG12',
    'B12': 'BIG12',
    'BIGTEN': 'BIG10',
    'BIG10': 'BIG10',
    'BIGTENCONFERENCE': 'BIG10',
    'SEC': 'SEC',
    'SOUTHEASTERNCONFERENCE': 'SEC',
    'PAC12': 'PAC12',
    'PAC12CONFERENCE': 'PAC12',
    'PAC': 'PAC12',
    'CUSA': 'CUSA',
    'CONFERENCEUSA': 'CUSA',
    'USA': 'CUSA',
    'MAC': 'MAC',
    'MIDAMERICAN': 'MAC',
    'MIDAMERICANCONFERENCE': 'MAC',
    'MIDAM': 'MAC',
    'MWC': 'MWC',
    'MOUNTAINWEST': 'MWC',
    'MOUNTAINWESTCONFERENCE': 'MWC',
    'MWEST': 'MWC',
    'SBC': 'SBC',
    'SUNBELT': 'SBC',
    'SUNBELTCONFERENCE': 'SBC',
    'BELT': 'SBC',
    'BELTE': 'SBC',
    'BELTW': 'SBC',
    'AAC': 'AAC',
    'AMERICAN': 'AAC',
    'AMERICANCONFERENCE': 'AAC',
    'AMERICANATHLETICCONFERENCE': 'AAC',
    'BIGSKY': 'BIGSKY',
    'BSKY': 'BIGSKY',
    'MVFC': 'MVFC',
    'MEAC': 'MEAC',
    'NEC': 'NEC',
    'NEAST': 'NEC',
    'PATRIOT': 'PATRIOT',
    'PAT': 'PATRIOT',
    'PFL': 'PFL',
    'PIONEER': 'PFL',
    'SOCON': 'SOCON',
    'SOUTHERN': 'SOCON',
    'SOUTH': 'SOCON',
    'SOUTHLAND': 'SOUTHLAND',
    'LAND': 'SOUTHLAND',
    'SWAC': 'SWAC',
    'CAA': 'CAA',
    'UAC': 'UAC',
    'OVC': 'OVC',
    'IVY': 'IVY',
    'IVYLEAGUE': 'IVY',
    'FBSIND': 'IND',
    'FBSINDEP': 'IND',
    'FCSIND': 'IND',
    'FCSINDEP': 'IND',
    'INDAA': 'IND',
    'IND': 'IND'
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
    norm = raw_str.upper().replace('-', '').replace(' ', '').replace('_', '').replace('.', '')
    if norm in CONF_NAME_ALIASES:
        return CONF_NAME_ALIASES[norm]
    if 'independent' in raw_str.lower() or 'independant' in raw_str.lower():
        return 'IND'
    return raw_str

def resolve_conference_id(raw_conf):
    if not raw_conf:
        return None
    raw_str = str(raw_conf).strip()
    if raw_str in CONFERENCE_MAP:
        return raw_str
    if raw_str.startswith('Conf_'):
        cid = raw_str.replace('Conf_', '')
        if cid in CONFERENCE_MAP:
            return cid
    clean_name = resolve_conference_name(raw_conf)
    return REVERSE_CONF_MAP.get(clean_name)

GROUP_MAP = {
    '80': 'FBS',
    '81': 'FCS',
    '82': 'D2',
    '83': 'D3'
}
REVERSE_GROUP_MAP = {v: k for k, v in GROUP_MAP.items()}

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
    
    # Core teams table definition with requested ordering:
    # espn_id, team_name, alt_name, abbreviation, division, division_id, conference, conference_id, logo_url
    target_cols = [
        'espn_id', 'team_name', 'alt_name', 'abbreviation',
        'division', 'division_id', 'conference', 'conference_id', 'logo_url'
    ]
    cursor.execute("PRAGMA table_info(teams)")
    existing_cols = [r['name'] for r in cursor.fetchall()]

    if not existing_cols:
        cursor.execute("""
        CREATE TABLE teams (
            espn_id TEXT PRIMARY KEY,
            team_name TEXT NOT NULL,
            alt_name TEXT,
            abbreviation TEXT,
            division TEXT,
            division_id TEXT,
            conference TEXT,
            conference_id TEXT,
            logo_url TEXT
        )
        """)
    elif existing_cols != target_cols:
        # Rebuild table to guarantee exact column ordering while preserving existing data
        cursor.execute("""
        CREATE TABLE teams_new (
            espn_id TEXT PRIMARY KEY,
            team_name TEXT NOT NULL,
            alt_name TEXT,
            abbreviation TEXT,
            division TEXT,
            division_id TEXT,
            conference TEXT,
            conference_id TEXT,
            logo_url TEXT
        )
        """)
        shared_cols = [c for c in existing_cols if c in target_cols]
        shared_str = ", ".join(shared_cols)
        cursor.execute(f"INSERT OR IGNORE INTO teams_new ({shared_str}) SELECT {shared_str} FROM teams")
        cursor.execute("DROP TABLE teams")
        cursor.execute("ALTER TABLE teams_new RENAME TO teams")

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

    # Fix historic distortion from previous 18/37 swap bug:
    # UConn (41) and Notre Dame (87) are Independents, never Sun Belt
    cursor.execute("UPDATE team_season_status SET conference='IND' WHERE espn_id IN ('41', '87') AND conference='SBC'")
    cursor.execute("UPDATE teams SET conference='IND', conference_id='18' WHERE espn_id IN ('41', '87')")

    # Core Sun Belt members that were mistakenly marked as IND in FBS
    sbc_core_ids = ('2026', '2032', '2247', '2433', '2653', '290', '309', '324', '6')
    cursor.execute(f"UPDATE team_season_status SET conference='SBC' WHERE espn_id IN {sbc_core_ids} AND conference='IND'")
    cursor.execute(f"UPDATE teams SET conference='SBC', conference_id='37' WHERE espn_id IN {sbc_core_ids}")

    # Backfill and clean division, division_id, conference and conference_id in teams table
    cursor.execute("SELECT espn_id, division, division_id, conference, conference_id FROM teams")
    team_rows = cursor.fetchall()
    for tr in team_rows:
        tid = tr['espn_id']
        curr_div = tr['division']
        curr_did = tr['division_id']
        curr_conf = tr['conference']
        curr_cid = tr['conference_id']
        
        # If missing division or conference info, attempt to populate from most recent team_season_status
        if not curr_conf or not curr_cid or not curr_div or not curr_did:
            cursor.execute("""
                SELECT division, conference FROM team_season_status
                WHERE espn_id = ?
                ORDER BY year DESC
                LIMIT 1
            """, (tid,))
            st_row = cursor.fetchone()
            if st_row:
                if not curr_conf and st_row['conference']:
                    curr_conf = st_row['conference']
                if not curr_div and st_row['division']:
                    curr_div = st_row['division']

        clean_conf = resolve_conference_name(curr_conf) if curr_conf else (resolve_conference_name(curr_cid) if curr_cid else None)
        clean_cid = curr_cid or resolve_conference_id(clean_conf)

        if curr_div and not curr_did:
            curr_did = REVERSE_GROUP_MAP.get(curr_div)
        elif curr_did and not curr_div:
            curr_div = GROUP_MAP.get(str(curr_did))

        if (clean_conf != tr['conference'] or clean_cid != tr['conference_id'] or
            curr_div != tr['division'] or curr_did != tr['division_id']):
            cursor.execute("""
                UPDATE teams
                SET division=?, division_id=?, conference=?, conference_id=?
                WHERE espn_id=?
            """, (curr_div, curr_did, clean_conf, clean_cid, tid))

    conn.commit()
    conn.close()

def save_teams(team_records):
    conn = get_connection()
    cursor = conn.cursor()
    for t in team_records:
        tname = t['team_name']
        if not tname or 'tbd' in tname.lower():
            continue

        conf_abbr = t.get('conference')
        conf_id = t.get('conference_id')

        if conf_abbr and not conf_id:
            conf_abbr = resolve_conference_name(conf_abbr)
            conf_id = resolve_conference_id(conf_abbr)
        elif conf_id and not conf_abbr:
            conf_abbr = resolve_conference_name(conf_id)
            conf_id = str(conf_id)
        elif conf_abbr and conf_id:
            conf_abbr = resolve_conference_name(conf_abbr)
            conf_id = str(conf_id)

        div = t.get('division')
        div_id = t.get('division_id')
        if div and not div_id:
            div_id = REVERSE_GROUP_MAP.get(div)
        elif div_id and not div:
            div = GROUP_MAP.get(str(div_id))
        elif div_id:
            div_id = str(div_id)

        cursor.execute("""
        INSERT INTO teams (espn_id, team_name, alt_name, abbreviation, division, division_id, conference, conference_id, logo_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(espn_id) DO UPDATE SET
            team_name=excluded.team_name,
            alt_name=excluded.alt_name,
            abbreviation=excluded.abbreviation,
            division=COALESCE(excluded.division, teams.division),
            division_id=COALESCE(excluded.division_id, teams.division_id),
            conference=COALESCE(excluded.conference, teams.conference),
            conference_id=COALESCE(excluded.conference_id, teams.conference_id),
            logo_url=excluded.logo_url
        """, (t['espn_id'], tname, t.get('alt_name'), t.get('abbreviation'), div, div_id, conf_abbr, conf_id, t.get('logo_url')))
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
    #init_db()
    #clean_database_records()
    sync_xml_backup()
    print("Database cleaned and initialized successfully.")
