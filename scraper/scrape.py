"""Public bank campaigns. Failed sources never replace the last good data.

Default: Chromium/Playwright. --http reads the banks' server-rendered HTML;
it is useful for diagnostics where Chromium is not installed.
Only a reviewed, text-hash-bound rule is used for monetary recommendations.
Title hints never turn a monthly 'up to' cap into a per-purchase reward.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SITELER = {
    "maximum": {"url": "https://www.maximum.com.tr/kampanyalar", "kart": ".camp_cardsAll .card", "baslik": ".card-text", "link": "a[href*='/kampanyalar/']", "daha": ".CampAllShow", "detay": ".campaign-detail-desc"},
    "bankkart": {"url": "https://www.bankkart.com.tr/kampanyalar", "kart": "a.campaign-box", "baslik": ".front .h4", "link": None, "daha": ".btn-all-campaigns", "detay": ".detail-content, .subpage-detail", "bos": ".warning-text"},
    "bonus": {"url": "https://www.bonus.com.tr/kampanyalar", "kart": ".campaign-online-list .campaign-box", "baslik": ".campaign-box__title", "link": "a.direct[href*='/kampanyalar/']", "daha": ".campaign-page-button", "detay": ".campaign-detail__content", "kapat": ".hypeModalBonusClose"},
}
BANKKART_KATEGORILER = ["akaryakit", "beyaz-esya-ve-ev-aletleri", "egitim-kitap-ve-kirtasiye", "elektronik-ve-telekomunikasyon", "e-ticaret", "giyim-ve-aksesuar", "hobi-ve-oyuncak", "kuyum-optik-ve-saat", "market-ve-gida", "mobilya-ve-dekorasyon", "turizm-ve-seyahat", "sigorta-ve-bireysel-emeklilik", "yapi-sektoru-ve-iklimlendirme", "genel-kampanyalar", "diger-kampanyalar"]
KATEGORILER = {"market": "Market", "akaryakit": "Akaryakıt", "yemek": "Yemek & kafe", "giyim": "Giyim", "elektronik": "Elektronik & ev", "seyahat": "Seyahat", "online": "Online alışveriş"}
ANAHTARLAR = {"market": ["market", "gida", "migros", "carrefoursa", "a101"], "akaryakit": ["akaryakit", "petrol", "shell", "opet", "yakit", "recharge"], "yemek": ["restoran", "yemek", "kafe", "kahve", "restaurant"], "giyim": ["giyim", "ayakkabi", "moda", "beymen", "pierre cardin", "cacharel", "koton"], "elektronik": ["elektronik", "beyaz esya", "mobilya", "ev alet", "teknosa", "arcelik", "monster", "dekorasyon"], "seyahat": ["seyahat", "turizm", "otel", "ucak", "bilet", "tatil", "arac kiralama"], "online": ["e-ticaret", "e ticaret", "internet", "online", "trendyol", "hepsiburada", "n11", "pazarama"]}
MARKALAR = ["CarrefourSA", "Migros", "Trendyol", "Hepsiburada", "Pazarama", "n11", "Shell Recharge", "Shell", "Opet", "Petrol Ofisi", "Teknosa", "MediaMarkt", "Monster", "Arçelik", "Beko", "Beymen", "Pierre Cardin", "Cacharel", "U.S. Polo Assn.", "Koton", "Mavi", "Boyner", "LC Waikiki", "IKEA", "A101", "Getir", "Yemeksepeti", "THY", "Pegasus", "ETS", "Jolly"]
AYLAR = {"ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6, "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12}


def norm(value):
    value = str(value).lower().replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def clean(value):
    return re.sub(r"\s+", " ", value).strip()


def number(value):
    return float(str(value).replace(".", "").replace(",", "."))


def iso(y, m, d):
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except (ValueError, TypeError):
        return None


def dates(text):
    """Read explicit purchase ranges, never infer a start from the current date."""
    s = norm(text).replace("–", "-").replace("—", "-")
    if "kampanya baslangic ve bitis" in s:
        s = s.split("kampanya baslangic ve bitis", 1)[1].split("bonus gecerlilik", 1)[0]
    months = "|".join(AYLAR)
    # 1 Eylül 2026 - 30 Eylül 2026; 1 - 30 Eylül 2026;
    # 15 Ağustos - 30 Eylül 2026. First explicit range wins.
    pattern = rf"(\d{{1,2}})\s*({months})?\s*(20\d{{2}})?\s*-\s*(\d{{1,2}})\s*({months})\s*(20\d{{2}})"
    m = re.search(pattern, s)
    if m:
        d1, m1, y1, d2, m2, y2 = m.groups()
        return iso(y1 or y2, AYLAR[m1 or m2], d1), iso(y2, AYLAR[m2], d2)
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](20\d{2})\s*-\s*(\d{1,2})[./](\d{1,2})[./](20\d{2})", s)
    if m:
        d1, m1, y1, d2, m2, y2 = m.groups()
        return iso(y1, m1, d1), iso(y2, m2, d2)
    return None, None


def hints(title):
    s = norm(title)
    amount = r"([\d.]+(?:,\d+)?)\s*(?:tl|lira)"
    minimum = re.search(amount + r"\s*(?:ve uzeri|uzeri|ve ustu)", s)
    cap = re.search(amount + r"(?:['’]?ye|['’]?ya)?\s*varan", s)
    percent = re.search(r"%\s*(\d+(?:,\d+)?)", s)
    installments = re.search(r"(\d+)\s*(?:ay(?:a)?\s*)?(?:varan\s*)?taksit", s)
    return {"minHarcama": number(minimum[1]) if minimum else None, "ustLimit": number(cap[1]) if cap else None, "oranIpucu": number(percent[1]) / 100 if percent else None, "taksitIpucu": int(installments[1]) if installments else None}


def detail_text(html, program):
    soup = BeautifulSoup(html, "html.parser")
    # First selector in priority order, not first in document order.
    node = next((soup.select_one(x.strip()) for x in SITELER[program]["detay"].split(",") if soup.select_one(x.strip())), None)
    if node is None:
        raise ValueError("Kampanya koşulları seçicisi bulunamadı")
    for child in node.select("script, style, nav, header, footer, .modal, .cookie"):
        child.decompose()
    return clean(node.get_text(" ", strip=True))


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cards_from_html(html, program, page_url):
    soup = BeautifulSoup(html, "html.parser")
    config = SITELER[program]
    output = []
    for node in soup.select(config["kart"]):
        link = node.select_one(config["link"]) if config["link"] else node
        title_node = node.select_one(config["baslik"])
        if not link or not title_node:
            continue
        title = clean(title_node.get_text(" ", strip=True))
        url = urljoin(page_url, link.get("href", "")).split("#")[0].split("?")[0]
        if not title or urlparse(url).hostname != urlparse(config["url"]).hostname or "/kampanyalar/" not in url:
            continue
        context = norm(title + " " + node.get_text(" ", strip=True) + " " + str(node.get("data-sector", "")) + " " + url)
        categories = [key for key, words in ANAHTARLAR.items() if any(w in context for w in words)]
        brand = next((b for b in MARKALAR if norm(b) in norm(title)), None)
        start, end = dates(node.get_text(" ", strip=True))
        if not end:
            m = re.search(r"son gun\s*(\d{1,2})[./](\d{1,2})[./](20\d{2})", norm(node.get_text(" ", strip=True)))
            if m:
                end = iso(m[3], m[2], m[1])
        campaign = {"id": program + "-" + hashlib.sha256(url.encode()).hexdigest()[:16], "program": program, "baslik": title, "kategori": categories, "marka": brand, "baslangic": start, "bitis": end, "url": url, "oran": None, "sabitKazanc": None, "taksitAy": 0, "puanTipi": "serbest", "katilimGerekli": True, "tahmini": True, "hesaplanabilir": False, "kosul": "Koşullar, uygun kartlar ve ödeme yöntemi bankanın sayfasından kontrol edilmeli.", **hints(title)}
        output.append(campaign)
    return output


def apply_rule(campaign, text, rules):
    campaign["metinOzeti"] = text[:1400]
    campaign["kosulHash"] = fingerprint(text)
    start, end = dates(text)
    if start and end:
        campaign.update(baslangic=start, bitis=end)
    rule = rules.get(campaign["url"])
    if not rule:
        automatic_rule(campaign, text)
    if rule and rule.get("kosulHash") == fingerprint(text) and rule.get("baslangic") == campaign["baslangic"] and rule.get("bitis") == campaign["bitis"]:
        allowed = {"minHarcama", "ustLimit", "oran", "sabitKazanc", "taksitAy", "puanTipi", "katilimGerekli", "kategori", "marka", "kademeler", "kanal", "kosul", "tahmini", "hesaplanabilir", "pesinFiyatina"}
        campaign.update({k: v for k, v in rule.items() if k in allowed})
    return campaign


def automatic_rule(campaign, text):
    """Small, conservative grammar. Unrecognised conditions remain excluded."""
    if not campaign.get("baslangic") or not campaign.get("bitis"):
        return
    s, title = norm(text), norm(campaign["baslik"])
    if any(w in title for w in ["ilk kart", "yeni musteri", "size ozel", "genc", "prestij", "platinum", "business", "ticari", "garantipay", "qr", "temassiz"]):
        return
    base = {"tahmini": False, "hesaplanabilir": True, "dogrulama": "otomatik", "kosul": "Tek alışveriş koşulu metinden otomatik okundu. Katılım, uygun kart türü, işyeri/POS, istisnalar ve kullanılmamış müşteri limiti bankadan doğrulanmalı."}
    amount = r"([\d.]+(?:,\d+)?)\s*tl"
    single = re.search(r"tek seferde yapacaginiz\s*" + amount + r"\s*ve uzeri her alisverisiniz\s*(?:ile|icin)\s*" + amount, s)
    if campaign["program"] == "bankkart" and single and not any(w in s for w in ["katilim ucreti", "ilk kez bankkart", "harcama sozu"]):
        cap = re.search(r"toplam\s*" + amount + r"\s*(?:jest|bankkart) lira", s)
        campaign.update(base, minHarcama=number(single[1]), sabitKazanc=number(single[2]), ustLimit=number(cap[1]) if cap else None, oran=None, taksitAy=0, puanTipi="serbest")
        if re.search(r"e-ticaret islemleri kampanyaya dahil degildir", s):
            campaign["kanal"] = "fiziksel"
        return
    # Only one unambiguous total instalment count at an identified brand.
    counts = set(re.findall(r"\b(\d{1,2})\s*(?:ay\s*)?taksit", title))
    restricted = ["varan", "ilave", "ekstra", "secili urun", "urun grubuna", "vade farki uygulan", "faiz oran", "katilim ucreti"]
    if not campaign.get("marka") or len(counts) != 1 or any(w in s for w in restricted):
        return
    n = int(next(iter(counts)))
    if not 2 <= n <= 36:
        return
    if not re.search(r"(?:pesin fiyatina|vade farksiz|faizsiz|ucretsiz)\s*" + str(n) + r"\s*(?:ay\s*)?taksit", s):
        return
    minimums = set(re.findall(amount + r"\s*ve uzeri", s))
    if len(minimums) > 1 or any(w in s for w in ["arasindaki alisveris", "altindaki alisveris"]):
        return
    campaign.update(base, minHarcama=number(next(iter(minimums))) if minimums else 0, oran=None, sabitKazanc=None, ustLimit=None, taksitAy=n, pesinFiyatina=True)


def initial_data():
    colors = ["#ae176e", "#bf2539", "#147846", "#344967"]
    programs = ["maximum", "bankkart", "bonus", "maximum"]
    return {"surum": 1, "guncelleme": None, "kategoriler": KATEGORILER, "kartlar": [{"id": f"kart-{i+1}", "ad": f"Kart {i+1}", "sahip": "", "program": programs[i], "banka": "", "kesimGunu": None, "renk": colors[i], "aktif": False} for i in range(4)], "kampanyalar": [], "kaynaklar": {}}


def merge_results(old, fresh, errors, now):
    """Per-source preservation; the 30-total gate protects first and later runs."""
    result = dict(old)
    campaigns = []
    health = dict(old.get("kaynaklar", {}))
    successes = 0
    for program in SITELER:
        previous = [c for c in old.get("kampanyalar", []) if c["program"] == program]
        incoming = fresh.get(program, [])
        if program not in errors and (len(incoming) < 10 or (previous and len(incoming) < len(previous) * .5)):
            errors[program] = f"Sayı kontrolü: {len(incoming)} kayıt (önceki {len(previous)}). Eski veri korundu."
        if program in errors:
            campaigns.extend(previous)
            health[program] = {**health.get(program, {}), "durum": "hata", "sonDeneme": now, "mesaj": str(errors[program])[:300]}
        else:
            previous_by_id = {c["id"]: c for c in previous}
            for item in incoming:
                prior = previous_by_id.get(item["id"], {})
                if prior.get("baslangic") == item.get("baslangic") and prior.get("bitis") == item.get("bitis") and item.get("bitis"):
                    if "katilim" in prior:
                        item["katilim"] = prior["katilim"]
            campaigns.extend(incoming)
            health[program] = {"durum": "ok", "sonDeneme": now, "sonBasari": now, "adet": len(incoming)}
            successes += 1
    if not successes or len(campaigns) < 30:
        raise ValueError("Güvenlik eşiği sağlanmadı. Mevcut JSON değiştirilmedi.")
    result.update(guncelleme=now, kampanyalar=campaigns, kaynaklar=health)
    return result


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


class Fetcher:
    def __init__(self, http=False):
        self.http = http
        self.context = None

    async def __aenter__(self):
        if not self.http:
            from playwright.async_api import async_playwright
            self.pw = await async_playwright().start()
            self.browser = await self.pw.chromium.launch(headless=True)
            self.context = await self.browser.new_context(locale="tr-TR")
        return self

    async def __aexit__(self, *args):
        if self.context:
            await self.browser.close()
            await self.pw.stop()

    async def http_get(self, url):
        def request():
            req = Request(url, headers={"User-Agent": "HangiKart-CampaignReader/1.0 (public campaign index)"})
            with urlopen(req, timeout=35) as response:
                return response.read().decode("utf-8", errors="replace")
        return await asyncio.to_thread(request)

    async def dismiss_overlays(self, page, config):
        """Use normal cookie/promotion controls; never remove or bypass overlays."""
        dismissed = False
        reject = page.get_by_text("Reddet", exact=True)
        if await reject.count() == 1 and await reject.is_visible():
            await reject.click(timeout=5000)
            dismissed = True
        if config.get("kapat"):
            close = page.locator(config["kapat"])
            if await close.count() == 1 and await close.is_visible():
                await close.click(timeout=5000)
                dismissed = True
        return dismissed

    async def get(self, url, program, listing=False):
        if self.http:
            return await self.http_get(url)
        from playwright.async_api import Error, TimeoutError as PlaywrightTimeout
        page = await self.context.new_page()
        try:
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Error as exc:
                # A Chromium connection reset is a transport failure, not a
                # selector failure. Read the same public URL once with urllib.
                # HTTP denials, challenges and certificate errors never use this path.
                if "net::ERR_CONNECTION_RESET" not in str(exc):
                    raise
                print(f"Bağlantı sıfırlandı; aynı açık sayfa HTTP ile okunuyor: {url}", flush=True)
                return await self.http_get(url)
            if response and response.status >= 400:
                raise ValueError(f"HTTP {response.status}: {url}")
            if listing:
                config = SITELER[program]
                ready = page.locator(config["kart"])
                if config.get("bos"):
                    ready = ready.or_(page.locator(config["bos"]).filter(has_text="kampanyamız bulunmamaktadır"))
                await ready.first.wait_for(state="attached", timeout=30000)
                for _ in range(50):
                    before = await page.locator(config["kart"]).count()
                    visible_before = await page.locator(config["kart"] + ":visible").count()
                    button = page.locator(config["daha"]).first
                    if not await button.count() or not await button.is_visible() or not await button.is_enabled():
                        break
                    # Some Bankkart 'all campaigns' links navigate instead of loading more.
                    href = await button.get_attribute("href")
                    if href and not href.startswith(("#", "javascript:")):
                        break
                    await self.dismiss_overlays(page, config)
                    try:
                        await button.click(timeout=5000)
                    except PlaywrightTimeout:
                        # Promotional windows can appear after the first check.
                        if not await self.dismiss_overlays(page, config):
                            raise
                        await button.click(timeout=5000)
                    try:
                        await page.wait_for_function("([selector, n, v]) => {const a=[...document.querySelectorAll(selector)]; return a.length>n || a.filter(e=>e.getClientRects().length).length>v}", arg=[config["kart"], before, visible_before], timeout=5000)
                    except PlaywrightTimeout:
                        break
            return await page.content()
        finally:
            await page.close()


async def collect(program, fetcher, rules, limit):
    config = SITELER[program]
    urls = [config["url"]]
    if program == "bankkart":
        # Visit every category, not the eight-card front page.
        urls = [config["url"] + "/" + slug for slug in BANKKART_KATEGORILER]
    campaigns = {}
    for url in urls:
        try:
            html = await fetcher.get(url, program, listing=True)
        except Exception as exc:
            raise ValueError(f"Liste okunamadı: {url} ({type(exc).__name__}: {exc})") from exc
        records = cards_from_html(html, program, url)
        if not records and program != "bankkart":
            raise ValueError("Liste seçicisi kampanya döndürmedi")
        for campaign in records:
            campaigns[campaign["id"]] = campaign
    entries = list(campaigns.values())
    entries.sort(key=lambda c: (c["url"] not in rules, not bool(c["kategori"])))
    semaphore = asyncio.Semaphore(3)
    async def enrich(campaign):
        try:
            async with semaphore:
                html = await fetcher.get(campaign["url"], program)
            text = detail_text(html, program)
            apply_rule(campaign, text, rules)
            return 1
        except Exception as exc:
            print(f"Detay okunamadı ({program}): {type(exc).__name__}", flush=True)
            return 0
    detail_success = sum(await asyncio.gather(*(enrich(c) for c in entries[:limit])))
    if not detail_success and entries:
        raise ValueError("Hiçbir detay sayfası okunamadı; önceki veri korundu")
    print(f"{program}: {len(entries)} kampanya, {detail_success} detay", flush=True)
    return entries


async def run(args):
    output = Path(args.output)
    old = json.loads(output.read_text(encoding="utf-8")) if output.exists() else initial_data()
    rules = json.loads((ROOT / "data/dogrulanmis-kosullar.json").read_text(encoding="utf-8"))
    fresh, errors = {}, {}
    async with Fetcher(args.http) as fetcher:
        for program in SITELER:
            try:
                fresh[program] = await collect(program, fetcher, rules, args.details)
            except Exception as exc:
                errors[program] = f"{type(exc).__name__}: {exc}"
                print(f"{program}: {errors[program]}", flush=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = merge_results(old, fresh, errors, now)
    atomic_write(output, result)
    print(f"Kaydedildi: {len(result['kampanyalar'])} kampanya; hesaplanabilir: {sum(bool(c.get('hesaplanabilir')) for c in result['kampanyalar'])}", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http", action="store_true")
    parser.add_argument("--details", type=int, default=80)
    parser.add_argument("--output", default=str(ROOT / "data/kampanyalar.json"))
    arguments = parser.parse_args()
    if arguments.details < 1:
        parser.error("--details en az 1 olmalı")
    raise SystemExit(asyncio.run(run(arguments)))
