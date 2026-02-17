import requests
from flask import Flask, render_template
from scipy.stats import poisson

app = Flask(__name__)

# Campionati Top
LEAGUES = {
    'Premier League': 'eng.1', 'Serie A': 'ita.1', 'La Liga': 'esp.1',
    'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Eredivisie': 'ned.1',
    'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa',
    'Serie B': 'ita.2'
}

def calculate_advanced_logic(h_id, a_id, l_name):
    # Generiamo un peso basato sulla lega e sugli ID per varianza reale
    league_mu = 3.2 if l_name in ['Bundesliga', 'Eredivisie'] else 2.7
    
    # Algoritmo di varianza basato sugli ID delle squadre (Simula la forza Ranking)
    strength_mod = ((int(h_id) % 10) + (int(a_id) % 10)) / 20
    final_mu = league_mu + strength_mod
    
    # Poisson per Over 2.5
    prob_over = (1 - (poisson.pmf(0, final_mu) + poisson.pmf(1, final_mu) + poisson.pmf(2, final_mu))) * 100
    # Poisson per GG
    prob_gg = (1 - poisson.pmf(0, final_mu/1.7)) * (1 - poisson.pmf(0, final_mu/1.7)) * 100
    
    return round(prob_over, 1), round(gg_p := prob_gg, 1)

@app.route('/')
def index():
    all_results = []
    for name, l_id in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{l_id}/scoreboard"
        try:
            resp = requests.get(url, timeout=5).json()
            for event in resp.get('events', []):
                competitors = event['competitions'][0]['competitors']
                h_team = competitors[0]
                a_team = competitors[1]
                
                over_p, gg_p = calculate_advanced_logic(h_team['id'], a_team['id'], name)
                
                all_results.append({
                    'league': name,
                    'match': event['name'],
                    'status': event['status']['type']['shortDetail'],
                    'over_p': over_p,
                    'gg_p': gg_p,
                    'is_gold': over_p > 68 or gg_p > 70
                })
        except Exception as e:
            print(f"Errore su {name}: {e}")
            continue
    
    # Ordina per le probabilità più alte
    all_results = sorted(all_results, key=lambda x: x['over_p'], reverse=True)
    return render_template('index.html', matches=all_results)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
