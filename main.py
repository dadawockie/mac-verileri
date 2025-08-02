from flask import Flask, send_file
import requests
from bs4 import BeautifulSoup
import csv
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Canlı Maç Listesi API"

@app.route('/csv')
def serve_csv():
    return send_file("mac_kanal_listesi.csv", mimetype="text/csv")

@app.route('/guncelle')
def update_and_serve_csv():
    # --- Buraya scraping kodunu ekle (kısaltılmış hali aşağıda) ---
    url = "https://www.sporekrani.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    matches = []
    for item in soup.find_all("div", class_="event-item"):
        try:
            sport_icon = item.find("img", alt=True)
            sport_alt = sport_icon["alt"].capitalize() if sport_icon else ""
            if sport_alt not in ["Futbol", "Basketbol"]:
                continue
            time = item.find("span", class_="text-body3-medium").get_text(strip=True)
            match_name = item.find("p", class_="q-mb-xs text-body3-bold").get_text(strip=True)
            tournament = item.find("p", class_="q-mb-none text-body3-medium text-grey-6").get_text(strip=True)
            channel_img = item.find("div", class_="channel-mobile").find("img")
            channel = channel_img["title"] if channel_img else "Bilinmiyor"
            matches.append({
                "spor": sport_alt,
                "saat": time,
                "maç": match_name,
                "turnuva": tournament,
                "kanal": channel
            })
        except Exception as e:
            continue

    with open("mac_kanal_listesi.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["spor", "saat", "maç", "turnuva", "kanal"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for m in matches:
            writer.writerow(m)

    return send_file("mac_kanal_listesi.csv", mimetype="text/csv")
    # --- Buraya kadar ---

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81)
