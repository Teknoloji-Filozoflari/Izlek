# İzlek Mimarisi

## Kapsam

İzlek, Linux öncelikli, tek kullanıcıya ait ve local-first bir masaüstü uygulamasıdır. Python 3.11+ temel dil, PySide6/Qt Quick arayüz katmanı, SQLAlchemy/SQLite kalıcı veri deposu ve TMDb tek çevrimiçi metadata kaynağıdır. Film/dizi kütüphaneleri, dashboard, favoriler, özel listeler ve detaylar yerel veritabanına bağlıdır; Keşfet merkezi TMDb client üzerinden çevrimiçi metadata alır.

## Katmanlar ve bağımlılık yönü

```text
QML → Python Controller/ViewModel → Service → Repository / TMDb Client
                                           ↘ SQLite / TMDb
```

QML yalnızca sunum ve kullanıcı etkileşimi içindir; SQL, HTTP veya test edilmesi gereken iş kararlarını içermez. Controller, UI olaylarını servislere aktarır. Servisler takip, liste, istatistik ve içe/dışa aktarma kurallarını uygular. Repository yalnızca yerel veriye, merkezi TMDb client yalnızca ağ API'sine erişir. Bağımlılıklar basit constructor parametreleriyle verilir; DI framework kullanılmaz.

## Paket düzeni

`src/izlek/app.py`, veritabanını hazırlayıp `QGuiApplication` ve `QQmlApplicationEngine` ile pencereyi açar. `ui/qml/Main.qml`, token yokken `OnboardingPage.qml`, kayıtlı token varken altı sayfalı `StackView` gezinmesini gösterir. `ui/qml/theme/Theme.qml`, koyu tema tokenlarını merkezileştirir. `ui/qml/components/`, bağımsız kontroller ve iki ekranda kullanılan `TokenForm.qml` içerir; diğer bileşen API'leri [bileşen belgesinde](components.md) açıklanır. `resources/icons/` uygulama ve sidebar ikonlarını, `resources/images/` örnek posterleri içerir. `core/paths.py` XDG dizinlerini hesaplar; `core/logging.py` yalnızca açıkça çağrılınca log dosyası açar. `db/models.py` yedi tabloyu, `db/engine.py` SQLite bağlantısını ve otomatik Alembic yükseltmesini, `repositories/` oturum tabanlı CRUD işlemlerini sağlar. `ui/controllers/token_controller.py`, QML ile token saklama ve TMDb client arasında köprüdür. `services/`, medya detayları, kütüphaneler, favoriler, özel listeler, bölüm ilerlemesi ve görseller için mevcut servisleri içerir.

TMDb URL ve yolları `tmdb/endpoints.py`, Pydantic API şemaları `tmdb/models.py`, HTTP ve hata davranışı `tmdb/client.py` içinde merkezileştirilir. İstemci ağ çağrıları için UI thread'i dışında kullanılmalıdır.

`services/image_service.py` TMDb configuration boyutlarını kullanarak poster ve backdrop indirmelerini işçi havuzunda yapar; sonuçları `Future[Path]` olarak verir. `cache/images.py` indirilen görselleri yalnızca XDG cache altında SHA-256 tabanlı adlarla ve atomik dosya değişimiyle saklar. Önbellek yoksa çevrimdışı placeholder kullanılır. Cache boyutu aynı işçi havuzunda ölçülebilir.

Özel listelerdeki üyelerin afişleri snapshot yayımlandıktan sonra worker'da
istenir; film/dizi kimliği birlikte kullanılır ve eski liste sonuçları yok
sayılır. Afiş güncellemeleri ayrı `itemsChanged` sinyaliyle medya seçimini
etkilemez. Disk cache yeniden açılışta ağ/configuration isteği olmadan okunur;
grid isteği için mevcut yüksek çözünürlüklü detay afişi de kullanılabilir.
Listeler medya seçicisi `MediaPickerDialog` içinde afişli, sanallaştırılmış
çoklu seçim kullanır. Seçimler sorgudan bağımsız medya türü/kimliğiyle tutulur;
controller tek bir `CustomListsService.add_many` transaction'ı başlatır.
Liste yazımları kapanışta tamamlanır, yalnız bekleyen okumalar iptal edilir.
180 günlük retention korunur.

Film/dizi özel sırası `0004_library_order` migration'ıyla nullable
`user_media.sort_order` alanında saklanır. Sırası olmayan eski kayıtlar eklenme
tarihine göre gösterilir. `LibraryController → LibraryOrderService →
MediaRepository` akışı görünür kart sırasını ayrı, sıralı yazım worker'ında
tek `BEGIN IMMEDIATE` transaction'ıyla kaydeder; status/favori/eklenme tarihi
korunur. Liste/üye sürüklemeleri mevcut liste konumlarını aynı şekilde topluca
yazar. QML yalnız koordinatı hedef karta çevirir. JSON sürüm 2 bu özel sırayı
taşır; sürüm 1 içe aktarma desteklenir.

Film/dizi kartları afiş veya başlıktan doğrudan sürüklenir. Ortak
`ReorderHandle`, `showHandle=false` ile görünmez olay alanı olarak kullanılır;
platform hareket eşiğini geçen basış detay açmaz. Kart içindeki favori/seçim
düğmeleri kendi olaylarını alır. Afiş önizlemesi ve kenarda otomatik kaydırma
yalnız QML etkileşimidir; mevcut sıralama kaydı ve veri şeması değişmez.
Liste sayfasındaki görünür tutamaçlar korunur.

Linux binary dağıtımı `packaging/izlek.spec` ile PyInstaller one-folder
çıktısından başlar. QML, SVG/desktop kaynakları ve Alembic migration dosyaları
paket içindeki mevcut `izlek/...` göreli konumlarını korur; bu nedenle çalışma
zamanındaki `__file__` tabanlı kaynak çözümü değişmez. Doğrulanan one-folder
çıktısı AppDir içine salt okunur uygulama payload'ı olarak yerleştirilir ve
`AppRun` yalnızca paketli executable'ı başlatır; XDG değişkenlerini uygulama
yanına yönlendirmez. x86_64 AppImage CI build'i Ubuntu 22.04 üzerinde glibc 2.35 tabanıyla,
test edilmiş PySide6 constraint'i ve paylaşılan Python kütüphanesiyle üretilir.

Kütüphane posterleri görünür GridView/ListView delegeleri tarafından istenir; controller bütün kütüphaneyi önceden indirmez ve aynı generation içindeki isteği tekilleştirir. Bölüm listesi yeniden kullanılan ListView delegeleriyle sanallaştırılır. Sayfadan ayrılma ilgili controller generation'ını geçersiz kılar ve başlamamış Future'ları iptal eder; geç gelen sonuç UI durumuna uygulanmaz.

`ui/controllers/search_controller.py` film ve dizi aramasını ayrı işçilere gönderir, eski sorgu sonuçlarını geçersiz kılar ve QML'ye yalnızca sunuma hazır veri verir. `GlobalSearch.qml` klavye kısayolu, debounce ve sonuç listesini; `MediaDetailPage.qml` seçilen kaydın detayını gösterir. QML HTTP isteği yapmaz.

Keşfet yönetmen/oyuncu araması `SearchController → DirectorSearchService → TmdbClient`
akışını kullanır. Kişi araması `search/person`, seçilen kişinin yapımları
`person/{id}/movie_credits` veya `tv_credits` ile okunur. Tipli yanıtlardan
oyuncu modunda cast, yönetmen modunda yalnız `crew.job == Director` alınır,
medya kimliğiyle tekilleştirilir ve
tarihe göre sıralanır. Yerel hariç tutma ve afiş akışı normal aramayla ortaktır.
Kişi ve yapım sonuçları generation kontrolüyle uygulanır; ağ/SQLite worker'da
çalışır. SQLite modeli ve kişisel kayıt kuralları değişmez. TMDb kişi
aramasının ilk sayfası kullanılır; dizi tarafı kişi/dizi credits kapsamındadır.
Kişinin tam yapım listesi controller belleğinde saklanır. `includeSaved` yalnız
bu snapshot'tan görünümü üretir; normal ad araması her zaman kayıtlıları ayıklar.
`ContentVisibilityService.snapshot` aynı SQLite okuma transaction'ında hariç
tutma kimliklerini ve takip durumlarını okur. Kayıt değişince snapshot'taki
rozetler yenilenir; yeni keşif görünümünde yeni kayıtlar gizlenir. Meta cache'i
kişisel kayıt sayılmaz. Cast sunumuna TMDb kişi kimliği eklenir; ortak
`CastGrid.actorActivated` → detay `actorSelected` → `Main.openActor` →
`DiscoverPage.showActor` akışıyla sorgu eşleşmesi olmadan kişi açılır.
API kaynakları: [Kişi araması](https://developer.themoviedb.org/reference/search-person),
[film yapımları](https://developer.themoviedb.org/reference/person-movie-credits),
[dizi yapımları](https://developer.themoviedb.org/reference/person-tv-credits).

Ana sayfa arama/keşfet kartlarının hızlı ekleme düğmesi
`QuickLibraryController → QuickLibraryService → repository` yolunu kullanır.
Sonuç özeti (başlık, gerçek yayın tarihi ve poster yolu) yalnız yeni medya
kaydına yazılır; tam detay senkronizasyonu yapılmış sayılmaz. Tek transaction
içinde film `PLANNED`, dizi `WATCHING` olarak eklenir. Mevcut status/favori,
metadata ve bölüm ilerlemesi korunur. UI thread'de disk/ağ işi yoktur; aynı
kayda tekrarlı tıklama tekilleştirilir, hata halinde yeniden deneme mümkündür.
Kartın kütüphane üyeliği SQLite'tan okunur ve sayfa yeniden görünür olduğunda
yenilenir; ekleme arama sorgusunu/sonuçlarını veya gezintiyi değiştirmez.

`services/movie_detail.py` film detayının TMDb bölümlerini paralel alır; başarılı metadata'yı `media_item` içinde saklar ve çevrimdışıyken son kopyayı okur. Takip durumu, favori ve liste üyeliği yalnızca `user_media` ve `custom_list_item` tablolarına yazılır. `ui/controllers/movie_detail_controller.py` önce local detayı yayımlar; `last_synced_at` 24 saatten eskiyse ağ yenilemesini aynı generation içinde arka planda yapar. Fresh kayıtta ağ isteği yapılmaz. Metadata yükleme kişisel durumu değiştirmez.

`services/tv_detail.py` dizi bölümlerini ve sezon listesini TMDb'den alır; sezon/bölüm metadata'sını `season` ve `episode` tablolarına upsert eder. Medya ve tam sezon cache'i ayrı `last_synced_at` değerleriyle 24 saatlik freshness uygular. Başarılı tam sezon isteği sezon sync zamanını günceller; özet satırının varlığı tek başına bölüm cache'i sayılmaz. İzlenen bilgisi sadece `episode_progress` tablosunda tutulur. Toplu işlem önce bütün hedef bölümlerin metadata'sını tamamlar, sonra tek SQLite transaction içinde progress'i günceller; eksik sezon çevrimdışıyken işlem yapılmaz. `TvDetailController` local veriyi önce yayımlar ve eski sezon isteklerinin sonucunu yok sayar.

`services/tv_status.py` bölüm ilerlemesinden otomatik dizi status kararını verir. Eski dolu status kayıtları `0002_status_source` migration'ıyla manuel kabul edilir; 2026-10-04 kullanıcı isteğiyle açık bölüm işlemleri bu eski seçimi de ilerlemeye göre günceller. Repository genel manuel koruması korunur; yalnız dizi ilerleme transaction'ı açık `override_manual=True` kullanır. TMDb metadata yenilemesi status'u değiştirmez; yayınlanmış izlenmemiş bölüm sayısı detay ekranında ayrıca gösterilir. [Kurallar](status-automation.md).

`services/statistics.py`, yalnızca SQLite'taki takip, favori, metadata ve bölüm ilerlemesi kayıtlarından aggregate değerler üretir. Süre toplamları yalnız pozitif runtime değeri bilinen izlenmiş film ve bölümleri toplar; eksik, sıfır veya negatif süreler dışarıda bırakılır. Bilinen süre yoksa toplam 0 olur. UI dışarıda kalan film/bölüm sayısını açıklar; izlenme sayaçları korunur. Son 12 aylık aktivite hem `user_media.watched_at` (film) hem bölüm `watched_at` değerlerini kullanır; `recent_history` günlük/geçmiş listesini üretir. `StatisticsController` snapshot'ı işçi havuzunda okuyup dashboard'a verir. Türler, tamamlanmış film/dizi metadata'sından sayılır; istatistik sorgusu TMDb isteği yapmaz.

`user_media.watched_at` WATCHED'e geçişte yazılır; WATCHED dışına çıkınca temizlenir. Film detayında İzlendi'ye yeniden basmak `rewatch=True` ile `rewatch_count` artırır ve tarihi yeniler; toplu status ve otomatik dizi teyidi yeniden izleme saymaz. JSON şema v4 bu alanları taşır.

`services/transfer.py`, `TransferRepository` üzerinden tüm taşınabilir kayıtları okuyup `services/transfer_schema.py` içindeki sürümlü Pydantic modele çevirir. Export atomik dosya değişimiyle ve `0600` izniyle yazılır. Import önce dosyanın tamamını doğrular, sonra medya kimliği, bölüm numarası ve büyük/küçük harften bağımsız liste adı üzerinden tek SQLite transaction içinde birleştirir. Controller dosya ve veritabanı işlerini UI thread'i dışında yürütür; başarılı import sonrasında yerel dashboard, kütüphane, favori, liste ve istatistik controller'ları yenilenir. Şema alanları ve migration yaklaşımı [İzlek JSON belgesinde](izlek-json.md) tanımlıdır.

## Yerel veri ve güvenlik

2026-10-18 kişisel özellikler fazında `0005_personal_preferences`,
`user_media.personal_rating` (nullable, 1–10 constraint), `personal_note` ve
`dismissed` alanlarını ekler. `PersonalMediaController → PersonalMediaService
→ repository` puan/not ve gizleme işlerini ayrı okuma ve sıralı yazım
worker'larında yürütür. Kabul edilen yazımlar kapanışta tamamlanır; eski
kişisel okumalar generation ile elenir. Bunlar metadata senkronizasyonundan,
takip durumu ve favoriden bağımsızdır. JSON v3 alanları taşır; v1/v2 içe
aktarma eksik kişisel alanları silmez. Retention kişisel satırlara dokunmaz.
`PersonalReview` film/dizi detayında kapalı başlar; sayfanın işlem satırında
Listeye Ekle yanındaki Puan ve not düğmesiyle satırın altında açılıp kapanır.
Açıklık yalnız bileşen durumudur, SQLite'a yazılmaz.
Kapatma taslağı korur; kayıt yine açık Kaydet eylemiyle yapılır.

`0006_watched_at_rewatch`, `user_media.watched_at` ve `rewatch_count`
alanlarını ekler. Film detayında İzlendi / Yeniden izledim aynı status
yolunu kullanır; JSON v4 alanları taşır ve v1–v3 içe aktarmada eksik alanlar
yerel tarih/sayıyı silmez.

`LibraryFilters` aynı anda durum, cache türü, yıl aralığı, maksimum süre ve
minimum TMDb puanı uygular. Film runtime'ı, dizi bildirilmiş en büyük bölüm
süresi kullanılır; bilinmeyen değerler etkin filtreden geçmez. Kütüphane
servisleri filtreden önce tür seçenekleri ve toplam istatistikleri üretir;
Favoriler/Devam Et bağımsızdır. Filtreler controller ömrü boyunca korunur.
QML seçim kimliklerini tutar; `LibraryController.batchApply` seçilen türdeki
kayıtları worker'da `BEGIN IMMEDIATE` transaction'ıyla değiştirir. Bütün
üyeler ve hedef liste yazımdan önce doğrulanır; status, favorite veya liste
üyeliği dışında alan yazılmaz. Dizi bölüm ilerlemesi değiştirilmez. Filtre
ve seçim modunda sürükleme kapalıdır, kaydedilmiş özel sıra korunur.

Öneri ayıklamasında repository, WATCHED ile dismissed kimliklerini birleştirir;
ham API cache'i korunur. DiscoverController tam API sayfasını bellekte tutar,
gizle/geri aç bildiriminde yeniden HTTP araması yapmadan ayıklar. Geç sayfa
yanıtı yeni gizleme kimliklerini geçersiz kılamaz. Açık ad/kişi araması bu
tercihle gizlenmez; mevcut kayıtlıları gizleme davranışı korunur. Ayarlar
gizlenenleri yerel sorgudan okur ve tek tek geri açar.

Discover controller'ının ayrı bir servis olmadan doğrudan client kullanması mevcut bir sapmadır; yeni kod için hedef akış yukarıdaki servis katmanını korumalıdır.

`XDG_CONFIG_HOME/izlek`, `XDG_DATA_HOME/izlek`, `XDG_CACHE_HOME/izlek` ve `XDG_STATE_HOME/izlek/logs` kullanılır; tanımsız değişkenler için XDG varsayılanları geçerlidir. Yol hesaplamak dizin oluşturmaz. Pencere boyutu ve büyütülmüş durumu `XDG_CONFIG_HOME/izlek/window.ini` içine yazılır; ekran konumu saklanmaz. SQLite dosyası `XDG_DATA_HOME/izlek/izlek.sqlite3` altındadır; yeni dosya yalnızca kullanıcıya açık izinlerle oluşturulur. Açılışta Alembic `head` revizyonuna yükseltilir; değişiklikler `db/migrations/versions/` içinde sürümlenir. SQLite yabancı anahtarları her bağlantıda açılır. `MediaItem`, `Season` ve `Episode` metadata tutar; `UserMedia`, `EpisodeProgress` ve özel listeler kişisel veriyi ayrı tutar. Metadata upsert işlemleri takip durumuna ve izlenen bölümlere dokunmaz. `security/token_store.py`, tokenı önce sistem anahtarlığında tutar; anahtarlık kullanılamazsa `XDG_CONFIG_HOME/izlek/tmdb-token` dosyasını `0600` izniyle yazar ve kullanıcıyı bilgilendirir. Token SQLite, QSettings ve loglara girmez. `tmdb/client.py`, `GET /3/authentication` isteğini Bearer başlığıyla gönderir; doğrulama ve saklama UI thread'i dışında yapılır. Cache silinmesi kişisel takip verisini etkilememelidir. Gelecekteki ağır veritabanı işleri de Qt UI thread'i dışında çalıştırılacaktır.

## Test sınırları

2026-10-18 kişiselleştirmesinde `ContentVisibilityService`, worker'da
`MediaRepository.excluded_tmdb_ids` üzerinden aramanın kayıtlı/izlenmiş
kimliklerini okur. Takip/favori, özel liste ve izlenmiş bölüm kaydı kişisel
kayıt sayılır; yalnız cache metadata'sı sayılmaz. Anahtar medya türü + TMDb
kimliğidir. Arama sonrası yerel yazım bildirimleri ağ isteğini tekrar etmeden
sonuçları ayıklar. Detay servisleri önerileri SQLite'taki WATCHED kayıtlarına
göre sunumda ayıklar; ham öneri metadata'sı korunur. Liste snapshot'ı medya
ve kişisel durumu tek outer join ile okur. Detay StackView öğeleri `mediaId`
tutar; öneriler push edilir, Geri tek öğe pop edip önceki kimliği yükler.
Discover, puan filtresi ve oy eşiğini koruyarak popularity.desc kullanır.

2026-10-18 denetiminde film/dizi controller'larının kabul edilmiş kişisel
yazımları ayrı, sıralı worker'a taşındı. Sayfa geçişi yalnız okuma/görsel
işlerini iptal eder; önceki sayfanın başarılı yazımı yerel modelleri yine
yeniler. Kapanış yazım kuyruğunu tamamladıktan sonra servisi kapatır. JSON
aktarımında bilinen metadata bölümleri doğrulanmış türlerle saklanır; eski
oyuncu kayıtları sunumda da doğrulanır. `scripts/run_dev.py`, kaynak kodu
proje içi `.dev-data/` XDG dizinleri ve null keyring ile çalıştırır.

2026-10-04 sekme performans düzeltmesinde kütüphane ve Devam Et modellerinin
bildirimi `itemsChanged` ile yükleme/durum bildirimlerinden ayrıldı. Görsel
sonuçları `posterAvailable` / `imageAvailable` ile yalnız ilgili QML kartını
günceller; bütün liste tekrar oluşturulmaz. Başarılı görsel URL'leri aynı
medya/yol için sekme dönüşünde korunur; placeholder sonraki yenilemeyi
engellemek üzere cache'lenmez. ImageService disk-cache okumalarını worker'da
yapar; TMDb configuration kilidi bekleyen istek tablosunun kilidinden
ayrıdır, bu nedenle config ağ isteği UI çağrısını bekletmez. Devam Et
anahtarlık okuması ve HTTP istemcisi kurulumu da worker'dadır.
StackView gezintisi Immediate kullanır; kütüphane açılışı tek yenileme yapar.
Mevcut kart varken loading skeleton gösterilmez; grid çerçevesi taşan çizimi
kırpar. Görsel saklama bakımını her detay görselinden sonra tetiklemek
yerine başarılı kişisel yazım bildirimi tetikler; mevcut .keep işaretleri
tekrar yazılmaz.

Film ve dizi detayındaki oyuncu fotoğraf kartları `CastGrid.qml` üzerinden
ortak gösterilir. Film servisi de oyuncu `profilePath` değerlerini sunar;
MovieDetailController mevcut ImageService.profile akışını kullanır ve kayıt
sonrasında fotoğrafları korur. Dizi detayında yalnız Önerilen Diziler şeridi
vardır; Benzer Diziler bölümü kaldırılmıştır. Film detayının alt bilgileri
diziyle aynı responsive sütun düzenini ve sabit genişlikli afiş kartlarını
kullanır. Kullanıcının sonraki isteğiyle film detayında da Benzer Filmler
kaldırılmıştır; yalnız Önerilen Filmler şeridi gösterilir.

2026-10-04 Devam Et denetimi, eski ilerlemesi olsa bile `UserMedia.status`
boş dizileri dışarıda bırakır. `list_continue_candidates(tracked_only=True)`
yalnız bu seçim için kullanılır; kütüphane/favori sorgularının varsayılanı
korunur. Hızlı İzlendi, `TvDetailService.set_episode_watched` içindeki isteğe
bağlı `require_in_library=True` ile aynı yazım transaction'ında üyeliği ve
bölümün yayınlanmış normal bölüm olmasını doğrular. Detay ekranındaki açık
bölüm işlemleri mevcut davranışını korur. Liste yükleme ve ilerleme yazımı
ayrı Future'larda tutulur; liste yenileme başlatılmış kişisel yazımı iptal
etmez. Geç liste/görsel sonuçları generation ile elenir, başarılı ilerleme
bildirimi ise diğer yerel özetlerin yenilenmesi için korunur.

2026-10-04 dizi detay düzenlemesinde oyuncuların `profile_path` değerleri
servisten `profilePath` olarak controller'a taşınır. `ImageService.profile()`
TMDb configuration profile boyutlarından 185 piksel veya daha büyük bir
boyut seçip mevcut güvenli indirme/disk cache akışını kullanır. Controller
eski generation sonuçlarını yok sayar ve sezon/durum güncellemelerinde hazır
oyuncu görsellerini korur. QML oyuncu kartlarını Flow, alt bilgileri dar
pencerede tek sütuna geçen GridLayout, benzer ve önerileri mevcut
HorizontalMediaStrip bileşeniyle gösterir.

2026-10-04 görsel düzenlemesinde Keşfet, `StackView` indeks 0'daki Ana Sayfa
oldu; arama girdisi ve film/dizi sonuçları burada inline gösterilir, detaydan
geri gelince sorgu ve sonuçlar korunur. Ana Sayfa'da Ctrl+K girdiye odaklanır;
diğer sekmelerde mevcut global arama kısayolu çalışır.
Ana Sayfa'daki tek medya seçimi soldadır; Film/Dizi hem keşfet hem arama
endpoint'ini belirler. Açık sorguda medya değişince aynı metin yeni kategoriyle
yeniden aranır. Arama yanında ayrı medya seçimi yoktur. Puan SpinBox'ları
0–100 tamsayıyı 0–10 puan olarak salt okunur etiketle gösterir; odak kaybında
metin parse edilmez, Uygula yalnız mevcut değerleri controller'a aktarır.
İndeks 4 İstatistikler'dir (Ctrl+5). Devam Et yalnız Diziler'dedir; kütüphane
sekme altı istatistikleri kaldırılmıştır. Kullanıcının sonraki isteğiyle Takibim ve Favorilerim İstatistikler sayfasından kaldırılmıştır; sayfa yalnız istatistik controller'ını yeniler.
Film kütüphanesi de diziler gibi tüm takip durumlarını tek grid'de gösterir;
ekleme `PLANNED`, açık İzlendi düğmesi `WATCHED`, İzlenmedi düğmesi `PLANNED`
kaydeder. Önceki film durumları arka planda değiştirilmez.
Devam Et'te adet sınırı yoktur; yalnız yereldeki normal sezon bölümleri
değerlendirilir. Takip/ilerleme başlamış ve yayınlanmış izlenmemiş bölümü olan
diziler çıkar; sonraki sezonun bölüm metadata'sı yüklenmediyse bilinmeyen bölüm
uydurulmaz veya kullanıcı isteği olmadan tüm sezonlar ağdan indirilmez.
`StatisticsRepository.watched_episode_activity()` medya, bölüm ve gerçek
izleme tarihini tek join ile okur. `StatisticsService` 12 aylık bölüm sürelerini,
izlenmiş içerik türlerini ve ilk beş dizi süresini Python'da hazırlar. Film
izleme tarihi tutulmadığından aylık grafiğe film eklenmez; `updated_at`
izleme tarihi olarak kullanılmaz. 2026-10-04 kullanıcı isteğiyle eksik runtime süre toplamına katılmaz;
film, bölüm ve toplam ekran süresi bilinen pozitif sürelerden gösterilir. Controller yalnız ilk beş dizi posterini
mevcut görsel servisiyle worker'da ister. Yeni migration veya kişisel veri
yazımı eklenmedi. QML yalnız hazır verinin çizimini ve kullanıcı olaylarını yapar.

2026-10-04 denetiminde `MetadataRetentionService` eklendi. `CacheController`
açılışta ve saatlik bakımda görseller ile uzak SQLite alanlarını 180 günlük
sınırla temizler; dosya/veritabanı işi worker'da çalışır. Kişisel tablolar ve
onların bağlı olduğu medya/sezon/bölüm kimlikleri silinmez. İlgili kütüphane
controller'ları bakım sonrası yenilenir. Opsiyonel TMDB yanıtlarının ayrı
sync tarihleri metadata JSON'unda tutulur. Kapanış, başlamamış görevleri iptal
eder; çalışan yazma işlemlerinin tamamlanmasından sonra database/görsel
kaynakları bırakılır. Import ve retention kararları `BEGIN IMMEDIATE`, export
ise açık `BEGIN` transaction'ıyla aynı SQLite snapshot'ını kullanır.

`tests/` içindeki pytest testleri XDG/logging davranışını, migration ileri/geri
çalışmasını, SQLite kısıtlarını, repository CRUD akışlarını ve gerçek QML
sidebar tıklamalarını doğrular. Suite genelindeki guard gerçek TCP
bağlantılarını engeller; TMDb HTTP senaryoları `httpx.MockTransport` kullanır ve
CI gerçek token gerektirmez. Qt testleri offscreen platformda çalışır, QML
uyarılarını yakalar ve screenshot karşılaştırmasına dayanmaz.

`python scripts/quality.py`, önce Ruff'ı sonra tam pytest paketini çalıştıran
yerel ve CI kalite kapısıdır.

Paket smoke modu gerçek QML'i offscreen açar, migration ile SQLite dosyasını
oluşturur ve config/data/cache/state yollarının executable dizininin altında
olmadığını doğrular. AppImage workflow'u build sonrasında artifact'ı temiz
Ubuntu 22.04 ve 24.04 ortamlarında tekrar çalıştırır; ayrıntılar
[release sürecinde](releases.md) yer alır.


RPM/Snap paketleri mevcut `packaging/izlek.spec` PyInstaller payload'ını
kullanır; uygulama katmanları değişmez. RPM build geçici rpmbuild topdir
kullanır ve yalnız uygulama payload'ı/masaüstü kaynaklarını arşivler. Snap
launcher XDG dizinlerini `SNAP_USER_COMMON` altında yönlendirir; host SQLite
veritabanını otomatik paylaşmaz. RPM/Snap workflow'ları elle başlatılır ve
mevcut tag tabanlı AppImage/.deb release akışından bağımsızdır.


Nix paketi PyInstaller payload'ı kullanmaz; Nixpkgs buildPythonApplication
ile kaynak wheel ve Python bağımlılıklarını kurar. wrapQtAppsHook Qt
plugin/QML yollarını Python wrapper'ına aktarır. Masaüstü dosyaları Nix
store'daki share altında; kişisel veriler mevcut XDG yollarındadır. Flake
checks paket kalite kapısı ve kurulu executable için offscreen smoke içerir.


Windows x64 paketleme aynı PyInstaller spec dosyasını kullanır; çıktı Inno
Setup ile kullanıcı başına kurulan EXE olur. Windows runner, paketli QML ve
migration dosyalarını, sessiz kurulum/açılış/kaldırmayı ve veri korumayı
doğrular. Ayarlar APPDATA, veritabanı/cache/loglar LOCALAPPDATA altındadır;
mutlak XDG değişkenleri izole geliştirme için önceliklidir. Windows profil
ACL'leri POSIX mod bitlerinden ayrıdır; token önce sistem keyring'ine gider.
Bu altyapının ilk gerçek Windows build koşusu henüz doğrulanmadı.

GitHub kaynaklarında yalnız README'nin kullandığı altı demo ekran görüntüsü
tutulur. Yerel çalışma raporları ve HANDOFF Git dışında kalır. Installer
payload'ı yalnız uygulama kaynaklarını/bağımlılıklarını ve lisansı içerir.
