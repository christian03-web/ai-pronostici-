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
    
    gg_calc = 55 + (h_l * 1.2) + (a_l * 1.2) - (h_d * 3)
    over_calc = 50 + (h_w * 2.1) + (a_w * 2.1) - (h_d * 4)
    
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
                home = comp['competitors'][0]
                away = comp['competitors'][1]
                
                # DATI LIVE
                score_h = home.get('score', '0')
                score_a = away.get('score', '0')
                status_type = event['status']['type']['name'] # es: STATUS_IN_PROGRESS, STATUS_FINAL
                live_clock = event['status']['type']['shortDetail'] # es: "72'", "HT", "21:00"
                
                is_live = status_type == "STATUS_IN_PROGRESS"
                
                gg_prob, over_prob = get_ai_prediction(home, away)
                
                all_matches.append({
                    'league': league_name,
                    'match_name': event['name'],
                    'home_name': home['team']['shortDisplayName'],
                    'away_name': away['team']['shortDisplayName'],
                    'logo_h': home['team'].get('logo'),
                    'logo_a': away['team'].get('logo'),
                    'score_h': score_h,
                    'score_a': score_a,
                    'clock': live_clock,
                    'is_live': is_live,
                    'is_final': status_type == "STATUS_FINAL",
                    'gg': gg_prob,
                    'over': over_prob
                })
        except: continue
    
    return render_template('index.html', predictions=all_matches, date=datetime.now().strftime('%d/%m/%Y'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
