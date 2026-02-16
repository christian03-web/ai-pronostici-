from flask import Flask, render_template
import requests

app = Flask(__name__)

LEAGUES = [
    "ita.1",
    "eng.1",
    "esp.1",
    "ger.1",
    "fra.1",
    "uefa.champions"
]

def get_matches():
    matches = []

    for league in LEAGUES:
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

                status = comp["status"]["type"]["description"]

                prediction = "⚖️ Normale"
                if status != "Scheduled":
                    total = int(home_score) + int(away_score)
                    if total >= 2:
                        prediction = "🔥 Alta probabilità Over 2.5"
                    else:
                        prediction = "⚠️ Attenzione"

                matches.append({
                    "home": home,
                    "away": away,
                    "status": status,
                    "home_score": home_score,
                    "away_score": away_score,
                    "prediction": prediction
                })
        except:
            pass

    return matches

@app.route("/")
def index():
    matches = get_matches()
    return render_template("index.html", matches=matches)

app.run(host="0.0.0.0", port=3000)
