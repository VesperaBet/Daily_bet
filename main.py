import requests
import datetime
from flask import Flask
import logging
import random
import time
import threading

# Supprime les logs inutiles
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# ===== CONFIGURATION =====
WEBHOOK_URL = "https://vesperaa-bot.onrender.com/send_paris"
API_KEY = "57d75879bce795736b4a4bcd9ca465d5"
BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

competitions_majeures = [
    # Clubs Europe
    "Premier League", "La Liga", "Ligue 1", "Serie A", "Bundesliga",
    "UEFA Champions League", "UEFA Europa League", "UEFA Europa Conference League",

    # Nations
    "World Cup", "European Championship", "UEFA Nations League", "Copa America", "Africa Cup of Nations",
    "CONCACAF Gold Cup",

    # Qualifications
    "WC Qualification Europe", "WC Qualification Africa", "WC Qualification South America",
    "WC Qualification CONCACAF", "WC Qualification Asia", "EC Qualification", "Copa America Qualification"
]

jours_fr = {'Monday':'Lundi','Tuesday':'Mardi','Wednesday':'Mercredi',
            'Thursday':'Jeudi','Friday':'Vendredi','Saturday':'Samedi','Sunday':'Dimanche'}

mois_fr = {'January':'janvier','February':'février','March':'mars','April':'avril',
           'May':'mai','June':'juin','July':'juillet','August':'août',
           'September':'septembre','October':'octobre','November':'novembre','December':'décembre'}

# Fonction pour récupérer les matchs du jour
def get_daily_matches():
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    params = {"date": today}
    response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params, timeout=10).json()
    return [match for match in response['response'] if match['league']['name'] in competitions_majeures and match['league']['country'] != "Wales"]

# Détecter value bet avec priorité 1X2 > BTTS > Buteur
def detect_value_bet(match):
    fixture_id = match['fixture']['id']
    try:
        odds_response = requests.get(f"{BASE_URL}/odds", headers=headers, params={"fixture": fixture_id, "bookmaker":8}, timeout=10).json()
    except Exception:
        return None

    if not odds_response['response']:
        return None

    bets = odds_response['response'][0]['bookmakers'][0]['bets']

    # Priorité 1 : Match Winner
    for market in bets:
        if market['name'] == "Match Winner":
            for outcome in market['values']:
                odd = float(outcome['odd'])
                if 1.5 <= odd <= 2.5:
                    return {
                        'league': match['league']['name'],
                        'teams': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
                        'pari': f"Vainqueur : {outcome['value']}",
                        'cote': odd
                    }

    # Priorité 2 : Les deux équipes marquent
    for market in bets:
        if market['name'] == "Both Teams Score":
            for outcome in market['values']:
                if outcome['value'] == "Yes":
                    odd = float(outcome['odd'])
                    if 1.5 <= odd <= 2.5:
                        return {
                            'league': match['league']['name'],
                            'teams': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
                            'pari': "Les deux équipes marquent : Oui",
                            'cote': odd
                        }

    # Priorité 3 : Buteur (léger)
    for market in bets:
        if market['name'] == "Goalscorer":
            top_choices = [o for o in market['values'] if 1.8 <= float(o['odd']) <= 3.0]
            if top_choices:
                outcome = random.choice(top_choices)
                return {
                    'league': match['league']['name'],
                    'teams': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
                    'pari': f"Buteur : {outcome['value']}",
                    'cote': float(outcome['odd'])
                }

    return None

# Construire le message Telegram
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

# Envoyer le message via Telegram webhook
def envoyer_message(message):
    requests.post(WEBHOOK_URL, json={"message": message})

# Fonction d'analyse en tâche de fond
def analyser_et_envoyer():
    matches = get_daily_matches()[:30]  # Analyse jusqu'à 30 matchs
    paris_du_jour = []

    for match in matches:
        pari = detect_value_bet(match)
        time.sleep(1)
        if pari:
            paris_du_jour.append(pari)
        if len(paris_du_jour) == 2:
            break

    if paris_du_jour:
        message = construire_message(paris_du_jour)
    else:
        message = "🚨 Aucun value bet intéressant aujourd'hui."

    envoyer_message(message)

@app.route('/')
def main():
    threading.Thread(target=analyser_et_envoyer).start()
    return {"status": "Analyse en cours"}, 200

if __name__ == '__main__':
    app.run(debug=True)
