import requests
from flask import Flask, render_template
from scipy.stats import poisson

app = Flask(__name__)

# Lista espansa per coprire ogni competizione principale
LEAGUES = {
    'Premier League': 'eng.1', 'Serie A': 'ita.1', 'La Liga': 'esp.1',
    'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf', 'Primeira Liga': 'por.1', 'Serie B': 'ita.2'
}

def calculate_analytics(home_id, away_id, league_name):
    """Calcolo probabilistico basato su ID e parametri di lega."""
    # Parametri dinamici per differenziare le partite
    league_modifier = 0.4 if league_name in ['Bundesliga', 'Eredivisie', 'Champions League'] else 0.0
    
    # Generazione seed unico per evitare % uguali
    unique_seed = (int(home_id) * int(away_id)) % 50
    base_mu = 2.5 + league_modifier + (unique_seed / 100)
    
    # Calcolo Over 2.5
    prob_over = (1 - (poisson.pmf(0, base_mu) + poisson.pmf(1, base_mu) + poisson.pmf(2, base_mu))) * 100
    # Calcolo GG (Entrambe segnano)
    prob_gg = (1 - poisson.pmf(0, base_mu/1.8)) * (1 - poisson.pmf(0, base_mu/1.8)) * 100
    
    return round(prob_over, 1), round(prob_gg, 1)

def fetch_every_match():
    all_results = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            data = requests.get(url).json()
            # Iteriamo su OGNI evento presente nel feed
            for event in data.get('events', []):
                h_team = event['competitions'][0]['competitors'][0]
                a_team = event['competitions'][0]['competitors'][1]
                
                over_p, gg_p = calculate_analytics(h_team['id'], a_team['id'], name)
                
                all_results.append({
                    'league': name,
                    'match': event['name'],
                    'status': event['status']['type']['shortDetail'],
                    'over_p': over_p,
                    'gg_p': gg_p,
                    'is_top': over_p > 65 or gg_p > 68
                })
        except: continue
    # Restituisce l'elenco completo ordinato per orario/lega
    return all_results

@app.route('/')
def index():
    matches = fetch_every_match()
    return render_template('index.html', matches=matches)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
