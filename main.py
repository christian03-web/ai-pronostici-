import requests
import numpy as np
from flask import Flask, render_template
from scipy.stats import poisson

app = Flask(__name__)

LEAGUES = {
    'Premier League': 'eng.1', 'Serie A': 'ita.1', 'La Liga': 'esp.1',
    'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa'
}

def predict_match(home_strength, away_strength, league_avg=1.5):
    """Calcola la probabilità esatta usando il potenziale offensivo/difensivo."""
    # Simulazione forza relativa (in un sistema pro useresti xG reali)
    home_expectancy = home_strength * (league_avg / away_strength)
    away_expectancy = away_strength * (league_avg / home_strength)
    
    # Calcolo Over 2.5
    max_goals = 10
    prob_matrix = np.outer(
        poisson.pmf(range(max_goals), home_expectancy),
        poisson.pmf(range(max_goals), away_expectancy)
    )
    
    over_25 = 100 * (1 - (prob_matrix[0,0] + prob_matrix[0,1] + prob_matrix[1,0] + 
                         prob_matrix[1,1] + prob_matrix[0,2] + prob_matrix[2,0]))
    
    # Calcolo GG (Entrambe segnano)
    prob_home_0 = poisson.pmf(0, home_expectancy)
    prob_away_0 = poisson.pmf(0, away_expectancy)
    gg = 100 * (1 - prob_home_0) * (1 - prob_away_0)
    
    return round(over_25, 1), round(gg, 1)

def get_advanced_analysis():
    all_data = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            res = requests.get(url).json()
            for event in res.get('events', []):
                # Analisi "Potenza": assegniamo un valore di forza dinamico 
                # basato sull'ID squadra (simulando il ranking attuale)
                h_id = int(event['competitions'][0]['competitors'][0]['id'])
                a_id = int(event['competitions'][0]['competitors'][1]['id'])
                
                # Algoritmo di aggiustamento forza (più l'ID è basso, più la squadra è "top")
                h_strength = 2.2 if h_id < 50 else 1.4
                a_strength = 1.9 if a_id < 50 else 1.2
                
                over_p, gg_p = predict_match(h_strength, a_strength)
                
                all_data.append({
                    'league': name,
                    'match': event['name'],
                    'over_p': over_p,
                    'gg_p': gg_p,
                    'score_potency': round((over_p + gg_p) / 2, 1), # Indice di "facilità" gol
                    'is_elite': over_p > 75 or gg_p > 75
                })
        except: continue
    return sorted(all_data, key=lambda x: x['score_potency'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html', matches=get_advanced_analysis())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
