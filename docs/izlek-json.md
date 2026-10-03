# İzlek JSON biçimi

İzlek JSON, yerel veriyi başka bir İzlek kurulumuna taşımak için kullanılan
sürümlü formattır. Veritabanı satır kimlikleri yerine `media_type` ve `tmdb_id`
birlikte kullanılır. Sezon ve bölüm referansları numaralarıyla kurulur. Böylece
dosya SQLite dosya yolundan ve kurulumdan bağımsız kalır.

## Kök alanlar

```json
{
  "schema_version": 1,
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
- `tracking`: Durum, manuel seçim bilgisi ve yerel zaman damgaları.
- `episodes`: İzlenen bölüm durumu ve izlenme zamanı.
- `favorites`: Durumdan bağımsız favori medya referansları.
- `lists`: Özel listeler, sıraları ve medya üyelikleri.

Token, authorization alanları, yerel cache yolları ve SQLite satır kimlikleri
export edilmez. Poster, backdrop ve bölüm görseli değerleri TMDb'nin taşınabilir
göreli yollarıdır; indirilen yerel görsel dosyaları JSON'a girmez.

## Import ve birleştirme

Dosya önce boyut, JSON ve Pydantic şema doğrulamasından geçer. Preview bu
aşamanın özetini gösterir; doğrulama sırasında veritabanına yazılmaz. Onaylanan
import tek SQLite transaction içinde uygulanır.

- Aynı `media_type + tmdb_id` tek medya olarak birleştirilir.
- Metadata için daha yeni `last_synced_at` korunur.
- Takip durumunda daha yeni `updated_at` esas alınır.
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
