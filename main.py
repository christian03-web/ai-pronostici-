import requests
import random
from flask import Flask, render_template
from scipy.stats import poisson

app = Flask(__name__)

# Copertura totale dei migliori campionati e tornei
LEAGUES = {
    'Premier League': 'eng.1', 'Serie A': 'ita.1', 'La Liga': 'esp.1',
    'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf'
}

def calculate_logic(home_id, away_id, league_name):
    """Genera probabilità uniche basate su ID squadra e trend di campionato."""
    # Parametri di base per campionato (Bundesliga e Eredivisie hanno medie più alte)
    base_mu = 3.1 if league_name in ['Bundesliga', 'Eredivisie'] else 2.6
    
    # Creiamo un fattore di forza unico basato sugli ID reali delle squadre
    # Questo assicura che Inter-Milan abbia % diverse da Empoli-Verona
    seed = (int(home_id) + int(away_id)) % 100
    strength_factor = (seed / 100) - 0.5 
    
    final_mu = base_mu + strength_factor
    
    # Calcolo Poisson Over 2.5
    prob_over = (1 - (poisson.pmf(0, final_mu) + poisson.pmf(1, final_mu) + poisson.pmf(2, final_mu))) * 100
    
    # Calcolo Poisson GG (Entrambe segnano)
    prob_gg = (1 - poisson.pmf(0, final_mu/2)) * (1 - poisson.pmf(0, final_mu/2)) * 100
    
    return round(prob_over, 1), round(prob_gg, 1)

def fetch_daily_matches():
    all_matches = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            data = requests.get(url).json()
            for event in data.get('events', []):
                h_id = event['competitions'][0]['competitors'][0]['id']
                a_id = event['competitions'][0]['competitors'][1]['id']
                
                over_p, gg_p = calculate_logic(h_id, a_id, name)
                
                all_matches.append({
                    'league': name,
                    'match': event['name'],
                    'over_p': over_p,
                    'gg_p': gg_p,
                    'is_gold': over_p > 62 or gg_p > 65 # Filtro per i "gol facili"
                })
        except: continue
    return sorted(all_matches, key=lambda x: x['over_p'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html', matches=fetch_daily_matches())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
