# Hangi kart · Aylık kampanyalar

Maximum, Bankkart ve Bonus programlarına bağlı dört kartı, belirli bir alışverişin kampanya ve vade değeriyle karşılaştıran Türkçe statik uygulama. Hesaplar cihazda yapılır. Sunucu, veritabanı, üyelik veya kart numarası gerekmez.

## İlk kullanım

1. Uygulamayı açıp **Kartlarım & ayarlar** bölümüne girin.
2. Her kartın adını, sahibini, programını, hesap kesim gününü ve rengini girip karşılaştırmaya dahil edin. Kişisel bilgiler bilinmediği için dört kart başlangıçta kapalıdır. İlk programlar ve renkler düzenlenebilir şablondur; belirli bir fiziksel kart ürünü iddiası değildir.
3. Tutar, kategori, tarih, gerekiyorsa marka ve mağaza/internet kanalını seçin.
4. Önerinin gerekçesini ve bankanın koşullarını okuyun. Kampanyaya bankanın uygulamasından katıldıktan sonra ilgili kartın **katıldım** notunu işaretleyin.
5. Size özel kampanyaları elle ekleyin. Telefon ve bilgisayar arasındaki ayar aktarımı için yedek indirip diğer cihazda yükleyin.

Yedi başlangıç kategorisi Market, Akaryakıt, Yemek & kafe, Giyim, Elektronik & ev, Seyahat ve Online alışveriştir. Kategoriler ve hesap motoru `index.html` içindedir.

## Dosyalar

```text
index.html                              Arayüz, hesap motoru, yerel kayıt ve ICS
data/kampanyalar.json                    Herkese açık kart şablonları ve kampanyalar
data/dogrulanmis-kosullar.json           Metin özeti hash'ine bağlı gözden geçirilmiş kurallar
scraper/scrape.py                        Playwright toplayıcı
scraper/requirements.txt                 Python bağımlılıkları
.github/workflows/kampanya-guncelle.yml  Zamanlayıcı, kontroller ve Pages yayını
tests/                                  Hesap, takvim ve veri koruma kontrolleri
```

Arayüz CSS ve JavaScript'i tek HTML'dedir; ayrı paket derleme adımı veya CDN bağımlılığı yoktur. Kampanyalar JSON'dan okunur. Kişisel kartlar, katılım işaretleri ve elle eklenen kampanyalar **yalnız `localStorage` içinde** saklanır; GitHub'a gönderilmez. İndirilen ayar yedeği kişisel bilgileri içerir. Tarayıcı verilerini silmek yerel ayarları siler. Kalıcı kayıt engellenirse ekranda uyarı görünür.

`index.html` dosyasını diskten çift tıklayarak açmak, tarayıcının `fetch` kısıtlaması nedeniyle JSON'u otomatik okuyamayabilir. GitHub Pages üzerinden kullanın veya ayarlardan kampanya JSON'unu elle yükleyin. Son başarılı kamuya açık veri tarayıcıda önbelleğe alınır; ağ sorunu sırasında kullanılabilir. Bu, arayüzün kendisinin çevrimdışı yükleneceği garantisini vermez.

## Hesap yaklaşımı

- **Vade:** bir sonraki gerçek hesap kesim tarihi bulunur. Ayda olmayan 29–31 günleri ayın son gününe çekilir. Kesim günü yapılan işlemin mevcut ekstreye girdiği varsayılır. Son ödeme yaklaşık kesim + 10 gündür; ayarlardan değişir. Hafta sonu, bankanın işlem saati ve resmi son ödeme tarihindeki kaymalar modellenmez.
- **Vade değeri:** `tutar × aylık getiri × vade günü / 30`.
- **Kampanya:** harcama başına sabit tutar veya yüzdelik kazanç, varsa tavan ve harcama kademeleri. Nakit katsayısı 1, serbest puan 0,80, markaya kilitli puan 0,40. Katsayılar düzenlenebilir.
- **Taksit:** peşin fiyatı aynı, vade farksız ve eşit aylık taksitler için `tutar × aylık getiri × (taksit sayısı − 1) / 2`. İlk taksit normal son ödeme tarihinde varsayılır. Vade farkı olan teklifleri elle bu türde eklemeyin.
- **Sıralama:** her karta uyan tek en değerli kampanya seçilir; farklı kampanyalar birleştirilmez. Kampanya + taksit + vade değeri sıralanır. Fark 1 TL'den küçükse iki kart da uygun gösterilir.

Aylık %3, güncel piyasa oranı iddiası değil, kullanıcının değiştirebileceği bir varsayımdır. Bu basit karşılaştırma bileşik iskonto, vergi, puan kullanma tarihi veya kart borcu faizi hesabı değildir. Ekstre borcunun tamamının ödendiğini varsayar. Sonuç garanti nakit kazanç değil, koşullu yaklaşık ekonomik değerdir.

## Belirsiz kampanyalar

Toplayıcı başlıktan alt limit, üst limit, yüzdelik oran ve taksit **ipuçları** çıkarır. `1.250 TL'ye varan` ifadesini tek alışverişte 1.250 TL kazanılacakmış gibi yorumlamaz. Tarih veya koşulu net olmayan kayıtlar `tahmini: true`, `hesaplanabilir: false` ile listelenir ve sayısal sıralamaya katılmaz.

Sayısal hesap iki yoldan açılır:

1. Metni ve kampanya tarihleri doğrulanmış kural: `dogrulanmis-kosullar.json` içindeki URL, tam temizlenmiş metnin SHA-256 özeti ve başlangıç/bitiş tarihleri birlikte eşleşmelidir. Banka aynı URL'deki koşulu değiştirirse önceki kural devre dışı kalır.
2. Dar otomatik dil kuralları: Bankkart'ın açıkça “tek seferde ... ve üzeri her alışverişiniz ile ... TL” dediği teklifler veya markası, tarihleri ve tek taksit adedi açık olan peşin fiyatına taksitler. “Varan”, ürün grubuna göre değişen, ücretli veya başka koşullu taksit ifadeleri hesap dışında kalır.

Otomatik çözüm kart alt türü, işyeri/POS, kişisel uygunluk, önceki harcama ve kullanılmış müşteri limitini doğrulayamaz. Bunlar koşul uyarısında gösterilir. Bankanın uygulamasındaki kişiye özel teklifler web sitesinde görünmeyebilir. Bu nedenle bulunan kampanya sayısı, aynı sayıda teklifin hesaplanabildiği anlamına gelmez.

Marka eşleşmesi Türkçe harfleri ve noktalama farklarını normalleştirir ama alt dize eşleşmesi yapmaz. Marka boşsa markaya özel kampanyalar öneriye alınmaz. Katılım notları **kart + kampanya + tarih dönemi** ile anahtarlanır; yeni ayın aynı URL'deki kampanyasına eski katılım taşınmaz.

## Takvim

`.ics` dosyası tarayıcıda oluşturulur. 3, 6 veya 12 ay için gelecek dönem başlangıçlarında birer tam gün etkinliği üretir. Varsayılan dönemler **6–20 / 21–5**; alternatif **1–15 / 16–ay sonu**.

Etkinlik başlığında dönemde en sık öne çıkan kart vardır. Açıklamasında yedi kategorinin her biri için gün aralıkları, kart değişimleri, yaklaşık değer ve gerekçe bulunur. Hesapta ekrandaki örnek tutar kullanılır; markaya özel kampanyalar takvime alınmaz. Hatırlatma önceki gün Türkiye saatiyle 20.00'ye (17.00 UTC) ayarlanır. Takvim uygulamasının bildirim izni ve alarm desteği gerekir.

Sonraki ayların kampanyaları henüz bilinmediği için uzak tarihler çoğunlukla vadeye dayanır. Takvim bir abonelik değildir; indirilen dosya otomatik değişmez. Güncel veriyle yeniden oluşturulabilir. Aynı dönemlerin UID'si sabittir; yeniden içe alma davranışı takvim uygulamasına bağlıdır.

## GitHub Pages kurulumu

Depo adı: **`aylik-kampanyalar`**. Görünen uygulama adı: **Aylık kampanyalar / Hangi kart**.

1. Dosyaları `main` dalına koyun.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions** seçin.
3. **Actions → Kampanyaları güncelle ve yayımla → Run workflow** ile ilk yayını başlatın.
4. Yayın adresi Pages ayarlarında ve Actions `github-pages` ortamında görünür.

Yayın adımı yalnız `index.html` ve `data/kampanyalar.json` dosyalarını yayımlar. Repo herkese açıksa kaynak kodu ve repodaki JSON da herkese açıktır; gerçek kişisel kart bilgilerini kamuya açık JSON'a yazmayın. Arayüzdeki yerel kart ayarları repoya aktarılmaz.

Zamanlayıcı **ayın 1 ve 15'inde 03.00 UTC / Türkiye saatiyle 06.00** çalışır. GitHub zamanlanmış görevleri geciktirebilir; kesin dakika garantisi yoktur. Herkese açık depolarda uzun süre etkinlik olmazsa GitHub zamanlanmış görevleri devre dışı bırakabilir. Actions ekranındaki durumu kontrol edin.

Workflow testleri çalıştırır, gerektiğinde Chromium kurar, veriyi toplar, değişen JSON'u bot hesabıyla `main` dalına işler ve aynı çalışmada Pages'i yayımlar. Böylece bot commit'inin yeni bir workflow tetiklemesine bağımlı değildir. Toplayıcı hata verse bile son geçerli veriyi yayımlar, ardından hata bildiren bir job başarısız olur. Chromium kurulumunun veya testlerin başarısızlığı güncelleme ve yayını durdurur; mevcut Pages yayını kalır. Dal koruması botun commit atmasını engellerse workflow günlüklerinde görünür.

## Toplayıcıyı yerelde çalıştırma

Python 3.12+ ve Node.js 20+ önerilir.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scraper/requirements.txt
python -m playwright install chromium
python scraper/scrape.py
```

Chromium bulunmayan ortamlarda bankanın sunucuda oluşturduğu HTML'i okumak için:

```bash
python scraper/scrape.py --http --details 80
```

`--http` JavaScript düğmelerini çalıştırmaz; varsayılan otomasyon yolu Playwright'tır. Site bir erişim kontrolü koyarsa bunu aşmak için kullanılmamalıdır. `SITELER` sözlüğü seçicileri tek yerde toplar. Maximum'da arşivler dışarıda bırakılır. Bankkart'ta ana sayfadaki sekiz kayıt yerine 15 kategori gezilir ve URL ile tekilleştirilir. “Daha fazla” düğmesinde toplam/görünür kart sayısı artmayı bırakınca durulur. Banka başına varsayılan en fazla 80 detay, eşzamanlı en fazla 3 detay okunur; tüm liste kayıtları korunur.

Güvenlik eşikleri: toplam en az 30, banka başına en az 10 kayıt ve önceki banka sayısına göre %50'den fazla düşmeme. Başarısız bankanın eski kayıtları korunur; diğer bankalar güncellenebilir. Hiçbir banka başarılı değilse veya toplam 30'un altındaysa dosya değişmez. Yazma geçici dosya + atomik değiştirme ile yapılır. Eski JSON'daki kart şablonları korunur. Tarayıcıdaki katılım notları zaten toplayıcıdan bağımsızdır; varsa eski JSON katılım alanları yalnız aynı kampanya dönemine taşınır.

## Kontroller

```bash
node --test tests/engine.test.cjs
python -m unittest discover -s tests -p 'test_*.py'
```

Kontroller gerçek ay uzunlukları, artık yıl, yıl geçişi, alt limit ve tavan, puan katsayıları, kampanyaların birleşmemesi, marka/kart/kanal kapsamı, taksit hesabı, UTF-8 ICS satır katlama, takvim dönemleri, tarihi ödül kullanım tarihiyle karıştırmama, kaynak başına koruma ve atomik yazmayı kapsar.

## Resmî kaynaklar

- [Maximum kampanyaları](https://www.maximum.com.tr/kampanyalar)
- [Bankkart kampanyaları](https://www.bankkart.com.tr/kampanyalar)
- [Bonus kampanyaları](https://www.bonus.com.tr/kampanyalar)
- [GitHub Pages özel workflow belgeleri](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub zamanlanmış workflow davranışı](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
