import requests
from flask import Flask, render_template, jsonify
from scipy.stats import poisson
from datetime import datetime, timedelta
import pytz
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
ITALY_TZ = pytz.timezone('Europe/Rome')

LEAGUES = {
    'Serie A': 'ita.1', 'Serie B': 'ita.2', 'Premier League': 'eng.1',
    'Bundesliga': 'ger.1', 'Eredivisie': 'ned.1', 'LaLiga': 'esp.1',
    'Champions': 'uefa.champions', 'Europa League': 'uefa.europa', 'Conference': 'uefa.conf'
}

def calculate_dynamic_probability(event, league_name):
    try:
        comp = event['competitions'][0]
        h_team = comp['competitors'][0]
        a_team = comp['competitors'][1]
        
        # Pesi campionati
        league_multipliers = {'Bundesliga': 1.4, 'Eredivisie': 1.35, 'Premier League': 1.2, 'Serie A': 1.1, 'LaLiga': 1.05, 'Serie B': 0.85}
        l_mult = league_multipliers.get(league_name, 1.1)

        h_rank = int(h_team.get('curatedRank', {}).get('current', 12))
        a_rank = int(a_team.get('curatedRank', {}).get('current', 13))

        # Calcolo xG specifico per i due team
        xg_h = ((21 - h_rank) / 8) * l_mult
        xg_a = ((21 - a_rank) / 9) * l_mult
        total_xg = max(1.5, xg_h + xg_a) # Minimo garantito per evitare prob. 0

        # Poisson Over 2.5
        over_p = round((1 - sum([poisson.pmf(i, total_xg) for i in range(3)])) * 100, 1)
        # Poisson GG
        gg_p = round(((1 - poisson.pmf(0, xg_h)) * (1 - poisson.pmf(0, xg_a))) * 100, 1)

        return {
            'league': league_name,
            'match': event['name'],
            'score': f"{h_team['score']} - {a_team['score']}",
            'time': event['status']['type']['shortDetail'],
            'is_live': event['status']['type']['state'] == 'in',
            'over_p': over_p,
            'gg_p': gg_p,
            'xg': round(total_xg, 2),
            'confidence': (over_p + gg_p) / 2
        }
    except: return None

def fetch_all_matches():
    today = datetime.now(ITALY_TZ).strftime("%Y%m%d")
    tomorrow = (datetime.now(ITALY_TZ) + timedelta(days=1)).strftime("%Y%m%d")
    pool = []

    def get_league(item):
        name, l_id = item
        # Cerchiamo sia oggi che domani per coprire i match serali/notturni
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard?dates={today}-{tomorrow}"
        try:
            r = requests.get(url, timeout=4).json()
            return [calculate_dynamic_probability(e, name) for e in r.get('events', [])]
        except: return []

    with ThreadPoolExecutor(max_workers=5) as exec:
        results = exec.map(get_league, LEAGUES.items())
        for r in results:
            pool.extend([m for m in r if m])

    # Ordiniamo: Prima i LIVE, poi i più probabili
    return sorted(pool, key=lambda x: (x['is_live'], x['confidence']), reverse=True)[:15]

@app.route('/')
def index():
    matches = fetch_all_matches()
    return render_template('index.html', matches=matches)

@app.route('/api/updates')
def updates():
    return jsonify(fetch_all_matches())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
