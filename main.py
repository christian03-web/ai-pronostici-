from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import requests
import numpy as np
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
templates = Jinja2Templates(directory="templates")

LEAGUES = ["eng.1", "ita.1", "esp.1", "ger.1", "fra.1"]

DAILY_PREDICTIONS = []
LAST_UPDATE = None

italy = pytz.timezone("Europe/Rome")


# -------- DATA ITALIANA --------
def today_italy():
    return datetime.now(italy).strftime("%Y%m%d")


# -------- SCOREBOARD --------
def get_scoreboard(league, date):
    url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date}"
    r = requests.get(url, timeout=20)
    if r.status_code == 200:
        return r.json()
    return None


# -------- STATISTICHE SQUADRA --------
def get_team_stats(league, team_id):
    url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_id}/statistics"
    r = requests.get(url, timeout=20)

    if r.status_code != 200:
        return None

    data = r.json()

    try:
        stats = data["statistics"]["splits"]["categories"]

        shots = 0
        shots_on_target = 0
        goals_for = 0
        goals_against = 0
        games = 1

        for category in stats:
            for item in category["stats"]:
                name = item["name"]

                if name == "shots":
                    shots = float(item["value"])
                if name == "shotsOnTarget":
                    shots_on_target = float(item["value"])
                if name == "goals":
                    goals_for = float(item["value"])
                if name == "goalsAgainst":
                    goals_against = float(item["value"])
                if name == "gamesPlayed":
                    games = float(item["value"])

        # medie per partita
        shots /= games
        shots_on_target /= games
        goals_for /= games
        goals_against /= games

        # xG stimato
        xg = (shots_on_target * 0.30) + (shots * 0.10)

        return {
            "xg": xg,
            "goals_for": goals_for,
            "goals_against": goals_against
        }

    except:
        return None


# -------- POISSON --------
def poisson_simulation(home_xg, away_xg, sims=10000):
    home_goals = np.random.poisson(home_xg, sims)
    away_goals = np.random.poisson(away_xg, sims)

    gg = np.sum((home_goals > 0) & (away_goals > 0)) / sims * 100
    over25 = np.sum((home_goals + away_goals >= 3)) / sims * 100

    return round(gg, 2), round(over25, 2)


# -------- COSTRUZIONE PREVISIONI --------
def build_daily_predictions():
    global DAILY_PREDICTIONS, LAST_UPDATE

    date = today_italy()
    predictions = []

    print("Analisi reale del:", date)

    for league in LEAGUES:
        data = get_scoreboard(league, date)
        if not data or "events" not in data:
            continue

        for event in data["events"]:
            try:
                comp = event["competitions"][0]["competitors"]

                home = comp[0]
                away = comp[1]

                home_team = home["team"]["displayName"]
                away_team = away["team"]["displayName"]

                home_id = home["team"]["id"]
                away_id = away["team"]["id"]

                # recupero statistiche reali
                home_stats = get_team_stats(league, home_id)
                away_stats = get_team_stats(league, away_id)

                if not home_stats or not away_stats:
                    continue

                # forza attacco/difesa
                home_xg = (home_stats["xg"] + away_stats["goals_against"]) / 2
                away_xg = (away_stats["xg"] + home_stats["goals_against"]) / 2

                gg, over25 = poisson_simulation(home_xg, away_xg)

                if gg >= 72 or over25 >= 70:
                    predictions.append({
                        "league": league,
                        "home": home_team,
                        "away": away_team,
                        "gg": gg,
                        "over25": over25
                    })

            except:
                continue

    DAILY_PREDICTIONS = predictions
    LAST_UPDATE = datetime.now(italy)


# aggiornamento automatico
scheduler = BackgroundScheduler(timezone=italy)
scheduler.add_job(build_daily_predictions, 'cron', hour=0, minute=5)
scheduler.start()

# primo avvio
build_daily_predictions()


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "predictions": DAILY_PREDICTIONS,
        "update": LAST_UPDATE
    })