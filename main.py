import requests
import datetime
import random

# --- Configuration ---
WEBHOOK_URL = "https://vesperaa-bot.onrender.com/send_paris"

# Fonctions de génération fictive de paris
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
        confiance = "⭐" * pari_type[3]  # étoiles

        paris_du_jour.append({
            "match": f"{home} vs. {away}",
            "pari": pari_texte,
            "cote": cote,
            "type": type_pari,
            "confiance": confiance
        })

    return paris_du_jour

def construire_message(paris):
    today = datetime.datetime.now().strftime("%A %d %B %Y")
    message = f"⚽️ <b>Paris du jour – {today}</b>\n\n"
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

# --- Routine quotidienne ---
if __name__ == "__main__":
    paris = generer_paris()
    message = construire_message(paris)
    envoyer_message(message)
