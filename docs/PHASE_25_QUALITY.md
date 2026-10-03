# Faz 25 kalite kapısı

## Kapsam

Faz 25, mevcut davranışları yeniden tasarlamadan test paketinin kritik veri ve
ağ sınırlarını genişletir. Paketleme bu kalite kapısı temiz olmadan
başlatılmamalıdır.

## Tek komut

```bash
python scripts/quality.py
```

Komut sırasıyla Ruff ve tam pytest paketini çalıştırır. Qt testleri offscreen ve
software backend varsayılanlarıyla çalışır. GitHub Actions aynı komutu Python
3.11 üzerinde kullanır ve herhangi bir TMDb token secret'ı tanımlamaz.

## Güvence matrisi

| Alan | Otomatik güvence |
| --- | --- |
| TMDb client | Bütün kullanılan endpoint yolları, Bearer başlığı, modeller, güvenli hata eşleme ve sınırlı 429 retry |
| Repository | Gerçek migration uygulanmış SQLite üzerinde CRUD, sıralama, join, cascade ve hata sınırları |
| Takip / bölüm | Manuel durum koruması, otomatik durum matrisi, ilerleme kalıcılığı ve joined progress okumaları |
| Devam Et | Yayın tarihi/special filtreleri, ilk izlenmemiş bölüm ve yeni bölümlü tamamlanmış dizi |
| İstatistik | Boş durum, yerel aggregate değerleri, eksik runtime ve tür sıralaması |
| Import/export | Round-trip, tekrar import, referans doğrulama, güvenli hata, özel dosya izni ve `.json` uzantısı |
| Freshness | 24 saat sınırı, naive/aware zamanlar ve farklı UTC offset'leri |
| Token store | Keyring önceliği, keyring'siz fallback, migration, dosya izinleri ve whitespace reddi |
| Listeler / favoriler | CRUD, sıralama, çoklu üyelik, doğrulama, status bağımsızlığı ve bulunamayan kayıtlar |
| QML smoke | Offscreen açılış, gezinme, klavye, minimum boyut ve HiDPI; screenshot karşılaştırması yok |

`tests/conftest.py` gerçek TCP bağlantılarını suite genelinde engeller. HTTP
senaryoları `httpx.MockTransport` ile yerel ve deterministik çalışır.
