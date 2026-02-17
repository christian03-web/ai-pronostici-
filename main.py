from flask import Flask, render_template
import requests
import math
from datetime import datetime

app = Flask(__name__)

# Campionati principali
LEAGUES = {
    "Serie A": "ita.1",
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Bundesliga": "ger.1",
    "Ligue 1": "fra.1",
    "Champions League": "uefa.champions",
    "Europa League": "uefa.europa"
}

# formula probabilità Over 2.5 (Poisson)
def over25_probability(expected_goals):
    p = 1 - (math.exp(-expected_goals) * (1 + expected_goals + (expected_goals**2)/2))
    return round(p*100,1)

def analyze_match(home, away):
    # modello iniziale (base europea)
    base_goals = 2.65

    # piccola logica intelligente
    attacking_teams = [
        "Bayern", "Liverpool", "Manchester City", "PSG", "Barcelona",
        "Real Madrid", "Atalanta", "Leverkusen", "Tottenham"
    ]

    if any(team in home for team in attacking_teams):
        base_goals += 0.35
    if any(team in away for team in attacking_teams):
        base_goals += 0.35

    probability = over25_probability(base_goals)

    if probability >= 72:
        level = "🔥 OVER 2.5 FORTE"
    elif probability >= 58:
        level = "🟡 OVER 2.5 POSSIBILE"
    else:
        level = "🔴 UNDER PROBABILE"

    return probability, level

def get_matches():
    matches = []

    for league_name, code in LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard"

        try:
            data = requests.get(url, timeout=15).json()

            for event in data.get("events", []):
                comp = event["competitions"][0]
                state = comp["status"]["type"]["state"]

                # SOLO PRE-PARTITA
                if state != "pre":
                    continue

                teams = comp["competitors"]
                home = teams[0]["team"]["displayName"]
                away = teams[1]["team"]["displayName"]

                probability, prediction = analyze_match(home, away)

                matches.append({
                    "league": league_name,
                    "home": home,
                    "away": away,
                    "prob": probability,
                    "prediction": prediction
                })

        except:
            pass

    # ordina per probabilità più alta
    matches.sort(key=lambda x: x["prob"], reverse=True)
    return matches

@app.route("/")
def home():
    games = get_matches()
    now = datetime.now().strftime("%d/%m %H:%M")
    return render_template("index.html", matches=games, update=now)

application = app