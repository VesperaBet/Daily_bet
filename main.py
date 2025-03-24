import requests
import datetime
from flask import Flask
import logging
import random
import time
import threading

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

WEBHOOK_URL = "https://vesperaa-bot.onrender.com/send_paris"
API_KEY = "57d75879bce795736b4a4bcd9ca465d5"
BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

jours_fr = {'Monday':'Lundi','Tuesday':'Mardi','Wednesday':'Mercredi','Thursday':'Jeudi','Friday':'Vendredi','Saturday':'Samedi','Sunday':'Dimanche'}
mois_fr = {'January':'janvier','February':'février','March':'mars','April':'avril','May':'mai','June':'juin','July':'juillet','August':'août','September':'septembre','October':'octobre','November':'novembre','December':'décembre'}

def get_daily_matches():
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    params = {"date": today}
    response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params, timeout=10).json()
    return response['response']

def get_odds(fixture_id):
    params = {"fixture": fixture_id}
    try:
        response = requests.get(f"{BASE_URL}/odds", headers=headers, params=params, timeout=10).json()
        if response['response']:
            return response['response'][0]['bookmakers'][0]['bets']
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
    teams = f"{home} vs {away}"

    bets = get_odds(fixture_id)
    bet = extract_bet_from_bets(bets, home, away, allow_fallback=True)
    if bet:
        return {"league": league, "teams": teams, **bet}
    return None

def construire_message(paris):
    today = datetime.datetime.now()
    date_fr = f"{jours_fr[today.strftime('%A')]} {today.day} {mois_fr[today.strftime('%B')]} {today.year}"
    message = f"⚽️ <b>Paris du jour – {date_fr}</b>\n\n"
    for i, pari in enumerate(paris, 1):
        message += f"{i}. {pari['teams']} ({pari['league']})\n"
        message += f"🔎 Pari : {pari['pari']}\n"
        message += f"💰 Cote : {pari['cote']}\n"
        message += f"🔸 Confiance : ⭐⭐⭐⭐\n\n"
    message += "🔁 Mise recommandée : 1 % de la bankroll par pari\n"
    message += "📈 Stratégie value / long terme / discipline stricte"
    return message

def envoyer_message(message):
    requests.post(WEBHOOK_URL, json={"message": message})

def analyser_et_envoyer():
    matches = get_daily_matches()[:15]
    paris_du_jour = []
    for match in matches:
        pari = detect_value_bet(match)
        time.sleep(1)
        if pari:
            paris_du_jour.append(pari)
            break
    message = construire_message(paris_du_jour) if paris_du_jour else "🚨 Aucun value bet intéressant aujourd'hui."
    envoyer_message(message)

@app.route('/')
def main():
    threading.Thread(target=analyser_et_envoyer).start()
    return {"status": "Analyse en cours"}, 200

if __name__ == '__main__':
    app.run(debug=True)
