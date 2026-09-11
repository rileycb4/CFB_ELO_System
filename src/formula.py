import math

class EloParameters:
    def __init__(self, C=400.0, N=136, K0=48.0, K_MIN=24.0, GAMMA=0.5, BETA=0.675, BETA_MAX=1.5, RHO=1.125, OMEGA=0.5):
        self.C = C              # Scaling factor
        self.N = N              # Total number of teams
        self.K0 = K0            # Initial K-factor
        self.K_MIN = K_MIN      # Minimum K-factor
        self.GAMMA = GAMMA      # Margin of victory weight
        self.BETA = BETA        # Upset factor weight
        self.BETA_MAX = BETA_MAX # Maximum upset boost cap
        self.RHO = RHO          # Upset non-linear exponent
        self.OMEGA = OMEGA      # Strength of Schedule adjustment factor

DEFAULT_PARAMS = EloParameters()

def calculate_delta_elo(team_elo, opp_elo, team_rank, opp_rank, outcome, score_t, score_opp, week_num, params=None):
    if params is None:
        params = DEFAULT_PARAMS

    C = params.C
    N = params.N
    K0 = params.K0
    K_MIN = params.K_MIN
    GAMMA = params.GAMMA
    BETA = params.BETA
    BETA_MAX = params.BETA_MAX
    RHO = params.RHO

    # Keff Calculation
    keff = max(K_MIN, K0 * (0.95**(int(week_num) - 1)))
    # Et (Expected win probability)
    et = 1 / (1 + 10**((opp_elo - team_elo) / C))
    # m (Margin of victory factor)
    m = math.log(1 + abs(int(score_t) - int(score_opp)) / C) 
    
    # U (Upset adjustment)
    u = 1.0
    is_upset = (outcome == 'L' and team_rank < opp_rank) or \
               (outcome == 'W' and team_rank > opp_rank)
    if is_upset:
        u = min(1 + BETA * ((abs(team_rank - opp_rank)) / (N - 1))**RHO, 1 + BETA_MAX)

    st = 1 if outcome == 'W' else 0

    return keff * (st - et) * (1 + GAMMA * m) * u