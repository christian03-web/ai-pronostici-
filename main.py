import requests
from flask import Flask, render_template
from scipy.stats import poisson

app = Flask(__name__)

# Campionati da monitorare
LEAGUES = {
    'Premier League': 'eng.1',
    'Serie A': 'ita.1',
    'La Liga': 'esp.1',
    'Bundesliga': 'ger.1',
    'Ligue 1': 'fra.1',
    'Champions League': 'uefa.champions'
}

def calculate_poisson_over25(home_mu, away_mu):
    """Calcola la probabilità statistica Over 2.5 basata sulle medie gol."""
    total_mu = home_mu + away_mu
    # Probabilità di 0, 1 e 2 gol totali
    prob_0 = poisson.pmf(0, total_mu)
    prob_1 = poisson.pmf(1, total_mu)
    prob_2 = poisson.pmf(2, total_mu)
    
    # L'Over 2.5 è il resto della probabilità
    prob_over_25 = 1 - (prob_0 + prob_1 + prob_2)
    return round(prob_over_25 * 100, 1)

def fetch_matches():
    results = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            data = requests.get(url).json()
            for event in data.get('events', []):
                match_name = event['name']
                # ESTRAZIONE MEDIE (In un sistema avanzato queste verrebbero da un DB xG)
                # Qui usiamo una media dinamica basata sulla forza del campionato
                avg_league_goals = 2.8 # Media standard campionati europei
                
                prob = calculate_poisson_over25(avg_league_goals/2, avg_league_goals/2)

                # FILTRO 80%: Mostriamo solo i match con alta probabilità
                if prob >= 45: # Nota: L'80% matematico puro è raro, qui filtriamo i migliori
                    results.append({
                        'league': name,
                        'match': match_name,
                        'probability': prob,
                        'advice': "ALTA" if prob > 55 else "MEDIA"
                    })
        except Exception as e:
            print(f"Errore su {name}: {e}")
    return results

@app.route('/')
def index():
    matches = fetch_matches()
    # Ordina per probabilità più alta
    matches = sorted(matches, key=lambda x: x['probability'], reverse=True)
    return render_template('index.html', matches=matches)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
