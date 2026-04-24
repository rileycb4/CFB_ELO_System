import math

# Constants for the Formula
C = 400          # Scaling factor
N = 136          # Total number of teams (FBS)
K0 = 48.0        # Initial K-factor
K_MIN = 24.0     # Minimum K-factor
GAMMA = 0.5
BETA = 0.675
BETA_MAX = 1.5
RHO = 1.125

def calculate_delta_elo(team_elo, opp_elo, team_rank, opp_rank, outcome, score_t, score_opp, week_num):

    # Keff Calculation
    keff = max(K_MIN, K0 * (0.95**(int(week_num) - 1)))
    # Et (Expected)
    et = 1 / (1 + 10**((opp_elo - team_elo) / C))
    # m (Margin)
    m = math.log(1 + abs(int(score_t) - int(score_opp))/ C) 
    # U (Upset/Adjustment)
    u = 1.0
    is_upset = (outcome == 'L' and team_rank < opp_rank) or \
               (outcome == 'W' and team_rank > opp_rank)
    if is_upset:
        u = min(1 + BETA * ((abs(team_rank - opp_rank)) / (N - 1))**RHO, 1 + BETA_MAX)

    st = 1 if outcome == 'W' else 0

    
    #if t_name == "Maryland":
        #print(f"{round(team_elo,3)}-{round(opp_elo,3)}:{round(float(team_elo) - float(opp_elo),3)} | {team_rank}-{opp_rank}:{int(team_rank) - int(opp_rank)} | {score_t}-{score_opp}:{int(score_t) - int(score_opp)} | {round(keff,5)} | St-Et:({round(st,5)}-{round(et,5)}={round(st-et,5)}) | (1+gamma+{round(m,5)} | {round(u,5)}) | D_ELO: {round(keff * (st - et) * (1 + GAMMA * m) * u,5)}")
    return keff * (st - et) * (1 + GAMMA * m) * u

'''def calculate_delta_elo(team, opponent, team_score, opp_score, week):
    """
    Implements: Delta_Elo = Keff * (St-Et) * (1+gamma*m) * U
    """
    # 1. Keff = MAX(K, K0 * 0.95^(Week-1))
    keff = max(K_MIN, K0 * (0.95 ** (week - 1)))
    
    # 2. St = 1 if win, 0 if loss
    st = 1 if team_score > opp_score else 0
    
    # 3. Et = 1 / (1 + 10^((ELOopp - ELOt) / C))
    et = 1 / (1 + 10 ** ((opponent.ELO - team.ELO) / C))
    
    # 4. m = ln(1 + abs(Scoret - scoreopp)) / C
    m = math.log(1 + abs(team_score - opp_score)) / C
    
    # 5. U Logic
    if st == 1:
        u = 1.0
    else:
        # U = min(1 + beta * (abs(Rankt - Rankopp) / N - 1)^rho, 1 + Betamax)
        # Handle the power function carefully for negative bases
        rank_diff_ratio = (abs(team.ranking - opponent.ranking) / N) - 1
        # If the term inside is negative, we take the absolute to avoid math errors with rho
        u_calc = 1 + BETA * (abs(rank_diff_ratio) ** RHO)
        u = min(u_calc, 1 + BETA_MAX)
        
    delta_elo = keff * (st - et) * (1 + GAMMA * m) * u
    return delta_elo'''