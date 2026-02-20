import requests
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

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
    def parse_record(team):
        summary = team.get('records', [{}])[0].get('summary', '0-0-0')
        try:
            parts = summary.replace('-', ' ').split()
            w, l = int(parts[0]), int(parts[1])
            d = int(parts[2]) if len(parts) > 2 else 0
            return w, l, d
        except: return 0, 0, 0

    h_w, h_l, h_d = parse_record(home_team)
    a_w, a_l, a_d = parse_record(away_team)
    
    # Algoritmo calibrato per essere più severo
    gg_calc = 55 + (h_l * 1.3) + (a_l * 1.3) - (h_d * 4)
    over_calc = 50 + (h_w * 2.2) + (a_w * 2.2) - (h_d * 5)
    
    return round(max(10, min(96, gg_calc)), 1), round(max(10, min(96, over_calc)), 1)

@app.route('/')
def index():
    all_matches = []
    today = datetime.now().strftime('%Y%m%d')
    
    for league_name, league_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard?dates={today}"
        try:
            res = requests.get(url, timeout=5).json()
            for event in res.get('events', []):
                comp = event['competitions'][0]
                home, away = comp['competitors'][0], comp['competitors'][1]
                
                gg_prob, over_prob = get_ai_prediction(home, away)
                
                # SOGLIA DI QUALITÀ: Almeno uno dei due deve essere >= 70%
                if gg_prob >= 70 or over_prob >= 70:
                    all_matches.append({
                        'league': league_name,
                        'match_name': event['name'],
                        'home_name': home['team']['shortDisplayName'],
                        'away_name': away['team']['shortDisplayName'],
                        'logo_h': home['team'].get('logo'),
                        'logo_a': away['team'].get('logo'),
                        'score_h': home.get('score', '0'),
                        'score_a': away.get('score', '0'),
                        'clock': event['status']['type']['shortDetail'],
                        'is_live': event['status']['type']['name'] == "STATUS_IN_PROGRESS",
                        'gg': gg_prob,
                        'over': over_prob,
                        'total_quality': gg_prob + over_prob # Usato per il ranking
                    })
        except: continue
    
    # 1. Ordina per qualità decrescente
    all_matches = sorted(all_matches, key=lambda x: x['total_quality'], reverse=True)
    
    # 2. Prendi solo le prime 8 partite migliori
    top_8_matches = all_matches[:8]
    
    return render_template('index.html', predictions=top_8_matches, date=datetime.now().strftime('%d/%m/%Y'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
