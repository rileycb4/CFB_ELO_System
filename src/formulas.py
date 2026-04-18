import math

def calculate_delta_elo(team_elo, opp_elo, team_rank, opp_rank, game, params):
    K = params.get('K', 48)
    K0 = params.get('K0', 24)
    C = params.get('C', 400)
    gamma = params.get('gamma', 0.5)
    pho = params.get('pho', 1.125)
    beta = params.get('beta', 0.675)
    beta_max = params.get('beta_max', 1.5)
    N = params.get('N', 136)

    # 1. Keff Calculation
    keff = max(K, K0 * (0.95**(game.week_num - 1)))
    
    # 2. Et (Expected)
    et = 1 / (1 + 10**((opp_elo - team_elo) / C))
    
    # 3. m (Margin)
    m = math.log(1 + abs(game.score_us - game.score_them)) / C
    
    # 4. U (Upset/Adjustment)
    u = 1.0
    is_upset = (game.outcome == 'L' and team_rank < opp_rank) or \
               (game.outcome == 'W' and team_rank > opp_rank)
    if is_upset:
        u_calc = 1 + beta * ((abs(team_rank - opp_rank)) / (N - 1))**pho
        u = min(u_calc, 1 + beta_max)

    st = 1 if game.outcome == 'W' else 0
    return keff * (st - et) * (1 + gamma * m) * u

def calculate_sos_adjustment(sos_avg, weight=0.5):
    """Calculates the adjustment value based on Strength of Schedule."""
    return (sos_avg - 1500) * weight