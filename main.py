import requests
import datetime
from flask import Flask, request
import logging
import time
import threading
import pytz

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

WEBHOOK_URL = "https://vesperaa-bot.onrender.com/send_paris"
API_KEY = "04e7128d2c962dcc02f6467c87d66afc"
BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

jours_fr = {'Monday':'Lundi','Tuesday':'Mardi','Wednesday':'Mercredi','Thursday':'Jeudi','Friday':'Vendredi','Saturday':'Samedi','Sunday':'Dimanche'}
mois_fr = {'January':'janvier','February':'février','March':'mars','April':'avril','May':'mai','June':'juin','July':'juillet','August':'août','September':'septembre','October':'octobre','November':'novembre','December':'décembre'}

europe_countries = ["France", "Germany", "Spain", "Italy", "England", "Portugal", "Netherlands", "Belgium", "Switzerland", "Austria", "Greece", "Denmark", "Sweden", "Norway", "Finland", "Poland", "Czech Republic", "Croatia", "Serbia", "Turkey"]
excluded_leagues = ["League One", "League Two"]  # Exclure League One et League Two

def get_daily_matches():
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    params = {"date": today}
    response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params, timeout=10).json()

    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    filtered = [
        match for match in response['response']
        if datetime.datetime.fromisoformat(match['fixture']['date'][:19]).replace(tzinfo=datetime.timezone.utc) > now
        and (
            match['league']['country'] in europe_countries
            or (
                "qualification" in match['league']['name'].lower()
                and "world" in match['league']['name'].lower()
            )
        )
        and all(keyword not in (match['league']['name'] + match['teams']['home']['name'] + match['teams']['away']['name']).lower()
                for keyword in ["reserve", "u19", "u21", "feminine", "amateur", "regional", "junior", "youth"])
        and match['league']['name'] not in excluded_leagues  # Exclure League One et League Two
    ]

    print(f"📅 API a retourné {len(response['response'])} matchs pour la date {today}")  # Affiche le nombre total de matchs retournés
    print(f"✅ Matchs après filtrage : {len(filtered)}")  # Affiche le nombre de matchs après filtrage
    return filtered

def analyser_et_envoyer():
    print("🟢 Analyse lancée...")
    matches = get_daily_matches()[:15]
    print(f"📊 {len(matches)} matchs à analyser")  # Affiche le nombre de matchs analysés
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

    print("📤 Envoi du message Telegram...")
    envoyer_message(message)
    print("✅ Message envoyé avec succès")

def get_odds(fixture_id):
    params = {"fixture": fixture_id}
    try:
        response = requests.get(f"{BASE_URL}/odds", headers=headers, params=params, timeout=10).json()
        if response['response']:
            for bookmaker in response['response'][0]['bookmakers']:
                if bookmaker['id'] == 21:
                    return bookmaker['bets']
    except:
        pass
    return []

def extract_bet_from_bets(bets, home, away):
    fallback_paris = []

    for market in bets:
        if market['name'] == "Match Winner":
            for outcome in market['values']:
                odd = float(outcome['odd'])
                winner = home if outcome['value'] == "Home" else away if outcome['value'] == "Away" else "Match nul"
                if 1.5 <= odd <= 2.5:
                    return {"pari": f"Vainqueur : {winner}", "cote": odd}
                elif odd <= 3.0:
                    fallback_paris.append({"pari": f"(Fallback) Vainqueur : {winner}", "cote": odd})

    for market in bets:
        if market['name'] == "Both Teams Score":
            for outcome in market['values']:
                if outcome['value'] == "Yes":
                    odd = float(outcome['odd'])
                    if 1.5 <= odd <= 2.5:
                        return {"pari": "Les deux équipes marquent : Oui", "cote": odd}
                    elif odd <= 3.0:
                        fallback_paris.append({"pari": "(Fallback) Les deux équipes marquent : Oui", "cote": odd})

    return fallback_paris[0] if fallback_paris else None

def detect_value_bet(match):
    fixture_id = match['fixture']['id']
    home = match['teams']['home']['name']
    away = match['teams']['away']['name']
    league = match['league']['name']
    country = match['league']['country']
    match_time = match['fixture']['date']

    bets = get_odds(fixture_id)
    bet = extract_bet_from_bets(bets, home, away)
    if bet:
        return {
            "league": league,
            "country": country,
            "teams": f"{home} vs {away}",
            "time": match_time,
            **bet
        }
    return None

def construire_message(paris):
    today = datetime.datetime.now()
    date_fr = f"{jours_fr[today.strftime('%A')]} {today.day} {mois_fr[today.strftime('%B')]} {today.year}"

    drapeaux = {
        "France": "🇫🇷", "Germany": "🇩🇪", "Spain": "🇪🇸", "Italy": "🇮🇹", "England": "🇬🇧",
        "Portugal": "🇵🇹", "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Switzerland": "🇨🇭", "Austria": "🇦🇹",
        "Greece": "🇬🇷", "Denmark": "🇩🇰", "Sweden": "🇸🇪", "Norway": "🇳🇴", "Finland": "🇫🇮",
        "Poland": "🇵🇱", "Czech Republic": "🇨🇿", "Croatia": "🇭🇷", "Serbia": "🇷🇸", "Turkey": "🇹🇷"
    }

    message = f"🔥 TES PARIS DU JOUR ({date_fr}) 🔥\n\n"

    for pari in paris:
        tz = pytz.timezone("Europe/Paris")
        match_datetime = datetime.datetime.fromisoformat(pari['time'][:19]).replace(tzinfo=datetime.timezone.utc).astimezone(tz)
        heure = match_datetime.strftime("%Hh%M")
        flag = drapeaux.get(pari['country'], "")
        message += f"📅 {pari['teams']} ({flag} {pari['country']} – {pari['league']})\n"
        message += f"🕒 {heure}\n"
        message += f"🎯 {pari['pari']}\n"
        message += f"💸 Cote : {pari['cote']}\n\n"

    message += "Mise conseillée : 1 % de la bankroll par pari\n"
    message += "<i>Rentabilité, rigueur et maîtrise : les clés du succès.</i>\n\n"
    message += "Code ROMATKCO : 30€ offerts en freebets 🤑\n"
    message += "👉 https://www.betclic.fr"

    return message

def envoyer_message(message):
    try:
        # Prépare la requête pour Telegram
        payload = {"chat_id": "-1002553433496", "text": message}
        response = requests.post(f"https://api.telegram.org/bot7561593316:AAGPz8jaC4lz3JrXUwEQB7mKsn3GUEqApAw/sendMessage", json=payload, timeout=10)

        # Log la réponse pour s'assurer qu'il n'y a pas d'erreur
        print(f"Réponse de Telegram : {response.json()}")  # Affiche la réponse pour debug
        if response.status_code == 200:
            print("✅ Message envoyé avec succès")
        else:
            print(f"⚠️ Erreur avec l'envoi : {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Erreur d'envoi du message : {e}")

@app.route('/')
def main():
    threading.Thread(target=analyser_et_envoyer).start()
    return {"status": "Analyse en cours"}, 200

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if 'message' in data and 'text' in data['message']:
        message_text = data['message']['text']
        chat_id = data['message']['chat']['id']

        if message_text.lower() == '/pari':
            threading.Thread(target=analyser_et_envoyer).start()
            send_telegram_reply(chat_id, "🔍 Analyse en cours, tu vas recevoir les paris dans quelques secondes...")
        else:
            send_telegram_reply(chat_id, "Commande non reconnue. Essaie /pari pour recevoir les paris du jour.")
    return {"status": "ok"}, 200

def send_telegram_reply(chat_id, text):
    bot_token = "7561593316:AAGPz8jaC4lz3JrXUwEQB7mKsn3GUEqApAw"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur d'envoi du message : {e}")

if __name__ == '__main__':
    app.run(debug=True)  # Debug à True pour le développement
