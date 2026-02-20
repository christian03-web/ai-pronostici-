import requests
from flask import Flask, render_template

app = Flask(__name__)

# Configurazione Leghe da monitorare
LEAGUES = {
    'Serie A': 'ita.1',
    'Premier League': 'eng.1',
    'La Liga': 'esp.1',
    'Bundesliga': 'ger.1',
    'Ligue 1': 'fra.1'
}

def analyze_match(event):
    competition = event['competitions'][0]
    home_team = competition['competitors'][0]
    away_team = competition['competitors'][1]
    
    # Estrazione dati base
    home_name = home_team['team']['displayName']
    away_name = away_team['team']['displayName']
    
    # In un'app reale, qui chiameresti un'altra API per xG e Formazioni.
    # Usiamo i dati di classifica e record attuali per simulare l'intelligenza.
    home_rank = int(home_team.get('curatedRank', {}).get('current', 50))
    away_rank = int(away_team.get('curatedRank', {}).get('current', 50))
    
    # Logica di analisi (Esempio semplificato)
    # Calcoliamo uno score basato sulla distanza in classifica e motivazione
    rank_diff = abs(home_rank - away_rank)
    
    # Simulazione calcolo Over 2.5 e GG
    # Se la differenza di ranking è bassa e sono squadre d'alta classifica -> Probabile GG
    is_gg = rank_diff < 5 or (home_rank < 10 and away_rank < 10)
    # Se la differenza è alta -> Probabile Over 2.5 (una squadra domina l'altra)
    is_over = rank_diff > 8
    
    return {
        'match': f"{home_name} vs {away_name}",
        'home_rank': home_rank,
        'away_rank': away_rank,
        'gg_prob': "ALTA" if is_gg else "MEDIA",
        'over_prob': "ALTA" if is_over else "MEDIA",
        'status': event['status']['type']['description']
    }

@app.route('/')
def index():
    all_predictions = []
    
    for league_name, league_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard"
        try:
            response = requests.get(url).json()
            events = response.get('events', [])
            for event in events:
                analysis = analyze_match(event)
                analysis['league'] = league_name
                all_predictions.append(analysis)
        except:
            continue
            
    return render_template('index.html', predictions=all_predictions)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
