import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('scrape', Path(__file__).resolve().parents[1] / 'scraper/scrape.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


class ScraperTests(unittest.TestCase):
    def test_turkish_number(self):
        self.assertEqual(s.number('1.250,50'), 1250.5)

    def test_cap_does_not_invent_reward(self):
        h = s.hints("1.250 TL'ye varan puan!")
        self.assertEqual(h['ustLimit'], 1250)
        self.assertIsNone(h['minHarcama'])
        self.assertNotIn('sabitKazanc', h)

    def test_date_range_variants(self):
        for text in ['1–30 Eylül 2026', '1 Eylül 2026 - 30 Eylül 2026', '01.09.2026 - 30.09.2026']:
            self.assertEqual(s.dates(text), ('2026-09-01', '2026-09-30'))
        self.assertEqual(s.dates('15 Ağustos–30 Eylül 2026'), ('2026-08-15', '2026-09-30'))

    def test_redemption_date_is_not_purchase_date(self):
        text = '3 Ekim - 3 Kasım 2026 puanlar KAMPANYA BAŞLANGIÇ VE BİTİŞ 1 - 30 Eylül 2026 BONUS GEÇERLİLİK 3 Ekim - 3 Kasım 2026'
        self.assertEqual(s.dates(text), ('2026-09-01', '2026-09-30'))
        self.assertEqual(s.dates('31 Şubat - 30 Eylül 2026')[0], None)

    def test_aspnet_forms_are_not_removed(self):
        html = '<form><div class="detail-content">1-30 Eylül 2026 kampanya</div></form>'
        self.assertIn('kampanya', s.detail_text(html, 'bankkart'))

    def test_current_selector_excludes_archive(self):
        html = '<div class="camp_cardsAll"><div class="card"><a href="/kampanyalar/live"></a><h3 class="card-text">Market kampanyası</h3></div></div><div id="gecmis"><div class="card"><a href="/kampanyalar/old"></a><h3 class="card-text">Eski</h3></div></div>'
        self.assertEqual(len(s.cards_from_html(html, 'maximum', s.SITELER['maximum']['url'])), 1)

    def test_review_requires_exact_hash_and_period(self):
        text = '1-30 Eylül 2026 market'; c = {'url': 'x'}
        rule = {'x': {'kosulHash': s.fingerprint(text), 'baslangic': '2026-09-01', 'bitis': '2026-09-30', 'sabitKazanc': 250, 'hesaplanabilir': True}}
        self.assertTrue(s.apply_rule(c, text, rule)['hesaplanabilir'])
        changed = s.apply_rule({'url': 'x'}, text+' yeni koşul', rule)
        self.assertNotIn('hesaplanabilir', changed)

    def test_single_purchase_grammar(self):
        c = {'baslik': 'Market alışverişinize toplam 1000 TL', 'program': 'bankkart', 'baslangic': '2026-09-01', 'bitis': '2026-09-30'}
        s.automatic_rule(c, 'tek seferde yapacağınız 5.000 TL ve üzeri her alışverişiniz ile 250 TL, toplam 1.000 TL Jest Lira. E-ticaret işlemleri kampanyaya dahil değildir.')
        self.assertEqual(c['sabitKazanc'], 250)
        self.assertEqual(c['ustLimit'], 1000)
        self.assertEqual(c['kanal'], 'fiziksel')

    def test_ambiguous_instalments_excluded(self):
        c = {'baslik': "Beymen'de 6 taksit", 'program': 'bonus', 'marka': 'Beymen', 'baslangic': '2026-09-01', 'bitis': '2026-09-30'}
        s.automatic_rule(c, 'Seçili ürünlerde peşin fiyatına 6 taksit')
        self.assertNotIn('hesaplanabilir', c)
        s.automatic_rule(c, 'Peşin fiyatına 6 taksit')
        self.assertEqual(c['taksitAy'], 6)

    def fixtures(self, n=12):
        old = s.initial_data()
        old['kampanyalar'] = [{'id': p+str(i), 'program': p} for p in s.SITELER for i in range(n)]
        fresh = {p: [{'id': p+str(i), 'program': p} for i in range(n)] for p in s.SITELER}
        return old, fresh

    def test_source_failure_preserves_previous_records(self):
        old, fresh = self.fixtures()
        old['kartlar'][0]['sahip'] = 'Local template'
        result = s.merge_results(old, fresh, {'bonus': 'timeout'}, 'now')
        self.assertEqual(len(result['kampanyalar']), 36)
        self.assertEqual(result['kaynaklar']['bonus']['durum'], 'hata')
        self.assertEqual(result['kartlar'][0]['sahip'], 'Local template')

    def test_drop_guard(self):
        old, fresh = self.fixtures(40)
        fresh['maximum'] = fresh['maximum'][:15]
        errors = {}
        result = s.merge_results(old, fresh, errors, 'now')
        self.assertIn('maximum', errors)
        self.assertEqual(len(result['kampanyalar']), 120)

    def test_minimum_gate(self):
        old, fresh = self.fixtures(5)
        with self.assertRaises(ValueError):
            s.merge_results(old, fresh, {}, 'now')

    def test_participation_only_transfers_same_period(self):
        old, fresh = self.fixtures()
        old['kampanyalar'][0].update(baslangic='2026-09-01', bitis='2026-09-30', katilim=True)
        fresh['maximum'][0].update(baslangic='2026-10-01', bitis='2026-10-31')
        result = s.merge_results(old, fresh, {}, 'now')
        self.assertNotIn('katilim', result['kampanyalar'][0])

    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'data.json'
            path.write_text('{"old":true}')
            s.atomic_write(path, {'kampanyalar': ['Türkçe']})
            self.assertEqual(json.loads(path.read_text())['kampanyalar'][0], 'Türkçe')
            self.assertEqual(len(list(Path(temp).iterdir())), 1)


if __name__ == '__main__':
    unittest.main()
