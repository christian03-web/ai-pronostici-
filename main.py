import requests
from flask import Flask, render_template

app = Flask(__name__)

# Configurazione Leghe con Media Gol stimata (per calcolo Over)
LEAGUES = {
    'Serie A': {'id': 'ita.1', 'avg_goals': 2.6},
    'Premier League': {'id': 'eng.1', 'avg_goals': 2.8},
    'La Liga': {'id': 'esp.1', 'avg_goals': 2.5},
    'Bundesliga': {'id': 'ger.1', 'avg_goals': 3.1},
    'Ligue 1': {'id': 'fra.1', 'avg_goals': 2.7}
}

def calculate_probability(home_team, away_team, league_avg):
    # Estraiamo i record (Vinte/Pareggiate/Perse) per capire la mentalità
    def get_stats(team):
        record = team.get('records', [{}])[0].get('summary', '0-0-0')
        parts = record.split('-')
        wins = int(parts[0]) if len(parts) > 0 else 0
        losses = int(parts[1]) if len(parts) > 1 else 0
        return wins, losses

    h_w, h_l = get_stats(home_team)
    a_w, a_l = get_stats(away_team)

    # ALGORITMO DI VALUTAZIONE
    # 1. Base GG: Se entrambe segnano spesso o hanno difese deboli
    gg_base = 50 + (league_avg * 2) 
    if h_l > h_w: gg_base += 10  # Difesa casa debole
    if a_l > a_w: gg_base += 10  # Difesa trasferta debole
    gg_perc = min(94, gg_base) # Cap a 94% (la certezza assoluta non esiste)

    # 2. Base Over 2.5: Basato sulla propensione offensiva
    over_base = 45 + (league_avg * 5)
    if h_w > h_l and a_w > a_l: over_base += 15 # Due squadre d'attacco
    over_perc = min(92, over_base)

    return round(gg_perc, 2), round(over_perc, 2)

@app.route('/')
def index():
    predictions = []
    for name, data in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{data['id']}/scoreboard"
        try:
            res = requests.get(url).json()
            for event in res.get('events', []):
                comp = event['competitions'][0]
                home = comp['competitors'][0]
                away = comp['competitors'][1]
                
                gg, over = calculate_probability(home, away, data['avg_goals'])
                
                # Filtro di potenza: mostriamo solo se una delle due è > 75%
                if gg > 75 or over > 75:
                    predictions.append({
                        'league': name,
                        'match': event['name'],
                        'gg': gg,
                        'over': over,
                        'logo_h': home['team']['logo'],
                        'logo_a': away['team']['logo']
                    })
        except: continue
    
    # Ordina per la probabilità più alta
    predictions = sorted(predictions, key=lambda x: max(x['gg'], x['over']), reverse=True)
    return render_template('index.html', predictions=predictions)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
