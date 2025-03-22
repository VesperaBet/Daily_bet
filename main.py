import requests
import datetime
from flask import Flask
import logging

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
    "Ligue 1", "Premier League", "La Liga", "Serie A", "Bundesliga",
    "UEFA Champions League", "UEFA Europa League", "UEFA Europa Conference League",
    "World Cup", "European Championship", "UEFA Nations League", "Copa America",
    "WC Qualification Europe", "EC Qualification", "Copa America Qualification"
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
    response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params).json()
    return [match for match in response['response'] if match['league']['name'] in competitions_majeures and match['league']['country'] != "Wales"]

# Fonction pour détecter un value bet avec des cotes entre 1.30 et 2.50
def detect_value_bet(match):
    fixture_id = match['fixture']['id']
    odds_response = requests.get(f"{BASE_URL}/odds", headers=headers, params={"fixture": fixture_id, "bookmaker":8}).json()

    if not odds_response['response']:
        return None

    for market in odds_response['response'][0]['bookmakers'][0]['bets']:
        if market['name'] == "Match Winner":
            for outcome in market['values']:
                odd = float(outcome['odd'])
                if 1.3 <= odd <= 2.5:
                    return {
                        'league': match['league']['name'],
                        'teams': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
                        'pari': f"Vainqueur : {outcome['value']}",
                        'cote': odd
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

@app.route('/')
def main():
    matches = get_daily_matches()[:10]  # Limite à 10 matchs analysés max
    paris_du_jour = []

    for match in matches:
        pari = detect_value_bet(match)
        if pari:
            paris_du_jour.append(pari)
        if len(paris_du_jour) == 2:
            break

    if paris_du_jour:
        message = construire_message(paris_du_jour)
        envoyer_message(message)
        return {"status": "Paris envoyés avec succès"}, 200
    else:
        envoyer_message("🚨 Aucun value bet intéressant aujourd'hui.")
        return {"status": "Aucun pari intéressant aujourd'hui"}, 200

if __name__ == '__main__':
    app.run(debug=True)
