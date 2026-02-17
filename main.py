import requests
from flask import Flask, render_template
from scipy.stats import poisson

app = Flask(__name__)

LEAGUES = {
    'Premier League': 'eng.1',
    'Serie A': 'ita.1',
    'La Liga': 'esp.1',
    'Bundesliga': 'ger.1',
    'Ligue 1': 'fra.1',
    'Champions League': 'uefa.champions'
}

def calculate_over25(mu):
    # Distribuzione di Poisson per calcolare probabilità cumulata > 2.5
    prob_0 = poisson.pmf(0, mu)
    prob_1 = poisson.pmf(1, mu)
    prob_2 = poisson.pmf(2, mu)
    return (1 - (prob_0 + prob_1 + prob_2)) * 100

def fetch_data():
    matches = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            data = requests.get(url).json()
            for event in data.get('events', []):
                # Simuliamo un calcolo basato sulla forza offensiva del campionato
                # Bundesliga e Olanda hanno medie più alte (mu = 3.2), Serie A (mu = 2.6)
                league_mu = 3.2 if name in ['Bundesliga', 'Premier League'] else 2.7
                
                # Aggiungiamo varianza per distinguere le partite
                match_id_sum = sum(int(digit) for digit in event['id'] if digit.isdigit())
                dynamic_mu = league_mu + (match_id_sum % 10 / 10) - 0.5
                
                prob = round(calculate_over25(dynamic_mu), 1)

                # FILTRO SEVERO: Mostriamo solo se la probabilità è alta
                if prob > 50: 
                    matches.append({
                        'league': name,
                        'match': event['name'],
                        'probability': prob,
                        # Se supera il 65% (raro e difficile), lo marchiamo come TOP
                        'is_gold': prob >= 65 
                    })
        except:
            continue
    # Ordina per le partite più "facili" (probabilità maggiore)
    return sorted(matches, key=lambda x: x['probability'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html', matches=fetch_data())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
