limport requests
from flask import Flask, render_template, jsonify
from scipy.stats import poisson
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
ITALY_TZ = pytz.timezone('Europe/Rome')

LEAGUES = {
    'Serie A': 'ita.1', 'Serie B': 'ita.2', 'Premier League': 'eng.1',
    'Bundesliga': 'ger.1', 'Eredivisie': 'ned.1', 'LaLiga': 'esp.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf'
}

def calculate_metrics(event, league_name):
    try:
        comp = event['competitions'][0]
        h_team = comp['competitors'][0]
        a_team = comp['competitors'][1]
        
        # Logica xG basata su League Mu e Ranking
        mu = 3.2 if league_name in ['Bundesliga', 'Eredivisie'] else 2.7
        h_rank = int(h_team.get('curatedRank', {}).get('current', 10))
        a_rank = int(a_team.get('curatedRank', {}).get('current', 10))
        
        # Calcolo Expected Goals (xG)
        total_xg = round(mu + ((20 - h_rank) + (20 - a_rank)) / 50, 2)
        
        # Poisson Over 2.5
        over_p = round((1 - sum([poisson.pmf(i, total_xg) for i in range(3)])) * 100, 1)
        # GG (Goal/Goal)
        gg_p = round(((1 - poisson.pmf(0, total_xg * 0.5)) * (1 - poisson.pmf(0, total_xg * 0.5))) * 100, 1)
        
        return {
            'league': league_name, 'match': event['name'],
            'score': f"{h_team['score']} - {a_team['score']}",
            'time': event['status']['type']['shortDetail'],
            'is_live': event['status']['type']['state'] == 'in',
            'over_p': over_p, 'gg_p': gg_p, 'xg': total_xg,
            'h_rank': h_rank if h_rank < 21 else '-', 'a_rank': a_rank if a_rank < 21 else '-'
        }
    except: return None

def fetch_league_data(league_item):
    name, l_id = league_item
    today = datetime.now(ITALY_TZ).strftime("%Y%m%d")
    url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard?dates={today}"
    try:
        r = requests.get(url, timeout=3)
        events = r.json().get('events', [])
        return [calculate_metrics(e, name) for e in events if e['status']['type']['state'] != 'post']
    except: return []

@app.route('/')
def index():
    # Esecuzione in parallelo per evitare il crash per timeout
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_league_data, LEAGUES.items())
    
    all_matches = [m for sublist in results for m in sublist if m]
    return render_template('index.html', matches=all_matches)

@app.route('/api/updates')
def updates():
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_league_data, LEAGUES.items())
    return jsonify([m for sublist in results for m in sublist if m])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
