# TMDB / JustWatch uyumluluk denetimi

Bu denetim, release öncesinde TMDB API Terms of Use, TMDB FAQ/branding ve
TMDB watch-provider endpoint belgelerine göre yapılmıştır. Bu belge hukuki
görüş değildir; şartlar ve marka varlıkları release anında yeniden kontrol
edilmelidir.

| Alan | Durum | İzlek'teki karşılık / gereken işlem |
| --- | --- | --- |
| Resmî TMDB bildirimi | Uyumlu | Ayarlar → Hakkında ekranında şu metin görünür: `This product uses the TMDB API but is not endorsed or certified by TMDB.` |
| About/Credits veri kaynağı | Uyumlu | Hakkında ekranı film, dizi, kişi, puan ve görsellerin TMDB'den; takip/favori/listelerin ise yalnızca yerel İzlek verisi olduğunu ayırır. Detay ekranları da kaynak etiketini gösterir. |
| Onaylı TMDB logosu | Uygulandı (2026-10-04) | Resmî logos & attribution sayfasının blue short SVG'si özgün renk/geometriyle `resources/images/tmdb.svg` içine eklendi; Ayarlar → Hakkında gösterir. |
| Logo baskınlığı | Uygulandı | Logo Hakkında kartında 116×16 çerçevede PreserveAspectFit ile görünür; ana İzlek markasının yerini almaz. |
| API token | Uyumlu | API Read Access Token yalnızca `Authorization: Bearer` başlığında gönderilir; UI, log, export, SQLite ve CI secret'larına yazılmaz. |
| Image URL'leri | Uyumlu | URL'ler TMDB `/configuration` yanıtının `secure_base_url`, desteklenen boyut ve `file_path` birleşiminden kurulur; `original` seçilmez. |
| Görsel cache | Uygulandı | İstek sırasındaki yaş kontrolüne ek olarak açılışta ve saatlik bakımda eski görseller temizlenir. Kütüphane `.keep` işaretleri elle cache temizliğinden korur; 180 günlük retention yine de siler ve çevrimiçiyken yeniden indirilir. |
| SQLite metadata / provider cache | Uygulandı | Arka plan bakımında 180 günlük uzak alanlar temizlenir; user_media, episode_progress, custom_list ve custom_list_item satırları ile ilişkisel kimlikler (tmdb_id, season_number, episode_number) korunur. Provider/credits/video/öneri yanıtlarının bağımsız sync tarihleri başarısız endpoint'lerde ilerletilmez. Sezon ve bölüm cache'i kendi `last_synced_at` değerlerini kullanır; bilinmeyen tarihler için medya oluşturma tarihi muhafazakâr sınırdır. JSON import süresi dolmuş TMDb alanlarını yazmaz (`metadata_skipped`) ve ardından prune çalıştırır. |
| Watch providers / JustWatch | Uyumlu | Seçilen bölgenin (varsayılan TR; Ayarlar → İzleme bölgesi) provider verisi yalnız `flatrate`, `rent` ve `buy` gruplarında gösterilir; arayüz `İzleme seçenekleri JustWatch tarafından sağlanır` metnini ve TMDB'nin verdiği linki kullanır. |

## Kaynaklar

- [TMDB FAQ: attribution, logo ve prominence](https://developer.themoviedb.org/docs/faq)
- [TMDB API Terms: attribution ve altı aylık cache sınırı](https://www.themoviedb.org/api-terms-of-use)
- [TMDB Logos & Attribution: onaylı SVG logolar](https://www.themoviedb.org/about/logos-attribution)
- [TMDB Image Basics: configuration tabanlı URL oluşturma](https://developer.themoviedb.org/docs/image-basics)
- [TMDB Watch Providers: JustWatch attribution zorunluluğu](https://developer.themoviedb.org/reference/tv-series-watch-providers)

TMDB markası için yalnız `TMDB` veya `The Movie Database` adı kullanılmalıdır.
TMDB'nin verdiği metadata ve görseller, İzlek'in kişisel tracking verisinden
ayrı kaynak veridir.

2026-11-10: Resmî [API Terms of Use](https://www.themoviedb.org/api-terms-of-use)
yeniden okundu (sayfa “last updated: October 20, 2023”). Kısıtlama metni:
“Cache, for longer than 6 months, any information obtained through or from
TMDB or the TMDB APIs.” İzlek bunu 180 günlük proje politikası olarak uygular.
Bu teknik uygulama hukuki onay veya kapsamlı marka sertifikasyonu anlamına
gelmez. Kişisel kayıt koruması ve cache temizliği regresyon testleri `tests/`
altında tutulur. Haricî JSON yedekleri uygulamanın saatlik bakımında
değiştirilmez; içe aktarmada süresi dolmuş TMDb metadata yazılmaz.
