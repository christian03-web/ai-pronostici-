import requests
from flask import Flask, render_template, jsonify
from scipy.stats import poisson
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
ITALY_TZ = pytz.timezone('Europe/Rome')

# Campionati monitorati
LEAGUES = {
    'Serie A': 'ita.1', 'Serie B': 'ita.2', 'Premier League': 'eng.1',
    'Bundesliga': 'ger.1', 'Eredivisie': 'ned.1', 'LaLiga': 'esp.1',
    'Champions': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference': 'uefa.conf'
}

def analyze_match(event, league_name):
    try:
        comp = event['competitions'][0]
        h_team = comp['competitors'][0]
        a_team = comp['competitors'][1]
        
        # Parametri statistici
        league_mu = 3.3 if league_name in ['Bundesliga', 'Eredivisie'] else 2.7
        h_rank = int(h_team.get('curatedRank', {}).get('current', 10))
        a_rank = int(a_team.get('curatedRank', {}).get('current', 10))
        
        # Calcolo xG (Expected Goals) dinamico
        total_xg = round(league_mu + ((20 - h_rank) + (20 - a_rank)) / 50, 2)
        
        # Probabilità Over 2.5 (Poisson)
        over_p = round((1 - sum([poisson.pmf(i, total_xg) for i in range(3)])) * 100, 1)
        # Probabilità GG (Goal/Goal)
        p_h = 1 - poisson.pmf(0, total_xg * 0.52)
        p_a = 1 - poisson.pmf(0, total_xg * 0.48)
        gg_p = round((p_h * p_a) * 100, 1)
        
        # Punteggio di affidabilità (media delle due probabilità)
        confidence = (over_p + gg_p) / 2

        return {
            'league': league_name, 'match': event['name'],
            'score': f"{h_team['score']} - {a_team['score']}",
            'time': event['status']['type']['shortDetail'],
            'is_live': event['status']['type']['state'] == 'in',
            'over_p': over_p, 'gg_p': gg_p, 'xg': total_xg,
            'confidence': confidence
        }
    except: return None

def fetch_data():
    today = datetime.now(ITALY_TZ).strftime("%Y%m%d")
    all_potential = []
    
    def get_league(item):
        name, l_id = item
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard?dates={today}"
        try:
            r = requests.get(url, timeout=3).json()
            return [analyze_match(e, name) for e in r.get('events', [])]
        except: return []

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(get_league, LEAGUES.items())
        for res in results:
            all_potential.extend([m for m in res if m])

    # FILTRO POTENTE: Ordina per probabilità e prendi solo le prime 10
    top_10 = sorted(all_potential, key=lambda x: x['confidence'], reverse=True)[:10]
    return top_10

@app.route('/')
def index():
    return render_template('index.html', matches=fetch_data())

@app.route('/api/updates')
def updates():
    return jsonify(fetch_data())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
