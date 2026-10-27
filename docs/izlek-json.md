# İzlek JSON biçimi

İzlek JSON, yerel veriyi başka bir İzlek kurulumuna taşımak için kullanılan
sürümlü formattır. Veritabanı satır kimlikleri yerine `media_type` ve `tmdb_id`
birlikte kullanılır. Sezon ve bölüm referansları numaralarıyla kurulur. Böylece
dosya SQLite dosya yolundan ve kurulumdan bağımsız kalır.

## Kök alanlar

```json
{
  "schema_version": 3,
  "exported_at": "2026-10-03T18:00:00Z",
  "app_version": "0.1.0",
  "media": [],
  "tracking": [],
  "episodes": [],
  "favorites": [],
  "lists": []
}
```

- `media`: Film/dizi metadata'sı; dizilerde sezon ve bölüm metadata'sı iç içedir.
- `tracking`: Durum, manuel seçim bilgisi, `sort_order` kart sırası,
  `personal_rating`, `personal_note`, `dismissed` ve yerel zaman damgaları.
- `episodes`: İzlenen bölüm durumu ve izlenme zamanı.
- `favorites`: Durumdan bağımsız favori medya referansları.
- `lists`: Özel listeler, sıraları ve medya üyelikleri.

Token, authorization alanları, yerel cache yolları ve SQLite satır kimlikleri
export edilmez. Poster, backdrop ve bölüm görseli değerleri TMDb'nin taşınabilir
göreli yollarıdır; indirilen yerel görsel dosyaları JSON'a girmez.

## Dış kaynaklar

`TransferService` ayrıca şu dosyaları İzlek belgesine çevirip aynı birleştirme
kurallarına uygular:

- **Trakt JSON dizisi:** `watched-movies`, `watched-shows`, history, ratings ve
  watchlist dışa aktarımları. Eşleşme `ids.tmdb` ile yapılır; TMDb kimliği
  olmayan satırlar atlanır.
- **Letterboxd CSV:** dışa/içe aktarma sütunları. Çevrimdışı çalıştığı için
  `tmdbID` / `tmdb_id` sütunu zorunludur; Letterboxd yıldız puanı 1–10 kişisel
  puana çevrilir.

## Import ve birleştirme

Dosya önce boyut, biçim algılama ve (İzlek JSON için) Pydantic şema
doğrulamasından geçer. Preview bu aşamanın özetini gösterir; doğrulama sırasında
veritabanına yazılmaz. Onaylanan import tek SQLite transaction içinde uygulanır.

- Aynı `media_type + tmdb_id` tek medya olarak birleştirilir.
- Metadata için daha yeni `last_synced_at` korunur.
- Takip durumunda daha yeni `updated_at` esas alınır.
- Kişisel puan (1–10 veya `null`), not (en fazla 2000 karakter) ve öneri
  gizleme tercihi, kabul edilen takip kaydıyla birlikte birleştirilir.
  Yeni yedekte `null` puan, boş not ve `false` gizleme açık temizleme anlamına
  gelir. Eski yedekte olmayan alanlar mevcut kişisel veriyi silmez.
- Film/dizi kartlarının özel sırası `tracking.sort_order` ile taşınır. Alan
  sıfırdan başlayan konum veya `null` olabilir. Eski yedekte alan yoksa yerel
  özel sıra silinmez; dolu gelen sıra, kabul edilen takip kaydıyla birlikte alınır.
- Favoriler birleşim olarak ele alınır; import mevcut favoriyi kaldırmaz.
- İzlenmiş bölüm tekrar import ile izlenmemişe dönmez ve en yeni `watched_at`
  korunur.
- Liste adları büyük/küçük harfe duyarsız eşleştirilir. Mevcut liste korunur,
  eksik üyeler eklenir ve aynı medya üyeliği çoğaltılmaz.

## Şema sürümleri

`schema_version` zorunludur. Uygulama kendisinden yeni sürümlü dosyayı yazmadan
önce reddeder. Eski sürümler, `services/transfer.py` içindeki ardışık migration
tablosundan güncel şemaya dönüştürüldükten sonra doğrulanır. Yeni sürüm eklerken
önceki sürümden saf JSON sözlüğü dönüşümü eklenmeli; mevcut sürümün Pydantic
modeli yalnızca güncel belgeyi temsil etmelidir.

Sürüm 2, film/dizi kütüphanesinin özel kart sırasını ekler. Sürüm 1 yedekleri
otomatik dönüştürülür; sıra bilgisi olmayan kayıtlar mevcut eklenme tarihi
sırasını kullanır. Yalnız sürüm 1 destekleyen eski İzlek kurulumları sürüm 2
yedeklerini okuyamaz.

Sürüm 3 kişisel puan/not ve öneri gizleme tercihini ekler. Sürüm 1 ve 2
okunur; eksik kişisel alanlar korunur. Eski İzlek sürümleri sürüm 3 yedeklerini
okuyamaz. Kişisel notların da JSON içinde bulunduğunu dışa aktarırken dikkate al.
