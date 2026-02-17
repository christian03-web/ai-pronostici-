import requests
from flask import Flask, render_template
from scipy.stats import poisson

app = Flask(__name__)

LEAGUES = {
    'Premier League': 'eng.1', 'Serie A': 'ita.1', 'La Liga': 'esp.1',
    'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf', 'Serie B': 'ita.2'
}

def get_rank_weight(team_id, league_id):
    """Recupera la posizione in classifica per pesare la forza della squadra."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/standings"
    try:
        data = requests.get(url).json()
        for team in data['children'][0]['standings']['entries']:
            if team['team']['id'] == team_id:
                # Più è alta la posizione (1°), più il peso è vicino a 1.0
                rank = int(team['stats'][0]['displayValue'])
                return max(0.5, 1.5 - (rank / 20)) 
    except: return 1.0 # Default se la classifica non è disponibile
    return 1.0

def calculate_advanced_logic(h_id, a_id, l_id, l_name):
    # Forza basata sulla classifica
    h_weight = get_rank_weight(h_id, l_id)
    a_weight = get_rank_weight(a_id, l_id)
    
    # Media gol del campionato
    league_mu = 3.2 if l_name in ['Bundesliga', 'Eredivisie'] else 2.6
    
    # Mu finale (media gol attesa per questo match specifico)
    final_mu = league_mu * ((h_weight + a_weight) / 2)
    
    # Poisson per Over 2.5 e GG
    prob_over = (1 - (poisson.pmf(0, final_mu) + poisson.pmf(1, final_mu) + poisson.pmf(2, final_mu))) * 100
    prob_gg = (1 - poisson.pmf(0, final_mu/1.7)) * (1 - poisson.pmf(0, final_mu/1.7)) * 100
    
    return round(prob_over, 1), round(prob_gg, 1)

def fetch_total_scanner():
    results = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            data = requests.get(url).json()
            for event in data.get('events', []):
                h_team = event['competitions'][0]['competitors'][0]
                a_team = event['competitions'][0]['competitors'][1]
                
                over_p, gg_p = calculate_advanced_logic(h_team['id'], a_team['id'], l_id, name)
                
                results.append({
                    'league': name,
                    'match': event['name'],
                    'status': event['status']['type']['shortDetail'],
                    'over_p': over_p,
                    'gg_p': gg_p,
                    'is_gold': over_p > 78 or gg_p > 80 # Il tuo target 80%
                })
        except: continue
    return results

@app.route('/')
def index():
    return render_template('index.html', matches=fetch_total_scanner())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
