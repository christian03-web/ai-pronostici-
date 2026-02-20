import requests
from flask import Flask, render_template, jsonify
from scipy.stats import poisson
from datetime import datetime
import pytz

app = Flask(__name__)
ITALY_TZ = pytz.timezone('Europe/Rome')

# Configurazione completa dei campionati richiesti
LEAGUES = {
    'Serie A': 'ita.1',
    'Serie B': 'ita.2',
    'Premier League': 'eng.1',
    'Bundesliga': 'ger.1',
    'Eredivisie': 'ned.1',
    'LaLiga': 'esp.1',
    'Champions League': 'uefa.champions',
    'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf'
}

def calculate_professional_metrics(event, league_name):
    comp = event['competitions'][0]
    h_team = comp['competitors'][0]
    a_team = comp['competitors'][1]
    
    # Parametri di Lega per xG (Expected Goals)
    # Bundesliga ed Eredivisie hanno xG storici più alti
    league_modifier = 1.2 if league_name in ['Bundesliga', 'Eredivisie'] else 1.0
    
    # Simulazione xG basata su Ranking e Forza Attacco/Difesa
    # Recuperiamo il "Form" o Ranking se disponibile nell'API
    h_rank = int(h_team.get('curatedRank', {}).get('current', 10))
    a_rank = int(a_team.get('curatedRank', {}).get('current', 11))
    
    # Algoritmo xG: Base + Bonus Posizione + Bonus Lega
    xg_base = 1.35 * league_modifier
    h_xg = xg_base + (0.05 * (20 - h_rank))
    a_xg = xg_base + (0.05 * (20 - a_rank))
    total_xg = round(h_xg + a_xg, 2)
    
    # Calcolo Probabilità Over 2.5 (Distribuzione di Poisson)
    prob_0 = poisson.pmf(0, total_xg)
    prob_1 = poisson.pmf(1, total_xg)
    prob_2 = poisson.pmf(2, total_xg)
    over_25 = round((1 - (prob_0 + prob_1 + prob_2)) * 100, 1)
    
    # Calcolo Probabilità GG (Entrambe segnano)
    prob_h_score = 1 - poisson.pmf(0, h_xg)
    prob_a_score = 1 - poisson.pmf(0, a_xg)
    gg_p = round((prob_h_score * prob_a_score) * 100, 1)
    
    # Analisi Punti e Urgenza (Distanza in classifica)
    rank_diff = abs(h_rank - a_rank)
    status_label = "SCONTRO DIRETTO" if rank_diff < 4 else "TEST CODA-TESTA"
    
    return {
        'over_p': over_p,
        'gg_p': gg_p,
        'xg': total_xg,
        'h_rank': h_rank if h_rank < 25 else '-',
        'a_rank': a_rank if a_rank < 25 else '-',
        'status': status_label
    }

def fetch_daily_intelligence():
    all_matches = []
    today_str = datetime.now(ITALY_TZ).strftime("%Y%m%d")
    
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard?dates={today_str}"
        try:
            resp = requests.get(url, timeout=4).json()
            for event in resp.get('events', []):
                # Filtro: solo match di oggi (escludiamo quelli finiti ieri)
                if event['status']['type']['state'] == 'post' and "FT" in event['status']['type']['shortDetail']:
                    continue
                
                metrics = calculate_professional_metrics(event, name)
                comp = event['competitions'][0]
                
                all_matches.append({
                    'league': name,
                    'match': event['name'],
                    'score': f"{comp['competitors'][0]['score']} - {comp['competitors'][1]['score']}",
                    'time': event['status']['type']['shortDetail'],
                    'is_live': event['status']['type']['state'] == 'in',
                    **metrics
                })
        except: continue
    return all_matches

@app.route('/')
def index():
    return render_template('index.html', matches=fetch_daily_intelligence())

@app.route('/api/updates')
def updates():
    return jsonify(fetch_daily_intelligence())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
