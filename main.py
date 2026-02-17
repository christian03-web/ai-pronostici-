import requests
from flask import Flask, render_template
from scipy.stats import poisson
from datetime import datetime
import pytz

app = Flask(__name__)

# Configurazione fuso orario Italiano
italy_tz = pytz.timezone('Europe/Rome')

LEAGUES = {
    'Serie A': 'ita.1', 'Premier League': 'eng.1', 
    'La Liga': 'esp.1', 'Bundesliga': 'ger.1', 
    'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions': 'uefa.champions', 'Europa': 'uefa.europa',
    'Conference': 'uefa.conf', 'Serie B': 'ita.2'
}

def calculate_simple_prob(h_id, a_id):
    mu = 2.9 + ((int(h_id) % 5 + int(a_id) % 5) / 10)
    prob = (1 - (poisson.pmf(0, mu) + poisson.pmf(1, mu) + poisson.pmf(2, mu))) * 100
    return round(prob, 1)

@app.route('/')
def index():
    all_matches = []
    # Data odierna in formato YYYYMMDD per l'API e DD/MM/YYYY per la visualizzazione
    now_italy = datetime.now(italy_tz)
    today_api = now_italy.strftime("%Y%m%d")
    today_display = now_italy.strftime("%d/%m/%Y")
    
    session = requests.Session()
    
    for name, l_id in LEAGUES.items():
        # Aggiungiamo il parametro ?dates= per forzare ESPN a darci solo oggi
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard?dates={today_api}"
        try:
            resp = session.get(url, timeout=3).json()
            for event in resp.get('events', []):
                status = event['status']['type']['state']
                
                # FILTRO: Escludiamo le partite già terminate (post)
                if status == 'post':
                    continue
                
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
            continue
    
    # Prende le migliori 8 partite del giorno
    slip = sorted(all_matches, key=lambda x: x['prob'], reverse=True)[:8]
    
    return render_template('index.html', slip=slip, date=today_display)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
