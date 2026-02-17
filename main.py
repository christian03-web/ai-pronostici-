from flask import Flask, render_template
import requests
import math
def poisson_over25(home_xg, away_xg):
    lam = home_xg + away_xg
    prob = 1 - (math.exp(-lam) * (1 + lam + (lam**2)/2))
    return round(prob * 100, 1)
app = Flask(__name__)

LEAGUES = {
    "Serie A": "ita.1",
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Bundesliga": "ger.1",
    "Ligue 1": "fra.1",
    "Champions League": "uefa.champions",
    "Europa League": "uefa.europa",
    "Conference League": "uefa.europa.conf"
}

def get_matches():
    matches = []

    for league_name, league in LEAGUES.items():
        url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
        try:
            data = requests.get(url).json()

            for event in data["events"]:
                comp = event["competitions"][0]
                teams = comp["competitors"]

                home = teams[0]["team"]["displayName"]
                away = teams[1]["team"]["displayName"]

                home_score = teams[0].get("score", "0")
                away_score = teams[1].get("score", "0")

                status = comp["status"]["type"]["state"]
if status != "pre":
    continue
                prediction = "⚖️ Normale"
                if status != "Scheduled":
                    total = int(home_score) + int(away_score)
                    if total >= 2:
                        prediction = "🔥 Alta probabilità Over 2.5"
                    else:
                        prediction = "⚠️ Attenzione"
# stima semplice attacco/difesa
home_attack = 1.4
away_attack = 1.2

# fattore casa
home_xg = home_attack * 1.10
away_xg = away_attack * 0.95

over_prob = poisson_over25(home_xg, away_xg)

if over_prob >= 70:
    prediction = f"🔥 OVER 2.5 FORTE ({over_prob}%)"
elif over_prob >= 55:
    prediction = f"🟡 OVER 2.5 POSSIBILE ({over_prob}%)"
else:
    prediction = f"🔴 UNDER PROBABILE ({over_prob}%)"
                matches.append({
                    "home": home,
                    "away": away,
                    "status": status,
                    "home_score": home_score,
                    "away_score": away_score,
                    "prediction": prediction
                    "league": league_name,
                })
        except:
            pass

    return matches

@app.route("/")
def index():
    matches = get_matches()
    return render_template("index.html", matches=matches)

import os
application = app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
