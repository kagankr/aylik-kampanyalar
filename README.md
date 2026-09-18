# Hangi kart · Aylık kampanyalar

[Uygulamayı aç](https://kagankr.github.io/aylik-kampanyalar/)

Maximum, Bankkart ve Bonus kampanyalarını alışveriş tutarı ve kategorisine göre karşılaştırır. Her kartın en çok kazandıran tek kampanyasını bulur; önerilen kartı, kampanya adını, geçerli marka/hizmeti ve TL kazancını gösterir.

## Kullanım

1. Tutar ve kategori seçin. Tarih varsayılan olarak bugündür; isterseniz alışveriş kanalını daraltın.
2. Yüzde indirimler için kampanya öncesi tutarı girin.
3. Önerilen kartın altında kampanyanın geçerli olduğu markayı, ürün veya hizmeti ve koşullarını okuyun. Seyahat kategorisi otel, uçak bileti ve araç kiralama gibi farklı hizmetleri kapsar; öneri belirtilen hizmet ve markaya bağlıdır.
4. İsterseniz **Kartlarım & ayarlar** bölümünden dört kişisel kartınızı tanımlayın. Kart eklenmezse üç banka programı karşılaştırılır. Hesap kesim günü gerekmez.
5. Bankanın uygulamasından katıldıktan sonra **katıldım** notunu işaretleyin. Kişiye özel kampanyaları elle ekleyebilirsiniz.

## Hesap

- Sabit kazanç, tutarın yüzdesi veya harcama kademesine karşılık gelen tutar kullanılır; varsa kazanç tavanı uygulanır.
- Puanlar bankanın belirttiği TL karşılığıyla gösterilir. Kullanım türü ayrıca yazılır; nakit, serbest puan ve markaya özel puan için katsayı uygulanmaz.
- Vade, faiz/getiri, kesim tarihi ve taksitlerin zaman değeri hesapta yer almaz. Taksit sayısı yalnız kampanya bilgisi olarak kalır.
- Marka girişi yoktur. Seçili kategorideki markaya özel kampanyalar da karşılaştırılır; önerinin kapsamı açıkça gösterilir.
- Ayrı kampanyalar toplanmaz. Hiçbir teklif hesaplanamıyorsa kazanan kart uydurulmaz; neden gösterilir.
- Kullanılmış müşteri limiti, önceki alışverişler, kişisel uygunluk, kart alt türü ve gerçek işyeri/POS uygunluğu bilinmez. Sonuç koşulludur.

Başlıktaki “7.500 TL’ye varan” tutar tek alışveriş kazancı sayılmaz. Koşulu veya tarihi belirsiz kayıtlar listelenir ama sayısal sıralamaya alınmaz. `data/dogrulanmis-kosullar.json` içindeki incelenmiş kurallar URL, tarih ve koşul metninin SHA-256 özetiyle eşleşir; koşul değişirse kural uygulanmaz. Toplayıcı ayrıca dar ve açık tek alışveriş ifadelerini çözebilir.

## Takvim ve yerel kayıt

Takvim düğmesi, seçilen tutar ve kategoride kazanç sağlayan kampanyaların **son günleri** için `.ics` dosyası üretir. Etkinlikte kart, marka, kazanç ve koşullar bulunur. Önceki akşam Türkiye saatiyle 20.00 için hatırlatma eklenir. Takvim bir abonelik değildir ve otomatik değişmez.

Kartlar, katılım notları ve kişisel kampanyalar yalnız tarayıcıdaki `localStorage` içinde saklanır. Banka hesabına bağlanılmaz; kart numarası istenmez. Ayar yedeğiyle cihazlar arasında aktarılabilir. Eski sürüm yedekleri ve kart kayıtları okunur; eski vade/getiri ayarları kullanılmaz. Tarayıcı verilerinin silinmesi yerel kayıtları siler.

## Dosyalar

- `index.html`: tek dosyalık arayüz, hesap motoru, yerel kayıt ve takvim
- `data/kampanyalar.json`: halka açık kampanyalar ve boş kart şablonları
- `data/dogrulanmis-kosullar.json`: incelenmiş ve koşul metnine bağlı hesap kuralları
- `scraper/scrape.py`: Playwright toplayıcı
- `.github/workflows/kampanya-guncelle.yml`: zamanlayıcı, kontroller ve GitHub Pages yayını
- `tests/`: hesap, takvim ve veri koruma kontrolleri

## Otomasyon

GitHub Actions ayın **1 ve 15’inde 03.00 UTC / Türkiye saatiyle 06.00** için ayarlanmıştır. GitHub çalışmaları geciktirebilir. Elle güncellemek için **Actions → Kampanyaları güncelle ve yayımla → Run workflow** kullanılır. Pages kaynağı **GitHub Actions** olmalıdır.

Toplayıcı Maximum listesini, Bankkart’ın 15 kategori sayfasını ve Bonus listesini tarar. Meşru boş kategorileri tanır, çerez ve tanıtım pencerelerini normal kapatma düğmeleriyle kapatır. Daha fazla düğmesinde toplam veya görünür kampanya sayısı artmayı bırakınca durur. Chromium bağlantısı sıfırlanırsa aynı açık URL bir kez HTTP üzerinden okunabilir; erişim engelleri aşılmaz.

Banka başına varsayılan en fazla 80 detay, eşzamanlı en fazla üç detay okunur. İncelenmiş kurallar önceliklendirilir; tüm liste kayıtları korunur. En az 30 toplam kayıt, banka başına en az 10 kayıt ve önceki sayıya göre en fazla %50 düşüş aranır. Başarısız bankanın eski verisi korunur. Hiçbir banka başarılı değilse JSON değişmez. Yazma atomiktir. Kişisel kart ve katılım kayıtları güncellemeden bağımsızdır.

Workflow kontrolleri çalıştırır, JSON değişirse depoya işler ve Pages’i yayımlar. Toplama sorunu olursa son geçerli veri yayımlanır, hata ayrı job ile bildirilir. HTML veya kod değişikliği mevcut veriyi tekrar toplamadan yayımlanır. Herkese açık depoda özel kart bilgileri saklanmamalıdır; uygulamadaki kişisel ayarlar GitHub’a gönderilmez.

## Geliştirme

```bash
python -m pip install -r scraper/requirements.txt
python -m playwright install chromium
python scraper/scrape.py
node --test tests/engine.test.cjs
python -m unittest discover -s tests -p 'test_*.py'
```

`--http` seçeneği JavaScript düğmelerini çalıştırmadan sunucunun HTML’ini okur. `--details` detay sınırını değiştirir. Arayüzü GitHub Pages veya yerel HTTP sunucusunda açın; dosyaya çift tıklamak JSON okumasını engelleyebilir. Son geçerli kampanya verisi tarayıcıda önbelleğe alınır.

## Kaynaklar

[Maximum](https://www.maximum.com.tr/kampanyalar) · [Bankkart](https://www.bankkart.com.tr/kampanyalar) · [Bonus](https://www.bonus.com.tr/kampanyalar)
