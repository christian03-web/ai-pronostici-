limport requests
from flask import Flask, render_template, jsonify
from scipy.stats import poisson
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
ITALY_TZ = pytz.timezone('Europe/Rome')

# I 9 Campionati richiesti
LEAGUES = {
    'Serie A': 'ita.1', 'Serie B': 'ita.2', 'Premier League': 'eng.1',
    'Bundesliga': 'ger.1', 'Eredivisie': 'ned.1', 'LaLiga': 'esp.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Conference League': 'uefa.conf'
}

def calculate_pro_metrics(event, league_name):
    try:
        comp = event['competitions'][0]
        h_team = comp['competitors'][0]
        a_team = comp['competitors'][1]
        
        # Base xG dinamica per campionato
        league_mu = 3.1 if league_name in ['Bundesliga', 'Eredivisie'] else 2.6
        
        # Calcolo forza relativa basata su Ranking o ID (xG stimato)
        h_rank = int(h_team.get('curatedRank', {}).get('current', 10))
        a_rank = int(a_team.get('curatedRank', {}).get('current', 10))
        
        # Simulazione xG (Expected Goals)
        total_xg = round(league_mu + ((20 - h_rank) + (20 - a_rank)) / 40, 2)
        
        # Poisson per Over 2.5
        prob_over = round((1 - sum([poisson.pmf(i, total_xg) for i in range(3)])) * 100, 1)
        
        # Calcolo GG (Entrambe segnano)
        # Basato sulla probabilità che ogni squadra segni almeno 1 gol
        p_h = 1 - poisson.pmf(0, total_xg * 0.52)
        p_a = 1 - poisson.pmf(0, total_xg * 0.48)
        gg_p = round((p_h * p_a) * 100, 1)
        
        return {
            'over_p': over_p,
            'gg_p': gg_p,
            'xg': total_xg,
            'h_rank': h_rank if h_rank < 25 else '-',
            'a_rank': a_rank if a_rank < 25 else '-',
            'urgency': "ALTA" if abs(h_rank - a_rank) < 5 else "MEDIA"
        }
    except:
        return {'over_p': 50.0, 'gg_p': 50.0, 'xg': 2.5, 'h_rank': '-', 'a_rank': '-', 'urgency': 'N/D'}

def get_soccer_data():
    all_matches = []
    # Prendiamo oggi e domani per evitare problemi di fuso orario
    now_it = datetime.now(ITALY_TZ)
    today_str = now_it.strftime("%Y%m%d")
    
    for name, l_id in LEAGUES.items():
        # URL senza restrizione eccessiva di data per debugging
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard?dates={today_str}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            data = r.json()
            
            for event in data.get('events', []):
                # Escludiamo i match finiti da tempo
                if event['status']['type']['state'] == 'post' and "FT" in event['status']['type']['shortDetail']:
                    continue
                
                comp = event['competitions'][0]
                m = calculate_pro_metrics(event, name)
                
                all_matches.append({
                    'league': name,
                    'match': event['name'],
                    'score': f"{comp['competitors'][0]['score']} - {comp['competitors'][1]['score']}",
                    'time': event['status']['type']['shortDetail'],
                    'is_live': event['status']['type']['state'] == 'in',
                    **m
                })
        except:
            continue
    return all_matches

@app.route('/')
def index():
    matches = get_soccer_data()
    return render_template('index.html', matches=matches)

@app.route('/api/updates')
def updates():
    return jsonify(get_soccer_data())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
