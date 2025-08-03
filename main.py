from flask import Flask, send_file
import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime, timedelta
import schedule
import time
import threading

app = Flask(__name__)


from pytz import timezone

def get_date_url(days_ahead=0):
    """Belirtilen gün sayısı kadar ileriye ait URL oluştur - SAAT DİLİMLİ!"""
    tr_tz = timezone('Europe/Istanbul')
    now_tr = datetime.now(tr_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    hedef_tarih = now_tr + timedelta(days=days_ahead)
    tarih_str = hedef_tarih.strftime('%Y-%m-%d')
    url = f"https://www.sporekrani.com/home/day/{tarih_str}"
    return url, tarih_str


def scrape_matches_for_date(days_ahead, date_label):
    """Belirtilen tarih için maç verilerini çek"""
    try:
        url, tarih_str = get_date_url(days_ahead=days_ahead)
        print(f"[{datetime.now()}] {date_label} URL'si çekiliyor: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        matches = []

        items = soup.find_all("div", class_="event-item")
        print(f"[{datetime.now()}] {date_label}: {len(items)} öğe bulundu")

        for item in items:
            try:
                sport_icon = item.find("img", alt=True)
                sport_alt = sport_icon["alt"].capitalize() if sport_icon else ""

                if sport_alt not in ["Futbol", "Basketbol"]:
                    continue

                time_elem = item.find("span", class_="text-body3-medium")
                time_str = time_elem.get_text(strip=True) if time_elem else ""

                match_name_elem = item.find("p", class_="q-mb-xs text-body3-bold")
                match_name = match_name_elem.get_text(strip=True) if match_name_elem else ""

                tournament_elem = item.find("p", class_="q-mb-none text-body3-medium text-grey-6")
                tournament = tournament_elem.get_text(strip=True) if tournament_elem else ""

                channel_div = item.find("div", class_="channel-mobile")
                if channel_div:
                    channel_img = channel_div.find("img")
                    channel = channel_img["title"] if channel_img else "Bilinmiyor"
                else:
                    channel = "Bilinmiyor"

                if match_name:
                    matches.append({
                        "spor": sport_alt,
                        "saat": time_str,
                        "maç": match_name,
                        "turnuva": tournament,
                        "kanal": channel,
                        "tarih": tarih_str
                    })

            except Exception as e:
                print(f"Maç işlenirken hata ({date_label}): {e}")
                continue

        print(f"[{datetime.now()}] {date_label}: {len(matches)} maç bulundu")
        return matches

    except Exception as e:
        print(f"[{datetime.now()}] {date_label} çekilirken hata: {e}")
        return []


def update_csv_data():
    """CSV verilerini güncelle ve GitHub'a push et"""
    print(f"[{datetime.now()}] Veri güncelleme başladı...")

    all_matches = []

    # Bugünün maçlarını çek
    today_matches = scrape_matches_for_date(0, "BUGÜN")
    all_matches.extend(today_matches)

    # Yarının maçlarını çek
    tomorrow_matches = scrape_matches_for_date(1, "YARIN")
    all_matches.extend(tomorrow_matches)

    # Yarından sonraki günün maçlarını çek
    day_after_matches = scrape_matches_for_date(2, "YARIN+1")
    all_matches.extend(day_after_matches)

    print(f"[{datetime.now()}] TOPLAM: {len(all_matches)} maç bulundu")

    try:
        # CSV dosyasını yaz
        with open("mac_kanal_listesi.csv", "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["spor", "tarih", "saat", "maç", "turnuva", "kanal"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Tarihe ve saate göre sırala
            all_matches.sort(key=lambda x: (x['tarih'], x['saat']))

            for m in all_matches:
                writer.writerow(m)

        print(f"[{datetime.now()}] CSV dosyası güncellendi. {len(all_matches)} maç bulundu.")

        # GitHub'a push et
        today_date = datetime.now().strftime('%Y-%m-%d')
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

        git_commands = [
            "git add mac_kanal_listesi.csv",
            f'git commit -m "auto: veriler guncellendi - {datetime.now().strftime("%Y-%m-%d %H:%M")} [{len(all_matches)} maç] ({today_date} + {tomorrow_date} + {day_after_date})"',
            "git push origin main"
        ]

        for cmd in git_commands:
            result = os.system(cmd)
            if result != 0:
                print(f"[{datetime.now()}] Git komutu başarısız: {cmd}")
            else:
                print(f"[{datetime.now()}] Git komutu başarılı: {cmd}")

        print(f"[{datetime.now()}] Veri güncelleme tamamlandı!")

    except Exception as e:
        print(f"[{datetime.now()}] Veri güncelleme hatası: {e}")


def run_scheduler():
    """Scheduler'ı arka planda çalıştır"""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Her dakika kontrol et


@app.route('/')
def home():
    return """
    <h2>🏆 Canlı Maç Listesi API - Otomatik Güncelleme Aktif</h2>
    <p><strong>Endpoints:</strong></p>
    <ul>
        <li><a href="/csv">/csv</a> - CSV dosyasını indir</li>
        <li><a href="/guncelle">/guncelle</a> - Manuel güncelleme yap</li>
        <li><a href="/status">/status</a> - Sistem durumu</li>
    </ul>
    <p><em>Sistem her gece 00:01'de otomatik olarak bugün, yarın ve yarından sonraki günün maçlarını günceller.</em></p>
    """


@app.route('/csv')
def serve_csv():
    """CSV dosyasını serve et"""
    if os.path.exists("mac_kanal_listesi.csv"):
        return send_file("mac_kanal_listesi.csv", mimetype="text/csv")
    else:
        return "CSV dosyası henüz oluşturulmamış. /guncelle endpoint'ini kullanın.", 404


@app.route('/guncelle')
def manual_update():
    """Manual güncelleme endpoint'i"""
    update_csv_data()
    if os.path.exists("mac_kanal_listesi.csv"):
        return send_file("mac_kanal_listesi.csv", mimetype="text/csv")
    else:
        return "Güncelleme sırasında hata oluştu.", 500


@app.route('/status')
def status():
    """Sistem durumu"""
    if os.path.exists("mac_kanal_listesi.csv"):
        modified_time = datetime.fromtimestamp(os.path.getmtime("mac_kanal_listesi.csv"))

        # CSV'deki maç sayısını oku
        try:
            with open("mac_kanal_listesi.csv", "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # Header'ı atla
                match_count = sum(1 for row in reader)
        except:
            match_count = "Bilinmiyor"

        # Tarihleri hesapla
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

        return f"""
        <h3>📊 Sistem Durumu</h3>
        <p><strong>Son güncelleme:</strong> {modified_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Toplam maç sayısı:</strong> {match_count}</p>
        <p><strong>Kapsanan tarihler:</strong> {today} (bugün) + {tomorrow} (yarın) + {day_after} (yarından sonra)</p>
        <p><strong>Sonraki otomatik güncelleme:</strong> Her gece 00:01</p>
        <hr>
        <p><a href="/csv">CSV'yi İndir</a> | <a href="/guncelle">Manuel Güncelle</a></p>
        """
    else:
        return """
        <h3>⚠️ Sistem Durumu</h3>
        <p>CSV dosyası henüz oluşturulmamış</p>
        <p><a href="/guncelle">İlk Güncellemeyi Yap</a></p>
        """


if __name__ == "__main__":
    # İlk başta bir kez çalıştır
    print("🚀 İlk veri güncelleme başlatılıyor...")
    update_csv_data()

    # Her gece 00:01'de çalışacak şekilde zamanla
    schedule.every().day.at("00:01").do(update_csv_data)

    # Scheduler'ı arka planda başlat
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    print("⏰ Otomatik güncelleme sistemi başlatıldı. Her gece 00:01'de çalışacak.")
    print("📊 Sistem bugün, yarın ve yarından sonraki günün maçlarını çekecek.")

    # Flask uygulamasını başlat
    app.run(host='0.0.0.0', port=81)