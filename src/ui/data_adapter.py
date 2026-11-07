"""Bridge between the existing SQLite/Elo engine and the GUI.

This module intentionally does not recalculate Elo. It consumes the results
from src.main.calculate_multi_year_elo() and supplements them with all schedule
rows (including games that have not been played yet) from the existing DB.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from archive.src.database import get_connection
from archive.src.main import calculate_multi_year_elo, get_available_years


def _record_text(wins: int, losses: int) -> str:
    return f"{wins}-{losses}"


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _grid_week(season_type: int, raw_week: int) -> int:
    # Match the existing ELO driver's weekly indexing.
    return int(raw_week) if int(season_type) == 2 else min(16, 14 + int(raw_week))


def _played(status: Any, home_score: Any, away_score: Any) -> bool:
    return (
        str(status or "").upper() == "STATUS_FINAL"
        and home_score is not None
        and away_score is not None
    )


def _team_record(team_obj) -> Dict[str, Any]:
    games = list(getattr(team_obj, "schedule", []) or [])
    wins = sum(1 for game in games if game.get("outcome") == "W")
    losses = sum(1 for game in games if game.get("outcome") == "L")
    points_for = sum(int(game.get("team_score") or 0) for game in games)
    points_against = sum(int(game.get("opp_score") or 0) for game in games)
    count = len(games)
    return {
        "wins": wins,
        "losses": losses,
        "record": _record_text(wins, losses),
        "points_for": points_for / count if count else None,
        "points_against": points_against / count if count else None,
        "average_margin": (points_for - points_against) / count if count else None,
    }


def _logo_text(team_obj) -> str:
    name = getattr(team_obj, "team_name", "?")
    return "".join(part[0] for part in name.split()[:2]).upper() or "?"


def _fetch_all_schedule_rows(year: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                g.game_id, g.year, g.season_type, g.week, g.game_date,
                g.home_team_id, g.away_team_id,
                g.home_score, g.away_score, g.status,
                g.is_champ, g.neutral_site,
                ht.team_name AS home_team_name,
                ht.logo_url AS home_logo_url,
                at.team_name AS away_team_name,
                at.logo_url AS away_logo_url
            FROM games g
            LEFT JOIN teams ht ON ht.espn_id = g.home_team_id
            LEFT JOIN teams at ON at.espn_id = g.away_team_id
            WHERE g.year = ?
            ORDER BY g.week ASC, g.game_date ASC, g.game_id ASC
            """,
            (int(year),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _build_game_history_lookup(teams_by_id: Dict[str, Any]):
    """Index game-history rows created by the Elo engine by (team id, game id)."""
    result = {}
    for team_id, team_obj in teams_by_id.items():
        last_rank = None
        for game in sorted(
            getattr(team_obj, "schedule", []) or [],
            key=lambda g: (g.get("date") or "", int(g.get("display_week") or g.get("week") or 0), str(g.get("game_id", ""))),
        ):
            # rank_before / rank_delta are populated by the patched engine below.
            result[(str(team_id), str(game.get("game_id")))] = game
            last_rank = game.get("new_rank", last_rank)
    return result


def load_dashboard_data(year: int) -> Dict[str, Any]:
    """Load the rankings data and complete schedules for one season."""
    season = calculate_multi_year_elo(int(year))
    teams_by_id = {str(t.espn_id): t for t in season["teams"]}
    teams_by_name = {t.team_name: t for t in season["teams"]}
    records = {name: _team_record(team) for name, team in teams_by_name.items()}
    game_history = _build_game_history_lookup(teams_by_id)
    schedule_rows = _fetch_all_schedule_rows(int(year))

    schedules: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    upcoming_by_team: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in schedule_rows:
        home_id = str(row.get("home_team_id") or "")
        away_id = str(row.get("away_team_id") or "")
        home = teams_by_id.get(home_id)
        away = teams_by_id.get(away_id)
        if not home or not away:
            continue

        played = _played(row.get("status"), row.get("home_score"), row.get("away_score"))
        neutral = bool(row.get("neutral_site"))
        week = _grid_week(row.get("season_type") or 2, row.get("week") or 0)
        game_date = (row.get("game_date") or "")[:10]

        for team_id, team_obj, opp_id, opponent, is_home in (
            (home_id, home, away_id, away, True),
            (away_id, away, home_id, home, False),
        ):
            history = game_history.get((team_id, str(row["game_id"])), {}) if played else {}
            if neutral:
                location = "N"
            else:
                location = "H" if is_home else "A"

            opp_name = opponent.team_name
            opp_record = records.get(opp_name, {}).get("record", "0-0")
            current_opp_elo = season["final_elos"].get(opp_name)
            game_opp_elo = history.get("opponent_elo_before", current_opp_elo)

            if played:
                team_score = int(row["home_score"] if is_home else row["away_score"])
                opp_score = int(row["away_score"] if is_home else row["home_score"])
                won = team_score > opp_score
                result = f"{'W' if won else 'L'} {team_score}-{opp_score}"
                delta_elo = history.get("delta")
                delta_rank = history.get("delta_rank")
                new_elo = history.get("new_elo")
                new_rank = history.get("new_rank")
            else:
                result = "—"
                delta_elo = None
                delta_rank = None
                new_elo = None
                new_rank = None
                game_opp_elo = current_opp_elo

            entry = {
                "game_id": str(row["game_id"]),
                "week": week,
                "raw_week": int(row.get("week") or 0),
                "date": game_date,
                "location": location,
                "opponent_name": opp_name,
                "opponent_id": opp_id,
                "opponent_record": opp_record,
                "opponent_elo": game_opp_elo,
                "result": result,
                "played": played,
                "delta_elo": delta_elo,
                "delta_rank": delta_rank,
                "new_elo": new_elo,
                "new_rank": new_rank,
                "team_score": int(row["home_score"] if is_home else row["away_score"]) if played else None,
                "opp_score": int(row["away_score"] if is_home else row["home_score"]) if played else None,
                "game_type": "Championship" if row.get("is_champ") else ("Postseason / Playoff" if int(row.get("season_type") or 0) == 3 else "Regular"),
            }
            schedules[team_id].append(entry)
            if not played:
                upcoming_by_team[team_id].append(entry)

    output_teams = []
    for team_id, team_obj in teams_by_id.items():
        name = team_obj.team_name
        rec = records.get(name, {})
        team_schedule = sorted(
            schedules.get(team_id, []),
            key=lambda g: (g["week"], g["date"], g["game_id"]),
        )
        upcoming = sorted(
            upcoming_by_team.get(team_id, []),
            key=lambda g: (g["week"], g["date"], g["game_id"]),
        )
        last_played = next((g for g in reversed(team_schedule) if g["played"]), None)
        next_game = upcoming[0] if upcoming else None
        elo_change = last_played.get("delta_elo") if last_played else 0.0
        rank_change = last_played.get("delta_rank") if last_played else 0

        # H2H comparison values: use stats that the current engine can support.
        sos = season.get("sos_values", {}).get(name)
        output_teams.append({
            "espn_id": team_id,
            "name": name,
            "nickname": name,
            "conference": team_obj.conference,
            "division": team_obj.division,
            "rank": season["final_ranks"].get(name),
            "elo": season["final_elos"].get(name),
            "record": rec.get("record", "0-0"),
            "wins": rec.get("wins", 0),
            "losses": rec.get("losses", 0),
            "logo_text": _logo_text(team_obj),
            "logo_url": team_obj.logo_url,
            "primary": "#C8103E",
            "elo_change": elo_change or 0.0,
            "previous_rank": (season["final_ranks"].get(name, 0) + (rank_change or 0)),
            "rank_change": rank_change or 0,
            "next_opponent": next_game["opponent_name"] if next_game else "BYE",
            "schedule": team_schedule,
            "points_for": rec.get("points_for"),
            "points_against": rec.get("points_against"),
            "average_margin": rec.get("average_margin"),
            "strength_of_schedule": sos,
            # Not currently produced by the supplied drivers; keep these absent
            # rather than inventing efficiency values.
            "offensive_efficiency": None,
            "defensive_efficiency": None,
        })

    output_teams.sort(key=lambda t: (t["rank"] is None, t["rank"] or 9999))
    return {
        "year": int(year),
        "teams": output_teams,
        "teams_by_name": {t["name"]: t for t in output_teams},
        "season": season,
    }


def find_last_meeting(team_a: Dict[str, Any], team_b: Dict[str, Any]) -> Dict[str, Any]:
    """Find the latest played meeting from the already-loaded team schedule."""
    meetings = [
        game for game in team_a.get("schedule", [])
        if game.get("played") and game.get("opponent_name") == team_b.get("name")
    ]
    if not meetings:
        return {
            "home_score": "—", "away_score": "—",
            "competition": "No completed meeting found", "date": "—",
        }
    game = sorted(meetings, key=lambda g: (g.get("date") or "", g.get("week") or 0))[-1]
    return {
        "home_score": game.get("team_score", "—"),
        "away_score": game.get("opp_score", "—"),
        "competition": game.get("game_type", "Previous meeting"),
        "date": game.get("date") or f"Week {game.get('week')}",
    }


def available_years() -> List[int]:
    return get_available_years()
