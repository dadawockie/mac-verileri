import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
from pytz import timezone

def get_date_url(days_ahead=0):
    tr_tz = timezone('Europe/Istanbul')
    now_tr = datetime.now(tr_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    hedef_tarih = now_tr + timedelta(days=days_ahead)
    tarih_str = hedef_tarih.strftime('%Y-%m-%d')
    url = f"https://www.sporekrani.com/home/day/{tarih_str}"
    return url, tarih_str

def scrape_matches_for_date(days_ahead, date_label):
    try:
        url, tarih_str = get_date_url(days_ahead=days_ahead)
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        matches = []
        items = soup.find_all("div", class_="event-item")
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
            except Exception:
                continue
        return matches
    except Exception:
        return []

def update_csv_data():
    all_matches = []
    today_matches = scrape_matches_for_date(0, "BUGÜN")
    all_matches.extend(today_matches)
    tomorrow_matches = scrape_matches_for_date(1, "YARIN")
    all_matches.extend(tomorrow_matches)
    day_after_matches = scrape_matches_for_date(2, "YARIN+1")
    all_matches.extend(day_after_matches)
    try:
        with open("mac_kanal_listesi.csv", "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["spor", "tarih", "saat", "maç", "turnuva", "kanal"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            all_matches.sort(key=lambda x: (x['tarih'], x['saat']))
            for m in all_matches:
                writer.writerow(m)
        print(f"CSV dosyası güncellendi. {len(all_matches)} maç bulundu.")
    except Exception as e:
        print(f"Veri güncelleme hatası: {e}")

if __name__ == "__main__":
    update_csv_data()
