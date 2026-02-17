limport requests
from flask import Flask, render_template
from scipy.stats import poisson
from datetime import datetime

app = Flask(__name__)

LEAGUES = {
    'Premier League': 'eng.1', 'Serie A': 'ita.1', 'La Liga': 'esp.1',
    'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf', 'Serie B': 'ita.2', 'Portogallo': 'por.1'
}

def calculate_over_prob(h_id, a_id, l_name):
    # Base mu più alta per campionati spettacolari
    base_mu = 3.3 if l_name in ['Bundesliga', 'Eredivisie', 'Champions League'] else 2.8
    # Varianza basata su ID per personalizzare il match
    mod = ((int(h_id) % 10) + (int(a_id) % 10)) / 20
    mu = base_mu + mod
    
    # Probabilità Poisson per Over 2.5
    prob = (1 - (poisson.pmf(0, mu) + poisson.pmf(1, mu) + poisson.pmf(2, mu))) * 100
    return round(prob, 1)

@app.route('/')
def index():
    all_matches = []
    today = datetime.now().strftime("%d/%m/%Y")
    
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            resp = requests.get(url, timeout=5).json()
            for event in resp.get('events', []):
                h_team = event['competitions'][0]['competitors'][0]
                a_team = event['competitions'][0]['competitors'][1]
                
                prob = calculate_over_prob(h_team['id'], a_team['id'], name)
                
                all_matches.append({
                    'league': name,
                    'match': event['name'],
                    'time': event['status']['type']['shortDetail'],
                    'prob': prob
                })
        except: continue
    
    # SELEZIONE DELLE 8 MIGLIORI (LA SCHEDINA)
    # Ordiniamo per probabilità decrescente e prendiamo le prime 8
    betting_slip = sorted(all_matches, key=lambda x: x['prob'], reverse=True)[:8]
    
    return render_template('index.html', slip=betting_slip, date=today)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
