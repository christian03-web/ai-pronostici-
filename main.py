import requests
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

# Configurazione estesa dei campionati e tornei
LEAGUES = {
    'Champions League': 'uefa.champions',
    'Europa League': 'uefa.europa',
    'Serie A': 'ita.1',
    'Premier League': 'eng.1',
    'La Liga': 'esp.1',
    'Bundesliga': 'ger.1',
    'Ligue 1': 'fra.1',
    'Eredivisie': 'ned.1',
    'Primeira Liga': 'por.1'
}

def get_ai_prediction(home_team, away_team):
    # Estrazione record: Vittorie (W), Pareggi (D), Sconfitte (L)
    def parse_record(team):
        summary = team.get('records', [{}])[0].get('summary', '0-0-0')
        try:
            w, l, d = map(int, summary.replace('-', ' ').split())
            return w, l, d
        except: return 0, 0, 0

    h_w, h_l, h_d = parse_record(home_team)
    a_w, a_l, a_d = parse_record(away_team)

    # Logica Potenziata
    # GG (Entrambe segnano): aumenta se entrambe hanno pochi pareggi (giocano per vincere)
    # o se hanno statistiche di sconfitte alte (difese deboli)
    gg_calc = 52 + (h_l * 1.5) + (a_l * 1.5) - (h_d * 2)
    
    # Over 2.5: aumenta con la differenza di forza e lo storico vittorie
    over_calc = 48 + (h_w * 2) + (a_w * 2) - (h_d * 3)

    # Normalizzazione range 10% - 96%
    gg_final = max(10, min(96, gg_calc))
    over_final = max(10, min(96, over_calc))

    return round(gg_final, 1), round(over_final, 1)

@app.route('/')
def index():
    all_matches = []
    # Otteniamo la data di oggi nel formato YYYYMMDD richiesto da ESPN
    today = datetime.now().strftime('%Y%m%d')
    
    for league_name, league_id in LEAGUES.items():
        # URL con parametro data per forzare i match del giorno
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard?dates={today}"
        
        try:
            res = requests.get(url, timeout=5).json()
            events = res.get('events', [])
            
            for event in events:
                comp = event['competitions'][0]
                # Saltiamo i match non ancora definiti o senza squadre
                if len(comp['competitors']) < 2: continue
                
                home = comp['competitors'][0]
                away = comp['competitors'][1]
                
                gg_prob, over_prob = get_ai_prediction(home, away)
                
                all_matches.append({
                    'league': league_name,
                    'match': event['name'],
                    'time': event['status']['type']['shortDetail'],
                    'gg': gg_prob,
                    'over': over_prob,
                    'logo_h': home['team'].get('logo'),
                    'logo_a': away['team'].get('logo'),
                    'home_name': home['team']['shortDisplayName'],
                    'away_name': away['team']['shortDisplayName']
                })
        except Exception as e:
            print(f"Errore su {league_name}: {e}")
            continue
    
    # Ordiniamo per le partite con più probabilità di successo (Over 2.5 + GG)
    all_matches = sorted(all_matches, key=lambda x: (x['over'] + x['gg']), reverse=True)
    
    return render_template('index.html', predictions=all_matches, date=datetime.now().strftime('%d/%m/%Y'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
