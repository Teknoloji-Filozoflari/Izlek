# İzlek Mimarisi

## Kapsam

İzlek, Linux öncelikli, tek kullanıcıya ait ve local-first bir masaüstü uygulamasıdır. Python 3.11+ temel dil, PySide6/Qt Quick arayüz katmanı, SQLAlchemy/SQLite kalıcı veri deposu ve TMDb tek çevrimiçi metadata kaynağıdır. Film/dizi kütüphaneleri, dashboard, favoriler, özel listeler ve detaylar yerel veritabanına bağlıdır; Keşfet merkezi TMDb client üzerinden çevrimiçi metadata alır. Tamamlanan fazlar [devir notunda](HANDOFF.md) tutulur.

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

Linux binary dağıtımı `packaging/izlek.spec` ile PyInstaller one-folder
çıktısından başlar. QML, SVG/desktop kaynakları ve Alembic migration dosyaları
paket içindeki mevcut `izlek/...` göreli konumlarını korur; bu nedenle çalışma
zamanındaki `__file__` tabanlı kaynak çözümü değişmez. Doğrulanan one-folder
çıktısı AppDir içine salt okunur uygulama payload'ı olarak yerleştirilir ve
`AppRun` yalnızca paketli executable'ı başlatır; XDG değişkenlerini uygulama
yanına yönlendirmez. x86_64 CI build'i glibc 2.28 tabanlı manylinux ortamında,
aynı tabana sahip PySide6 wheel constraint'iyle üretilir.

Kütüphane posterleri görünür GridView/ListView delegeleri tarafından istenir; controller bütün kütüphaneyi önceden indirmez ve aynı generation içindeki isteği tekilleştirir. Bölüm listesi yeniden kullanılan ListView delegeleriyle sanallaştırılır. Sayfadan ayrılma ilgili controller generation'ını geçersiz kılar ve başlamamış Future'ları iptal eder; geç gelen sonuç UI durumuna uygulanmaz. Faz 24 sentetik veri bütçeleri ve ölçümleri [performans profilinde](PHASE_24_PERFORMANCE.md) tutulur.

`ui/controllers/search_controller.py` film ve dizi aramasını ayrı işçilere gönderir, eski sorgu sonuçlarını geçersiz kılar ve QML'ye yalnızca sunuma hazır veri verir. `GlobalSearch.qml` klavye kısayolu, debounce ve sonuç listesini; `MediaDetailPage.qml` seçilen kaydın detayını gösterir. QML HTTP isteği yapmaz.

`services/movie_detail.py` film detayının TMDb bölümlerini paralel alır; başarılı metadata'yı `media_item` içinde saklar ve çevrimdışıyken son kopyayı okur. Takip durumu, favori ve liste üyeliği yalnızca `user_media` ve `custom_list_item` tablolarına yazılır. `ui/controllers/movie_detail_controller.py` önce local detayı yayımlar; `last_synced_at` 24 saatten eskiyse ağ yenilemesini aynı generation içinde arka planda yapar. Fresh kayıtta ağ isteği yapılmaz. Metadata yükleme kişisel durumu değiştirmez.

`services/tv_detail.py` dizi bölümlerini ve sezon listesini TMDb'den alır; sezon/bölüm metadata'sını `season` ve `episode` tablolarına upsert eder. Medya ve tam sezon cache'i ayrı `last_synced_at` değerleriyle 24 saatlik freshness uygular. Başarılı tam sezon isteği sezon sync zamanını günceller; özet satırının varlığı tek başına bölüm cache'i sayılmaz. İzlenen bilgisi sadece `episode_progress` tablosunda tutulur. Toplu işlem önce bütün hedef bölümlerin metadata'sını tamamlar, sonra tek SQLite transaction içinde progress'i günceller; eksik sezon çevrimdışıyken işlem yapılmaz. `TvDetailController` local veriyi önce yayımlar ve eski sezon isteklerinin sonucunu yok sayar.

`services/tv_status.py` bölüm ilerlemesinden otomatik dizi status kararını verir. `user_media.status_is_manual` kullanıcı seçimini korur; eski dolu status kayıtları `0002_status_source` migration'ıyla manuel kabul edilir. Otomatik status yalnızca bölüm ilerlemesi transaction'ında değişir. TMDb metadata yenilemesi status'u değiştirmez; yayınlanmış izlenmemiş bölüm sayısı detay ekranında ayrıca gösterilir. [Kurallar](status-automation.md).

`services/statistics.py`, yalnızca SQLite'taki takip, favori, metadata ve bölüm ilerlemesi kayıtlarından aggregate değerler üretir. Runtime değeri eksik olan izlenen film veya bölüm bulunduğunda ilgili süre ve tahmini toplam `None` olur; UI eksik veriyi açıklar. `StatisticsController` snapshot'ı işçi havuzunda okuyup dashboard'a verir. Türler, tamamlanmış film/dizi metadata'sından sayılır; istatistik sorgusu TMDb isteği yapmaz.

`services/transfer.py`, `TransferRepository` üzerinden tüm taşınabilir kayıtları okuyup `services/transfer_schema.py` içindeki sürümlü Pydantic modele çevirir. Export atomik dosya değişimiyle ve `0600` izniyle yazılır. Import önce dosyanın tamamını doğrular, sonra medya kimliği, bölüm numarası ve büyük/küçük harften bağımsız liste adı üzerinden tek SQLite transaction içinde birleştirir. Controller dosya ve veritabanı işlerini UI thread'i dışında yürütür; başarılı import sonrasında yerel dashboard, kütüphane, favori, liste ve istatistik controller'ları yenilenir. Şema alanları ve migration yaklaşımı [İzlek JSON belgesinde](izlek-json.md) tanımlıdır.

## Yerel veri ve güvenlik

Faz 16–18'in mevcut mimariye uyumu [denetim notunda](PHASE_16_18_ARCHITECTURE_AUDIT.md) açıklanır. Discover controller'ının ayrı bir servis olmadan doğrudan client kullanması mevcut bir sapmadır; yeni kod için hedef akış yukarıdaki servis katmanını korumalıdır. Model/oturum değişimi mevcut mimariyi veya tamamlanmış fazları yeniden tasarlama gerekçesi değildir; kapsam kuralları `AGENTS.md` içindedir.

`XDG_CONFIG_HOME/izlek`, `XDG_DATA_HOME/izlek`, `XDG_CACHE_HOME/izlek` ve `XDG_STATE_HOME/izlek/logs` kullanılır; tanımsız değişkenler için XDG varsayılanları geçerlidir. Yol hesaplamak dizin oluşturmaz. Pencere boyutu ve büyütülmüş durumu `XDG_CONFIG_HOME/izlek/window.ini` içine yazılır; ekran konumu saklanmaz. SQLite dosyası `XDG_DATA_HOME/izlek/izlek.sqlite3` altındadır; yeni dosya yalnızca kullanıcıya açık izinlerle oluşturulur. Açılışta Alembic `head` revizyonuna yükseltilir; değişiklikler `db/migrations/versions/` içinde sürümlenir. SQLite yabancı anahtarları her bağlantıda açılır. `MediaItem`, `Season` ve `Episode` metadata tutar; `UserMedia`, `EpisodeProgress` ve özel listeler kişisel veriyi ayrı tutar. Metadata upsert işlemleri takip durumuna ve izlenen bölümlere dokunmaz. `security/token_store.py`, tokenı önce sistem anahtarlığında tutar; anahtarlık kullanılamazsa `XDG_CONFIG_HOME/izlek/tmdb-token` dosyasını `0600` izniyle yazar ve kullanıcıyı bilgilendirir. Token SQLite, QSettings ve loglara girmez. `tmdb/client.py`, `GET /3/authentication` isteğini Bearer başlığıyla gönderir; doğrulama ve saklama UI thread'i dışında yapılır. Cache silinmesi kişisel takip verisini etkilememelidir. Gelecekteki ağır veritabanı işleri de Qt UI thread'i dışında çalıştırılacaktır.

## Test sınırları

`tests/` içindeki pytest testleri XDG/logging davranışını, migration ileri/geri
çalışmasını, SQLite kısıtlarını, repository CRUD akışlarını ve gerçek QML
sidebar tıklamalarını doğrular. Suite genelindeki guard gerçek TCP
bağlantılarını engeller; TMDb HTTP senaryoları `httpx.MockTransport` kullanır ve
CI gerçek token gerektirmez. Qt testleri offscreen platformda çalışır, QML
uyarılarını yakalar ve screenshot karşılaştırmasına dayanmaz.

`python scripts/quality.py`, önce Ruff'ı sonra tam pytest paketini çalıştıran
yerel ve CI kalite kapısıdır. Kapsam matrisi ve CI sınırları
[Faz 25 kalite notunda](PHASE_25_QUALITY.md) tutulur.

Paket smoke modu gerçek QML'i offscreen açar, migration ile SQLite dosyasını
oluşturur ve config/data/cache/state yollarının executable dizininin altında
olmadığını doğrular. AppImage workflow'u build sonrasında artifact'ı temiz
Ubuntu 22.04 ve 24.04 ortamlarında tekrar çalıştırır; ayrıntılar
[Faz 26 AppImage notunda](PHASE_26_APPIMAGE.md) yer alır.
