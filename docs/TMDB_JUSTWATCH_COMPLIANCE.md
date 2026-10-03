# TMDB / JustWatch uyumluluk denetimi

Bu denetim, release öncesinde TMDB API Terms of Use, TMDB FAQ/branding ve
TMDB watch-provider endpoint belgelerine göre yapılmıştır. Bu belge hukuki
görüş değildir; şartlar ve marka varlıkları release anında yeniden kontrol
edilmelidir.

| Alan | Durum | İzlek'teki karşılık / gereken işlem |
| --- | --- | --- |
| Resmî TMDB bildirimi | Uyumlu | Ayarlar → Hakkında ekranında şu metin görünür: `This product uses the TMDB API but is not endorsed or certified by TMDB.` |
| About/Credits veri kaynağı | Uyumlu | Hakkında ekranı film, dizi, kişi, puan ve görsellerin TMDB'den; takip/favori/listelerin ise yalnızca yerel İzlek verisi olduğunu ayırır. Detay ekranları da kaynak etiketini gösterir. |
| Onaylı TMDB logosu | **Release engeli** | TMDB, değiştirilmemiş onaylı logo ister. Bu çalışma ortamı resmî SVG'yi indiremediği için sahte veya yeniden çizilmiş bir logo eklenmedi. Release öncesinde resmi logos & attribution sayfasındaki SVG dosyası değiştirilmeden `resources/branding/` altına eklenmeli ve Hakkında ekranında gösterilmelidir. |
| Logo baskınlığı | **Logo eklenince doğrulanacak** | TMDB logosu İzlek markasından küçük, İzlek markasından daha az görünür, oranı/renkleri değiştirilmemiş olmalıdır; endorsement izlenimi vermemelidir. |
| API token | Uyumlu | API Read Access Token yalnızca `Authorization: Bearer` başlığında gönderilir; UI, log, export, SQLite ve CI secret'larına yazılmaz. |
| Image URL'leri | Uyumlu | URL'ler TMDB `/configuration` yanıtının `secure_base_url`, desteklenen boyut ve `file_path` birleşiminden kurulur; `original` seçilmez. |
| Görsel cache | Uyumlu | XDG cache'teki TMDB görselleri 180 gün sonunda kullanılmadan önce silinir; indirme ve cache UI thread'i dışında yapılır. |
| SQLite metadata / provider cache | **Release engeli** | 24 saat freshness yenileme kararını yönetir ancak offline fallback için saklanan TMDB metadata'sı, sezon bilgisi ve provider JSON'u henüz altı aylık fiziksel saklama sınırıyla temizlenmez. Release öncesinde kişisel tracking verisini koruyup yalnız TMDB alanlarını en geç 180 günde temizleyen migration/cleanup eklenmelidir. |
| Watch providers / JustWatch | Uyumlu | TR provider verisi yalnız `flatrate`, `rent` ve `buy` gruplarında gösterilir; arayüz `İzleme seçenekleri JustWatch tarafından sağlanır` metnini ve TMDB'nin verdiği linki kullanır. |

## Kaynaklar

- [TMDB FAQ: attribution, logo ve prominence](https://developer.themoviedb.org/docs/faq)
- [TMDB API Terms: attribution ve altı aylık cache sınırı](https://www.themoviedb.org/api-terms-of-use)
- [TMDB Logos & Attribution: onaylı SVG logolar](https://www.themoviedb.org/about/logos-attribution)
- [TMDB Image Basics: configuration tabanlı URL oluşturma](https://developer.themoviedb.org/docs/image-basics)
- [TMDB Watch Providers: JustWatch attribution zorunluluğu](https://developer.themoviedb.org/reference/tv-series-watch-providers)

TMDB markası için yalnız `TMDB` veya `The Movie Database` adı kullanılmalıdır.
TMDB'nin verdiği metadata ve görseller, İzlek'in kişisel tracking verisinden
ayrı kaynak veridir.
