# Meta veri kaynakları

İzlek kişisel takip verisini SQLite'ta tutar. Çevrimiçi katalog metadata'sı
yapılandırılabilir kaynaklardan gelir. **TMDb varsayılan ve zorunlu yedektir**;
Trakt, TVmaze ve OMDb Ayarlar'dan isteğe bağlı olarak açılır.

Bu belge hukuki görüş değildir; her kaynağın güncel şartları release öncesi
yeniden kontrol edilmelidir.

## Mimari

```text
QML Settings → MetadataSettingsController → MetadataSettings / CredentialStore
Service / Controller → MetadataClientRegistry.resolve(capability)
                     ↘ TmdbMetadataClient (çalışan katalog yolu)
                     ↘ Trakt / TVmaze / OMDb (ayar + yetenek matrisi; HTTP sonraki dilim)
```

- Ayarlar: `XDG_CONFIG_HOME/izlek/metadata-sources.json` (anahtar/token yok).
- TMDb token: mevcut `TokenStore` (keyring / `tmdb-token`).
- Trakt Client ID / OMDb API Key: `SourceCredentialStore` (keyring veya
  `0600` dosya). TVmaze ücretsiz genel API anahtarsızdır.
- İzleme sağlayıcısı bölgesi aynı ayar dosyasında tutulur; detay sunumu
  TMDb `watch/providers` yanıtından seçilen ISO ülke kodunu okur.

## Yetenek matrisi (uygulama ihtiyacı)

| Yetenek | TMDb | Trakt | TVmaze | OMDb |
| --- | --- | --- | --- | --- |
| Arama | ✓ | ✓ | ✓ (dizi) | — |
| Keşfet | ✓ | — | — | — |
| Detay | ✓ | ✓ | ✓ (dizi) | — |
| Sezon / bölüm | ✓ | ✓ | ✓ | — |
| Kişi / yönetmen | ✓ | kısmi | cast | — |
| Görseller | ✓ | — | — | — |
| Fragman | ✓ | — | — | — |
| Nerede izlenir | ✓ JustWatch | sınırlı | — | — |
| Başlık zenginleştirme | — | — | — | ✓ (ince) |

Ayarlar'daki anahtarlar kaynak başına yalnız bu tablodaki desteklenen
yetenekleri gösterir. Çalışma zamanında `MetadataClientRegistry` önce
etkin+uygulanan kaynağı seçer; katalog yeteneklerinde TMDb yedektir.

## OMDb — ticari olmama kapısı

OMDb API şartları kişisel / ticari olmayan kullanıma göredir (CC BY-NC tarzı
sınırlar). İzlek:

1. OMDb'yi birincil katalog yerine **yalnızca ince başlık zenginleştirme**
   yeteneği olarak listeler.
2. Kaynağı açmadan önce Ayarlar'da açık **kişisel / ticari olmayan kullanım**
   onayını zorunlu kılar.
3. Onay kaldırılırsa OMDb otomatik kapanır.
4. Anahtar keyring'de saklanır; SQLite, export ve QSettings'e yazılmaz.

Ticari dağıtım veya ürünleştirme planında OMDb kullanılmamalı; TMDb (veya
uygun lisanslı alternatif) tercih edilmelidir. Ayrıntılı alternatif karşılaştırması
proje analiz notlarındadır.

## JustWatch / bölge

Watch-provider verisi TMDb üzerinden JustWatch atıfı ile gelir. Bölge kodu
Ayarlar → İzleme bölgesi ile değişir (varsayılan `TR`). Uyumluluk kuralları
[TMDB_JUSTWATCH_COMPLIANCE.md](TMDB_JUSTWATCH_COMPLIANCE.md) belgesindedir.

## Kaynaklar

- [TMDB API Terms](https://www.themoviedb.org/api-terms-of-use)
- [Trakt API Use Policy](https://trakt.docs.apiary.io/)
- [TVmaze API](https://www.tvmaze.com/api)
- [OMDb API](https://www.omdbapi.com/)
