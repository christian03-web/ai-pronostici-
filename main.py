import requests
from flask import Flask, render_template
from scipy.stats import poisson
from datetime import datetime

app = Flask(__name__)

# Usiamo i campionati che giocano di più per garantire le 8 partite
LEAGUES = {
    'Serie A': 'ita.1', 'Premier League': 'eng.1', 
    'La Liga': 'esp.1', 'Bundesliga': 'ger.1', 
    'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions': 'uefa.champions', 'Europa': 'uefa.europa'
}

def calculate_simple_prob(h_id, a_id):
    # Logica veloce senza chiamate esterne extra
    mu = 2.9 + ((int(h_id) % 5 + int(a_id) % 5) / 10)
    prob = (1 - (poisson.pmf(0, mu) + poisson.pmf(1, mu) + poisson.pmf(2, mu))) * 100
    return round(prob, 1)

@app.route('/')
def index():
    all_matches = []
    today = datetime.now().strftime("%d/%m/%Y")
    
    # Sessione di richiesta con timeout globale
    session = requests.Session()
    
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            # Timeout molto basso per evitare il crash su Railway
            resp = session.get(url, timeout=2).json()
            for event in resp.get('events', []):
                competitors = event['competitions'][0]['competitors']
                h_team = competitors[0]
                a_team = competitors[1]
                
                prob = calculate_simple_prob(h_team['id'], a_team['id'])
                
                all_matches.append({
                    'league': name,
                    'match': event['name'],
                    'time': event['status']['type']['shortDetail'],
                    'prob': prob
                })
        except:
            continue # Se una lega fallisce, passa alla prossima senza crashare
    
    # Prende le migliori 8, se ce ne sono meno prende quelle disponibili
    slip = sorted(all_matches, key=lambda x: x['prob'], reverse=True)[:8]
    
    return render_template('index.html', slip=slip, date=today)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
