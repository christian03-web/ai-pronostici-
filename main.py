import requests
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
    'Champions': 'uefa.champions', 'Europa League': 'uefa.europa', 'Conference': 'uefa.conf'
}

def calculate_dynamic_probability(event, league_name):
    try:
        comp = event['competitions'][0]
        h_team = comp['competitors'][0]
        a_team = comp['competitors'][1]
        
        # 1. Moltiplicatore di Lega (Basato su dati storici reali)
        # Bundesliga/Eredivisie = Spettacolo | Serie B/LaLiga = Più tattiche
        league_multipliers = {
            'Bundesliga': 1.45, 'Eredivisie': 1.40, 'Premier League': 1.25,
            'Serie A': 1.10, 'LaLiga': 1.05, 'Serie B': 0.90
        }
        l_mult = league_multipliers.get(league_name, 1.15)

        # 2. Forza d'Attacco e Debolezza Difensiva (basata su Rank)
        # Più il rank è basso (1, 2, 3), più la squadra è forte
        h_rank = int(h_team.get('curatedRank', {}).get('current', 10))
        a_rank = int(a_team.get('curatedRank', {}).get('current', 10))

        # Calcolo forza d'attacco (Home e Away)
        # Un rank 1 (primo in classifica) produce molta più spinta xG
        h_attack = (21 - h_rank) / 10 
        a_attack = (21 - a_rank) / 10 
        
        # 3. Calcolo xG Dinamico per questa specifica partita
        # Non più un numero fisso, ma una combinazione di lega + forza attacchi
        xg_home = (1.2 * h_attack) * l_mult
        xg_away = (1.1 * a_attack) * l_mult
        total_xg = xg_home + xg_away

        # 4. Distribuzione di Poisson per coerenza matematica
        # Calcoliamo la probabilità esatta di avere 3 o più gol (Over 2.5)
        # 
        prob_0 = poisson.pmf(0, total_xg)
        prob_1 = poisson.pmf(1, total_xg)
        prob_2 = poisson.pmf(2, total_xg)
        over_25 = round((1 - (prob_0 + prob_1 + prob_2)) * 100, 1)

        # 5. Calcolo GG (Entrambe segnano)
        # Probabilità che H segni almeno 1 E A segni almeno 1
        p_h_scores = 1 - poisson.pmf(0, xg_home)
        p_a_scores = 1 - poisson.pmf(0, xg_away)
        gg_p = round((p_h_scores * p_a_scores) * 100, 1)

        return {
            'league': league_name,
            'match': event['name'],
            'score': f"{h_team['score']} - {a_team['score']}",
            'time': event['status']['type']['shortDetail'],
            'is_live': event['status']['type']['state'] == 'in',
            'over_p': over_p,
            'gg_p': gg_p,
            'xg': round(total_xg, 2),
            'rank_info': f"Rank {h_rank} vs {a_rank}"
        }
    except:
        return None

def fetch_top_matches():
    today = datetime.now(ITALY_TZ).strftime("%Y%m%d")
    pool = []

    def process_league(item):
        name, l_id = item
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard?dates={today}"
        try:
            data = requests.get(url, timeout=3).json()
            return [calculate_dynamic_probability(e, name) for e in data.get('events', [])]
        except: return []

    with ThreadPoolExecutor(max_workers=5) as exec:
        results = exec.map(process_league, LEAGUES.items())
        for r in results:
            pool.extend([m for m in r if m])

    # Seleziona le 10 con la probabilità di Over 2.5 più ALTA per oggi
    return sorted(pool, key=lambda x: x['over_p'], reverse=True)[:10]

@app.route('/')
def index():
    return render_template('index.html', matches=fetch_top_matches())

@app.route('/api/updates')
def updates():
    return jsonify(fetch_top_matches())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
