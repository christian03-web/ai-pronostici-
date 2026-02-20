import requests
from flask import Flask, render_template, jsonify
from scipy.stats import poisson

app = Flask(__name__)

LEAGUES = {
    'Premier League': 'eng.1', 'Serie A': 'ita.1', 'La Liga': 'esp.1',
    'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf', 'Serie B': 'ita.2'
}

def calculate_logic(h_id, a_id, l_name):
    league_mu = 3.2 if l_name in ['Bundesliga', 'Eredivisie'] else 2.7
    seed = (int(h_id) + int(a_id)) % 100
    final_mu = league_mu + (seed / 100) - 0.5
    
    prob_over = (1 - (poisson.pmf(0, final_mu) + poisson.pmf(1, final_mu) + poisson.pmf(2, final_mu))) * 100
    prob_gg = (1 - poisson.pmf(0, final_mu/1.7)) * (1 - poisson.pmf(0, final_mu/1.7)) * 100
    return round(prob_over, 1), round(prob_gg, 1)

def get_live_data():
    all_results = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            resp = requests.get(url, timeout=5).json()
            for event in resp.get('events', []):
                comp = event['competitions'][0]
                h_team = comp['competitors'][0]
                a_team = comp['competitors'][1]
                
                over_p, gg_p = calculate_logic(h_team['id'], a_team['id'], name)
                
                all_results.append({
                    'league': name,
                    'match': event['name'],
                    'score': comp['competitors'][0]['score'] + " - " + comp['competitors'][1]['score'],
                    'time': event['status']['type']['shortDetail'],
                    'over_p': over_p,
                    'gg_p': gg_p,
                    'is_live': event['status']['type']['state'] == 'in'
                })
        except: continue
    return all_results

@app.route('/')
def index():
    return render_template('index.html', matches=get_live_data())

@app.route('/api/updates')
def updates():
    return jsonify(get_live_data())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
