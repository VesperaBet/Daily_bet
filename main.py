import requests
import datetime
import random

WEBHOOK_URL = "https://vesperaa-bot.onrender.com/send_paris"

# Liste des jours et mois en français
jours_fr = {
    'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
}

mois_fr = {
    'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril',
    'May': 'mai', 'June': 'juin', 'July': 'juillet', 'August': 'août',
    'September': 'septembre', 'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
}

matchs_possibles = [
    ("Marseille", "Reims"),
    ("Lille", "Nice"),
    ("Lyon", "Toulouse"),
    ("Valence", "Séville"),
    ("Lazio", "Roma"),
    ("PSG", "Monaco"),
    ("Naples", "Atalanta"),
    ("Betis", "Real Sociedad"),
    ("Lens", "Strasbourg")
]

paris_possibles = [
    ("Victoire {home}", 1.60, "Pari simple", 3),
    ("Les deux équipes marquent", 1.70, "Pari simple", 2),
    ("+2,5 buts dans le match", 1.85, "Pari simple", 2),
    ("Victoire {home} ou nul + +1,5 buts", 1.95, "Combiné", 3),
    ("Score exact : 2-1", 2.10, "Pari simple", 1)
]

def generer_paris():
    nombre_de_paris = random.choice([1, 2])
    paris_du_jour = []
    matchs_du_jour = random.sample(matchs_possibles, nombre_de_paris)

    for match in matchs_du_jour:
        pari_type = random.choice(paris_possibles)
        home, away = match
        pari_texte = pari_type[0].format(home=home, away=away)
        cote = pari_type[1]
        type_pari = pari_type[2]
        confiance = "⭐" * pari_type[3]

        paris_du_jour.append({
            "match": f"{home} vs. {away}",
            "pari": pari_texte,
            "cote": cote,
            "type": type_pari,
            "confiance": confiance
        })

    return paris_du_jour

def construire_message(paris):
    today = datetime.datetime.now()
    jour_en = today.strftime("%A")
    mois_en = today.strftime("%B")
    jour_fr = jours_fr[jour_en]
    mois_francais = mois_fr[mois_en]
    date_fr = f"{jour_fr} {today.day} {mois_francais} {today.year}"

    message = f"⚽️ <b>Paris du jour – {date_fr}</b>\n\n"
    for i, pari in enumerate(paris, 1):
        message += f"{i}. {pari['match']}\n"
        message += f"🔎 Pari : {pari['pari']}\n"
        message += f"💰 Cote : {pari['cote']}\n"
        message += f"🔹 Type : {pari['type']}\n"
        message += f"🔸 Confiance : {pari['confiance']}\n\n"

    message += "🔁 Mise recommandée : 1 % de la bankroll par pari\n"
    message += "📈 Stratégie value / long terme / discipline stricte"
    return message

def envoyer_message(message):
    payload = {"message": message}
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        print("✅ Message envoyé avec succès sur Telegram.")
    else:
        print("❌ Échec de l'envoi.", response.text)
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "Bot prêt à envoyer les paris"}, 200

if __name__ == "__main__":
    paris = generer_paris()
    message = construire_message(paris)
    envoyer_message(message)
