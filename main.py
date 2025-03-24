import requests
import datetime
from flask import Flask
import logging
import random
import time
import threading
import pytz

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

WEBHOOK_URL = "https://vesperaa-bot.onrender.com/send_paris"
API_KEY = "57d75879bce795736b4a4bcd9ca465d5"
BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

jours_fr = {'Monday':'Lundi','Tuesday':'Mardi','Wednesday':'Mercredi','Thursday':'Jeudi','Friday':'Vendredi','Saturday':'Samedi','Sunday':'Dimanche'}
mois_fr = {'January':'janvier','February':'février','March':'mars','April':'avril','May':'mai','June':'juin','July':'juillet','August':'août','September':'septembre','October':'octobre','November':'novembre','December':'décembre'}

europe_countries = ["France", "Germany", "Spain", "Italy", "England", "Portugal", "Netherlands", "Belgium", "Switzerland", "Austria", "Greece", "Denmark", "Sweden", "Norway", "Finland", "Poland", "Czech Republic", "Croatia", "Serbia", "Turkey"]

def get_daily_matches():
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    params = {"date": today}
    response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params, timeout=10).json()
    now = datetime.datetime.now()

    return [
        match for match in response['response']
        if datetime.datetime.fromisoformat(match['fixture']['date'][:19]) > now
        and match['league']['country'] in europe_countries
        and all(keyword not in match['league']['name'].lower()
                for keyword in ["reserve", "u19", "u21", "feminine", "amateur", "regional", "junior", "youth"])
    ]

def get_odds(fixture_id):
    params = {"fixture": fixture_id}
    try:
        response = requests.get(f"{BASE_URL}/odds", headers=headers, params=params, timeout=10).json()
        if response['response']:
            for bookmaker in response['response'][0]['bookmakers']:
                if bookmaker['id'] == 21:  # Betclic
                    return bookmaker['bets']
    except:
        pass
    return []

def extract_bet_from_bets(bets, home, away, allow_fallback=True):
    fallback_paris = []

    for market in bets:
        if market['name'] == "Match Winner":
            for outcome in market['values']:
                odd = float(outcome['odd'])
                winner = home if outcome['value'] == "Home" else away if outcome['value'] == "Away" else "Match nul"
                if 1.5 <= odd <= 2.5:
                    return {"pari": f"Vainqueur : {winner}", "cote": odd}
                elif allow_fallback and odd <= 3.0:
                    fallback_paris.append({"pari": f"(Fallback) Vainqueur : {winner}", "cote": odd})

    for market in bets:
        if market['name'] == "Both Teams Score":
            for outcome in market['values']:
                if outcome['value'] == "Yes":
                    odd = float(outcome['odd'])
                    if 1.5 <= odd <= 2.5:
                        return {"pari": "Les deux équipes marquent : Oui", "cote": odd}
                    elif allow_fallback and odd <= 3.0:
                        fallback_paris.append({"pari": "(Fallback) Les deux équipes marquent : Oui", "cote": odd})

    for market in bets:
        if market['name'] == "Goalscorer":
            top_choices = [o for o in market['values'] if 1.8 <= float(o['odd']) <= 3.5]
            if top_choices:
                outcome = random.choice(top_choices)
                return {"pari": f"Buteur : {outcome['value']}", "cote": float(outcome['odd'])}

    if fallback_paris:
        return fallback_paris[0]
    return None

def detect_value_bet(match):
    fixture_id = match['fixture']['id']
    home = match['teams']['home']['name']
    away = match['teams']['away']['name']
    league = match['league']['name']
    country = match['league']['country']
    match_time = match['fixture']['date']

    bets = get_odds(fixture_id)
    bet = extract_bet_from_bets(bets, home, away, allow_fallback=False)
    if bet:
        return {
            "league": league,
            "country": country,
            "teams": f"{home} vs {away}",
            "time": match_time,
            **bet
        }
    return None

def construire_message(pari):
    today = datetime.datetime.now()
    date_fr = f"{jours_fr[today.strftime('%A')]} {today.day} {mois_fr[today.strftime('%B')]} {today.year}"
    
    tz = pytz.timezone("Europe/Paris")
    match_datetime = datetime.datetime.fromisoformat(pari['time'][:19]).replace(tzinfo=datetime.timezone.utc).astimezone(tz)
    heure = match_datetime.strftime("%Hh%M")

    drapeaux = {
        "France": "🇫🇷", "Germany": "🇩🇪", "Spain": "🇪🇸", "Italy": "🇮🇹", "England": "🇬🇧",
        "Portugal": "🇵🇹", "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Switzerland": "🇨🇭", "Austria": "🇦🇹",
        "Greece": "🇬🇷", "Denmark": "🇩🇰", "Sweden": "🇸🇪", "Norway": "🇳🇴", "Finland": "🇫🇮",
        "Poland": "🇵🇱", "Czech Republic": "🇨🇿", "Croatia": "🇭🇷", "Serbia": "🇷🇸", "Turkey": "🇹🇷"
    }

    flag = drapeaux.get(pari['country'], "")
    message = f"""🔥 TON PARI DU JOUR 🔥

📅 Match : {pari['teams']} ({pari['league']})
🕒 Heure : {heure}
🎯 Pari : {pari['pari']}
💸 Cote : {pari['cote']}
🏆 Championnat : {flag} {pari['country']}

Mise conseillée : 1 % de la bankroll

<i>Rentabilité, rigueur et maîtrise : les clés du succès.</i>

Avec mon code ROMATKCO, profite de 30€ offerts en freebets !
👉 https://www.betclic.fr
"""
    return message

def envoyer_message(message):
    try:
        response = requests.post(WEBHOOK_URL, json={"message": message}, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Erreur d’envoi du message : {e}")

def analyser_et_envoyer():
    matches = get_daily_matches()[:10]
    for match in matches:
        pari = detect_value_bet(match)
        time.sleep(1)
        if pari:
            message = construire_message(pari)
            envoyer_message(message)
            return
    envoyer_message("🚨 Aucun value bet intéressant aujourd'hui.")

@app.route('/')
def main():
    threading.Thread(target=analyser_et_envoyer).start()
    return {"status": "Analyse en cours"}, 200

if __name__ == '__main__':
    app.run(debug=True)
