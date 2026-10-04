# İzlek devir notu

Son durum: **2026-10-04 kullanıcı referanslarına göre Keşfet ana sayfası, yazısız bölüm tikleri, ilerleme çubukları ve toplu İstatistikler görünümü uygulandı; v1.0.0 tag/release yayımlanmadı.** Önceki kod denetimi ve düzeltmeler korunur. Uygulama Linux için Python/PySide6/QML masaüstü uygulamasıdır; web uygulaması değildir. Ana proje kuralları [AGENTS.md](../AGENTS.md) ve [mimari notlarında](architecture.md) yer alır.

## 2026-10-04 denetimi

İçe/dışa aktarma, detay/sezon hata durumları, worker/database yaşam döngüsü,
gezinti, filtreler, test izolasyonu ve kaynak paketleme düzeltildi. Faz 31'deki
eksik resmî TMDB logosu ve uzak metadata saklama işi uygulandı; önceki faz
notlarının bu iki maddeyi açık gösteren ifadeleri tarihsel durumdur.
180 günlük bakım kişisel tabloları ve ilişkisel kimlikleri korur; başlık ve
diğer uzak alanlar yeniden indirilene kadar yer tutucu/eksik veri görünür.
Tam bulgular, doğrulamalar ve kalan paket yayın sınırları
[denetim raporunda](AUDIT_2026_10_04.md) bulunur. Sistem uygulaması yeniden
kurulmadı; temiz wheel denemesi yalnız geçici sanal ortamda yapıldı.

## Tamamlanan işler

### Ana sayfada tek tıkla kütüphaneye ekleme (2026-10-04)

- **Yapılanlar:** Kullanıcının `Resimler/arama.png` referansındaki gibi ana
  sayfa arama/keşfet kartlarının altına tam genişlikte sarı çerçeveli
  `+ Kütüphaneye Ekle` düğmesi eklendi. Detay/overlay açılmaz, sorgu ve sonuçlar
  korunur. Film `PLANNED`, dizi `WATCHING` eklenir; mevcut kişisel durum,
  favori, bölüm ilerlemesi ve detay metadata'sı değiştirilmez. Düğme işlemde
  `Ekleniyor…`, başarıda devre dışı `✓ Kütüphanede` olur. Başarısız kayıt
  sade hata ve yeniden deneme sunar; tekrar tıklama tekilleştirilir.
  SQLite işlemleri yeni küçük service/controller üzerinden worker'dadır.
  Özet başlık/tarih/poster yolu kaydedilir, tam detay tazeliği taklit edilmez;
  mevcut afiş disk cache'i kütüphane kartında tekrar kullanılabilir.
- **Değiştirilen önemli dosyalar:** quick_library.py,
  quick_library_controller.py, app.py, MediaGrid.qml, MediaCardDelegate.qml,
  DiscoverPage.qml, search/discover controller özetleri, ilgili testler,
  components.md, architecture.md ve bu not.
- **Test sonucu:** Ruff temiz; 196 test geçti. Film/dizi için arama kartından
  fare/klavye eklemesi, detay açılmaması, sorgunun korunması, tekrar aramada
  üyelik göstergesi, film/dizi aynı kimliği, kalıcılık, mevcut izlenmiş durum ve
  detay metadata'sının korunması, işlem hatası/yeniden deneme doğrulandı.
- **Manuel kontrol:** İzole veriler ve sahte TMDb ile gerçek Wayland ve
  X11/XWayland'da film/dizi eklemesi 1366×768/1920×1080 isteklerinde geçti;
  QML uyarısı yok. Ekran görüntüsü incelendi. Kullanıcı verisi/tokeni kullanılmadı.
- **Bilinen sorunlar:** Önceki desktop portal kayıt uyarısı sürer; canlı TMDb
  içeriğiyle kullanıcı denemesi yapılmadı. Kaynak değişikliği için açık eski
  uygulama yeniden başlatılmalıdır. Hızlı ekleme tam detay/bölüm indirmez;
  mevcut detay sayfası gerekli metadata'yı açılışta tamamlar.
- **Sonraki faz:** Kullanıcı denemesi.

### Listeler medya menüsü ve kalıcı afişler (2026-10-04)

- **Yapılanlar:** Listeler Medya Ekle seçicisi ortak Templates tabanlı
  FilterComboBox'a geçirildi; hover sırasında kaybolan KDE native popup
  çakışması kaldırıldı. Film/Dizi etiketi korunur, Escape yalnız menüyü kapatır.
  Liste üyelerinde afiş gösterilir; mevcut ImageService arka planda indirip
  XDG disk cache'e kaydeder. Yeniden açılışta cache'deki afişler ağ isteği
  olmadan kullanılır; detay afişi varsa grid için tekrar indirilmez.
  Film/dizi aynı TMDb kimliğiyle karışmaz; eski callback'ler yok sayılır.
  Afiş sinyali aday menüsünün seçimini sıfırlamaz. Token değişimi/kapanış
  kaynak sahipliği korunur; kişisel veriye migration/toplu yazım yok.
- **Değiştirilen önemli dosyalar:** ListsPage.qml, custom_lists.py,
  custom_lists_controller.py, image_service.py, app.py, liste/görsel testleri,
  smoke_display.py (`--hover-list-picker`), architecture.md ve bu not.
- **Test sonucu:** Ruff temiz; 192 test geçti. Liste CRUD/hover/Escape,
  film/dizi afiş ayrımı, eklemede indirme, yeniden açılışta HTTP/configuration
  isteği olmadan cache kullanımı ve eski afiş callback'i test edilir.
- **Manuel kontrol:** İzole verilerle gerçek Wayland ve X11/XWayland menüsünde
  iki seçenek hover boyunca görünür kaldı; 1366×768/1920×1080 istekleri,
  0 QML uyarısı. X11 çalışma alanı yüksekliği 1052 px uygular.
  Masaüstü testi sabit gecikme yerine liste yüklenmesini bekler.
- **Bilinen sorunlar:** Cache temizlenir/180 günlük saklama süresi dolarsa
  yeniden indirme gerekir. TMDb'de afiş yoksa/bağlantı kesilirse mevcut
  placeholder kullanılır. Önceki desktop portal kayıt uyarısı sürer.
  Açık eski uygulama kaynak değişikliği için yeniden başlatılmalıdır.
- **Sonraki faz:** Kullanıcı denemesi.

### KDE hover sırasında kaybolan filtre menüleri (2026-10-04)

- **Yapılanlar:** Sorun gerçek Wayland oturumunda üretildi: hover edilen
  delegate ve metni `visible=false` oluyor, ilk Film/Tüm türler satırı da
  kayboluyordu. Sistem KDE `Controls.ComboBox` QML'i kendi Menu/Repeater'ını
  aynı `delegateModel` üzerinde kullanır; uygulamanın özel ListView popup'ıyla
  çakışır. Metin rasterizer'ını değiştirmek sorunu gidermedi. `FilterComboBox`
  artık `QtQuick.Templates.ComboBox/ItemDelegate/Popup` kullanır; tüm görseller,
  metin, hover katmanı ve ok uygulama temasında tanımlıdır. Genel uygulama
  render backend'i değiştirilmedi; yeni bağımlılık yok.
- **Değiştirilen önemli dosyalar:** `FilterComboBox.qml`, `test_discover.py`,
  `scripts/smoke_display.py` (`--hover-filters` modu), `components.md` ve bu not.
- **Test sonucu:** Ruff temiz; **190 test geçti**. Mevcut menü testi görünen
  bütün satırlarda fare gezdirir ve tüm delegelerin görünür kaldığını doğrular.
  Kalıcı desktop hover testi ilk satır dahil menü metinlerini/görünürlüğünü
  kontrol eder; Film/Dizi fare seçimi de test edilir.
- **Manuel kontrol:** Gerçek Wayland'da önce boşalan menü ekran görüntüleri
  alındı; düzeltme sonrası Film/Dizi, tür ve ülke menülerinde bütün satırlar
  görünür kaldı. Yerel izole hover/piksel testi ve kalıcı `--hover-filters`
  modu Wayland ve X11/XWayland üzerinde geçti; 0 QML uyarısı.
  Kullanıcı verilerine/tokenine yazma veya ağ isteği yok.
- **Bilinen sorunlar:** Önceki desktop portal uyarısı sürer; eski açık uygulama
  kaynak değişikliğini almak için kapatılıp yeniden açılmalıdır. Önceki notta
  üretilemeyen menü hatası bu çalışmada yeniden üretilip giderildi.
- **Sonraki faz:** Kullanıcı denemesi.

### Ana sayfa tek medya seçimi ve filtre kontrolleri (2026-10-04)

- **Yapılanlar:** Arama yanındaki medya ComboBox kaldırıldı; soldaki Film/Dizi
  keşfet ve arama için tek kaynak olur. Medya değişiminde açık sorgu aynı metinle
  yeniden aranır, placeholder güncellenir; detaydan dönüşte arama korunur.
  `FilterComboBox` satır yüksekliği/padding/popup yüksekliği açıkça ayarlanır,
  ilk açılışta liste başına konumlanır ve yazılar kırpılıp normalize edilir.
  Puan `FilterSpinBox` içeriği salt okunur Label oldu: odak kaybında ondalıklı
  metni tekrar sayıya dönüştüren TextInput yolu kaldırıldı. Oklar/klavye
  değerleri 0–100 aralığında değiştirir; UI 0–10 puan gösterir.
- **Değiştirilen önemli dosyalar:** `DiscoverPage.qml`, `FilterComboBox.qml`,
  `FilterSpinBox.qml`, keşfet/global arama regresyon testleri, `components.md`,
  `architecture.md` ve bu devir notu.
- **Test sonucu:** Ruff temiz; **190 test geçti**. Türkçe/İngilizce locale'de
  gerçek fare oklarıyla 7.5/8.5 seçimi, klavye okları, odak kaybı, tekrarlı
  Uygula, doğru API puanı ve Temizle doğrulandı. Üç menünün ilk satırı/yüksekliği
  ve boşluksuz metni, tek medya seçimi, sorgu sırasında kategori değişimi ve
  geri dönüş de test edildi.
- **Manuel kontrol:** İzole verilerle menü ekran görüntüleri incelendi;
  Film/Dizi ile Tüm türler/Tüm ülkeler ilk satırda görünür. Gerçek Wayland ve
  X11/XWayland 1366×768/1920×1080 açılış/gezinti kontrolünde 0 QML uyarısı.
- **Bilinen sorunlar:** Eski kodun 7.5 değerini 10'a çevirdiği ve Film satırını
  gizlediği olay offscreen ortamda birebir üretilemedi; kontroller tema/odak
  bağımlılıklarını kaldıracak şekilde sağlamlaştırıldı. Kullanıcının açık eski
  uygulama süreci yeniden başlatılmalıdır. Önceki portal kaydı uyarısı sürer;
  kişisel veriler ve gerçek token bu denemelerde kullanılmadı/değiştirilmedi.
- **Sonraki faz:** Kullanıcı denemesi.

### Sade film takibi ve Devam Et açıklaması (2026-10-04)

- **Yapılanlar:** Film detayındaki üçlü durum seçici kaldırıldı; Kütüphaneye
  Ekle `PLANNED`, İzlendi `WATCHED`, İzlenmedi `PLANNED` kaydeder. Film durum
  sekmeleri gizlendi; kütüphane tüm takip durumlarını birlikte gösterir.
  Eski film kayıtları değiştirilmedi, favori ve arama-only kayıt ayrımı korundu.
  Devam Et yalnız teşhis edildi; seçim kuralları değiştirilmedi, adet sınırı
  bulunmadığına dair üç dizi regresyon testi eklendi.
- **Değiştirilen önemli dosyalar:** `MovieDetailPage.qml`, `LibraryPage.qml`,
  `movie_library.py`, `library_controller.py`, film/global arama/shell/Devam Et
  testleri ve `architecture.md`.
- **Test sonucu:** Ruff temiz; **187 test geçti**. Film ekleme → izlendi → izlenmedi, birleşik
  kütüphane/sıralama/favoriler/posterler ve Devam Et'te üç dizi test edilir.
- **Manuel kontrol:** Gerçek Wayland ve X11/XWayland 1366×768/1920×1080 gezinme testinde
  0 QML uyarısı. Kullanıcı SQLite verileri `sqlite3 -readonly` ile incelendi;
  kişisel veriye veya tokene yazma yapılmadı.
- **Bilinen sorunlar:** Devam Et yalnız yerelde yüklü normal sezonları ve
  yayınlanmış izlenmemiş bölümleri kullanır. Gerçek kayıtlarda Young Sheldon ve
  Stranger Things koşulları sağlıyor. Diğer bazı dizilerde sonraki sezonlar
  indirilmemiş: örneğin The Mentalist 151 toplam / 23 yerel bölüm; 23'ü izlenmiş.
  Hiç başlanmamış PLANNED diziler de bilerek dışarıda kalır. Tüm sezonları
  otomatik indirme bu teşhis isteği kapsamında eklenmedi. Portal kaydı uyarısı
  önceki sistem kaldırma işleminden kaynaklanır.
- **Sonraki faz:** Kullanıcı denemesi.

### Ana sayfada arama, tamamlanan dizi durumu ve Devam Et (2026-10-04)

- **Yapılanlar:** Ana Sayfa araması modal açmaz; film/dizi seçimi ve posterli
  sonuçlar keşfet grid'inde gösterilir. Detaydan Geri ile dönünce sorgu, kategori
  ve sonuçlar korunur; aynı sonuç yeniden açılabilir. Ana Sayfa'da Ctrl+K arama
  girdisine odaklanır; diğer sekmelerin global arama kısayolu korunur.
  Açık bölüm işaretleme işlemleri eski manuel `PLANNED`/`WATCHING` seçimini de
  ilerlemeye göre günceller. Tüm bölümler izlendiğinde `WATCHED`; izlenmedi
  yapılınca `WATCHING` olur. Sıfır ilerlemeli takip kaydı kütüphanede kalır.
  Metadata yenilemesi kişisel durumu değiştirmez; otomatik toplu veri onarımı
  veya migration yapılmadı. Repository manuel koruması yalnız açık dizi bölüm
  işlemleri için `override_manual=True` ile aşılır.
  Film/dizi sekme altı istatistikleri kaldırıldı. Devam Et yalnız Diziler
  sekmesinde, kaydırılabilir kütüphane içinde bulunur. Hızlı bölüm işaretlemesi
  sonrası kütüphane grid'i ve ilerleme çubuğu da yenilenir.
- **Değiştirilen önemli dosyalar:** `DiscoverPage.qml`, `Main.qml`,
  `LibraryPage.qml`, `HomePage.qml`, `tv_status.py`, `tv_detail.py`, `local.py`,
  `continue_watching_controller.py`, ilgili UI/servis testleri ve mimari/durum
  otomasyonu/bileşen belgeleri.
- **Test sonucu:** Ruff temiz; **186 test geçti**. Arama kategorileri, detaydan
  dönüş ve yeniden sonuç açma; eski üç manuel durumun tamamlanma/geri alma
  davranışı; tarihi bilinmeyen tüm bölümlerin tamamlanması; yalnız Diziler'de
  Devam Et ve kütüphanelerde istatistik bulunmaması doğrulandı.
- **Manuel kontrol:** İzole veri ve sahte TMDb ile 1366×768 inline arama,
  1920×1080 Diziler/Devam Et ekran görüntüleri incelendi. Gerçek Wayland ve
  X11/XWayland açılış/gezinti/boyut testlerinde 0 QML uyarısı.
- **Bilinen sorunlar:** Önceki desktop portal kaydı uyarısı sürer; X11 tam
  yüksekliği çalışma alanı nedeniyle 1052 px uygular. Canlı TMDb ile kullanıcı
  denemesi yapılmadı; kullanıcı veritabanına test yazımı yapılmadı.
- **Sonraki faz:** Kullanıcı denemesi. Yeni faz uygulanmadı.

### Dizi takibi ve masaüstü istatistik düzeni (2026-10-04)

- **Yapılanlar:** Dizi ekleme artık doğrudan `WATCHING` kaydeder; detay durum
  seçicisi kaldırıldı. Dizi kütüphanesi durum sekmelerini gizler ve tüm takip
  durumlarındaki dizileri birlikte gösterir; film sekmeleri değişmedi.
  Sezon/dizi izlendi ve izlenmedi düğmeleri tek satır, iki etiketli grup içinde
  düzenlendi. Sezon işlemleri onaysız uygulanır; tüm dizi işlemleri onaylı kalır.
  İstatistiklerin 900 px sınırı ve Son 12 ay grafiği kaldırıldı. Yerel geçmiş,
  favoriler ve mevcut durum kayıtları korunur.
- **Değiştirilen önemli dosyalar:** `TvDetailPage.qml`, `LibraryPage.qml`,
  `HomePage.qml`, `StatisticsPanel.qml`, `library_controller.py`, `tv_library.py`
  ve ilgili detay/kütüphane/istatistik testleri.
- **Test sonucu:** Ruff temiz; tam kalite kontrolünde **183 test geçti**.
  İlk çalıştırmada eski grid seçimi beklentisi başarısız oldu ve ardından Qt
  test süreci çöktü; poster güncellemeleri sonrası seçimi yapan test düzeltildi,
  tam yeniden çalıştırma başarılıdır.
- **Manuel kontrol:** İzole verilerle detay ve istatistik ekran görüntüleri
  incelendi. Gerçek Wayland 1366×768 ve 1920×1080 testi geçti; 0 QML uyarısı.
- **Bilinen sorunlar:** Sistem masaüstü kaydı kaldırılmış olduğu için portal
  kaydı tek Qt uyarısı verir; arayüz açılışı ve gezinme başarılıdır. Canlı TMDb
  verileriyle kullanıcı denemesi henüz yapılmadı.
- **Sonraki faz:** Yeni faz açılmadı. Kullanıcı mevcut uygulamayı kapatıp kaynak
  sürümü yeniden açarak dizi ekleme ve sezon düğmelerini deneyebilir.

### Görsel referanslar ve Keşfet ana sayfası (2026-10-04)

- **Yapılanlar:** Kullanıcının `Resimler/dizi_tik.png`, `progress.png` ve
  `istatistik.png` referanslarına göre yazısız yuvarlak bölüm tikleri, dizi
  detay/kütüphane bölüm sayacı ve sarı ilerleme barı uygulandı. Ana Sayfa artık
  Keşfet ve global aramadır. İstatistikler ayrı menüde bir başlık altında süre,
  sayaçlar, aylık bölüm grafiği, tür halkası ve posterli ilk beş diziyi içerir.
  Devam Et/favoriler/hızlı girişler burada korunur. Filtre delegate metin ve
  hover referansları açık id'lere bağlandı; popup odağı/Escape davranışı düzeltildi.
- **Değiştirilen önemli dosyalar:** `Main.qml`, `DiscoverPage.qml`, `HomePage.qml`,
  `TvDetailPage.qml`, `FilterComboBox.qml`, yeni `EpisodeCheck`,
  `EpisodeProgressBar`, `StatisticsPanel`, istatistik service/controller/repository,
  TV library/detail sunum verileri ve ilgili testler.
- **Test sonucu:** Ruff temiz, **183 test geçti**. Testler menü sırası/ilk sayfa,
  arama modalı, filtrelerde fare hover/klavye/Escape, yazısız tikle kalıcı izleme
  ve 1/3 ilerleme, aylık tarih sınırları, eksik süre ve gerçek yerel veriyi kapsar.
- **Manuel kontrol:** İzole SQLite ve sahte TMDb ile istatistik/dizi ekran
  görüntüleri incelendi. Offscreen, Wayland ve X11/XWayland gezinme/boyut
  kontrollerinde 0 QML uyarısı. Wayland/X11'de mevcut kaldırılmış desktop kaydı
  nedeniyle bir portal uyarısı var; X11 1920×1080 isteğini ekran çalışma alanı
  nedeniyle 1920×1052 olarak uyguladı. Kullanıcı veritabanına test yazımı yok.
- **Bilinen sorunlar:** Film izleme tarihi tutulmadığı için aylık grafik yalnız
  bölümlere aittir; metadata süresi yoksa uydurulmaz. Üst dizi sıralaması bilinen
  bölüm sürelerine göredir; eksik süreli değerler “en az” diye işaretlenir.
  Dağıtım paketleri bu değişikliklerden yeniden üretilmedi; eski açık süreç
  yeniden başlatılmalıdır. Önceki paket yayın sınırları değişmedi.
- **Sonraki faz:** Kullanıcı görsel geri bildirimi.

### Kütüphane posterleri (2026-10-04)

- **Yapılanlar:** Film/dizi ortak kütüphane kartları model veya görünürlük
  değişiminde eksik posterlerini yeniden ister. Servis hazırlığı worker'a alındı;
  indirme sürerken yanlış "Poster yok" mesajı yerine skeleton gösterilir.
  Geçici ağ/CDN hataları tek, sınırlı tekrar denemeyle ele alınır.
- **Değiştirilen önemli dosyalar:** `image_service.py`, `library_controller.py`,
  `LibraryPosterGrid.qml`, `PosterCard.qml`, görsel/kütüphane testleri.
- **Test sonucu:** Gerçek JPEG'in `.img` cache dosyasından QML'de görüntülenmesi,
  yenileme/sıralama sonrası posterler ve bağlantı/408/429/503 tekrarları doğrulandı.
  Ruff temiz, **182 test geçti**. Galeri 1366×768 ve 1920×1080 boyutlarında
  offscreen platformda QML/Qt uyarısı olmadan açıldı.
- **Manuel kontrol:** Kayıtlı üç dizinin posterleri mevcut ve Qt tarafından
  okunabilir. Canlı TMDb aramasında dört poster başarıyla indirildi ve okunabildi;
  token çıktıya yazılmadı, kişisel takip verileri değiştirilmedi.
- **Bilinen sorunlar:** TMDb'de gerçekten posteri olmayan kayıtlar veya kalıcı
  bağlantı kesintisi için gerçek poster garanti edilemez; kayıtlar gizlenmez.
  Açık eski süreç yeni kodu almak için yeniden başlatılmalıdır.
- **Sonraki faz:** Kullanıcı geri bildirimi.

### Ana sayfa arama düzeltmesi ve tür seçimi (2026-10-04)

- **Yapılanlar:** Ana sayfanın salt okunur arama alanındaki odak olayı modal
  kapanışında aramayı yeniden açıyordu. Tıklama ve Enter/Space ile açık etkinleştirme
  kullanıldı. Film ve Dizi / Film / Dizi seçimi eklendi; seçilmeyen endpoint çağrılmaz.
- **Değiştirilen önemli dosyalar:** `HomePage.qml`, `GlobalSearch.qml`,
  `search_controller.py`, global arama/dashboard regresyon testleri ve bileşen belgesi.
- **Test sonucu:** Önceki kodda ana sayfa→arama→dizi→menü testi başarısızdı;
  düzeltmeyle film/dizi için menü tıklaması ve modal kapanışı, kategori değişiminde
  geç sonuçların yok sayılması doğrulandı. Tam kalite kontrolünde Ruff temiz,
  **176 test geçti**. Offscreen 1366×768 ve 1920×1080 açılış/gezinti kontrolü geçti.
- **Manuel kontrol:** Kullanıcının gerçek TMDb aramasını yeni süreçte tekrar
  denemesi gerekir; otomatik kontroller sahte yanıtlarla kişisel veriden izoledir.
- **Bilinen sorunlar:** Önceden açık süreç QML değişikliklerini yeniden başlatmadan
  almaz. Paket dağıtımına ilişkin önceki doğrulama sınırları değişmedi.
- **Sonraki faz:** Kullanıcı geri bildirimi.

- Faz 0: Python `src/izlek` paketi, `pyproject.toml`, XDG yolları, logging, pytest ve Ruff.
- Faz 1: Qt Quick ana pencere, altı sayfalı sidebar, koyu tema, pencere durumu.
- Faz 2: Yeniden kullanılabilir QML bileşenleri ve çevrimdışı galeri.
- Faz 3: Yedi SQLAlchemy tablosu, repository katmanı, Alembic migration; SQLite dosyası XDG data dizininde.
- Faz 4: İlk açılış TMDb token ekranı, `GET /3/authentication` ile Bearer doğrulaması, arka plan worker'ı, anahtarlık öncelikli saklama, `0600` izinli düz metin fallback ve Ayarlar'da token değiştirme.
- Faz 5: Merkezi httpx TMDb istemcisi; configuration, film/dizi araması, film/dizi ve sezon detayı; Pydantic yanıt modelleri, domain hataları, timeout ve sınırlı 429 tekrar denemesi.
- Faz 6: TMDb configuration'a göre poster grid/detail ve backdrop boyutları, işçi havuzunda görsel indirme, XDG disk cache, atomik kayıt, placeholder ve cache boyutu API'si.
- Faz 7: Ctrl+K global arama overlay'i, debounce, eşzamanlı film/dizi sorgusu, eski sonuç koruması, orijinal başlıklarla sonuç kartları ve medya detay sayfası.
- Faz 8: Film hero/detail sayfası, TMDb credits/videos/similar/recommendations/watch providers, yerel metadata cache'i, takip durumu/favori/liste aksiyonları ve sistem tarayıcısında fragman.
- Faz 9: Film tasarımına uyumlu dizi detayı, sezon/bölüm listesi, yerel bölüm ilerlemesi, onaylı sezon/dizi toplu işlemleri ve offline metadata erişimi.
- Faz 10: Dizi bölüm ilerlemesinden otomatik `WATCHING`/`WATCHED` kararı, manuel status koruması, eski status verisini koruyan migration ve yeni yayınlanmış izlenmemiş bölüm göstergesi.
- Faz 14: SQLite tabanlı ortak film/dizi favorileri, kütüphane kartlarında kalp aksiyonu, ana sayfada altı favorilik özet ve tümünü gösterme.
- Faz 15: Yerel özel liste yönetimi, çoklu medya üyeliği, kalıcı sıralama, Listeler sayfası ve film/dizi detayından ekleme.
- Faz 16: Arama, hızlı giriş, Devam Et, favoriler ve yerel istatistiklerden oluşan responsive ana sayfa dashboard'u; veri yoksa başlangıç görünümü.
- Faz 17: TMDb Discover Movie/TV ile puan odaklı Keşfet, yıl/tür/ülke/puan filtreleri, 100 oy eşiği ve kontrollü sayfalama.
- Faz 18: TR watch-provider görünümü, abonelik/kiralama/satın alma grupları, JustWatch attribution'ı, güvenli TMDb sağlayıcı bağlantısı ve cache'lenen provider metadata'sı.
- Faz 19: SQLite tabanlı izleme istatistikleri, eksik runtime yönetimi, en çok izlenen türler, dashboard StatCard'ları ve ayrıntı dialogu.
- Faz 20: Film, dizi ve sezonlar için 24 saatlik metadata freshness; local-first detay akışı, arka plan refresh ve offline/timeout/404 koruması.
- Faz 21: Sürümlü ve taşınabilir tam durum İzlek JSON'u; atomik export, doğrulama/preview/import raporu, kimlik tabanlı duplicate merge ve Ayarlar arayüzü.
- Faz 22: TMDb bağlantı durumu/token değiştirme ve test, taşınabilir veri import/export, iş parçacığı dışında cache boyutu/temizleme, global klavye kısayolları ve İzlek/GitHub/lisans/TMDb/JustWatch hakkında bölümleri.
- Faz 23: Klavye kısayolları ve Esc akışının otomatik testi, görünür odak göstergeleri/tooltips, modal dialog odak davranışı, sabit poster çerçevesinde skeleton yükleme, sade kullanıcı hataları ve minimum pencere/HiDPI smoke kontrolleri.
- Faz 24: 500 film/200 dizi/10.000 bölümlük sentetik performans senaryosu ve SQL bütçeleri; TV ilerlemesi, detay ve liste akışlarında N+1 düzeltmeleri; görünür-delege thumbnail lazy-load, bölüm ListView sanallaştırması, decode boyutu sınırı, sayfa görev iptali ve sahiplik denetimi.
- Faz 25: Kritik TMDb, repository, takip/bölüm ilerlemesi, Devam Et, istatistik, import/export, freshness, token store, liste ve favori sınır testleri; suite genelinde gerçek TCP engeli; token gerektirmeyen GitHub Actions ve tek `python scripts/quality.py` kalite komutu.
- Faz 26: PyInstaller one-folder → AppDir → AppImage build sırası; paketli QML/resources/Alembic migration'ları; İzlek desktop/icon/category metadata'sı; XDG dışına yazmayı engelleyen package smoke modu; glibc 2.28/PySide6 constraint'i ve Ubuntu 22.04/24.04 artifact smoke işlerini içeren GitHub workflow'u.
- Faz 27: Arch standardında `izlek` PKGBUILD; runtime/build/test bağımlılık ayrımı; desktop dosyası, hicolor SVG simgesi ve GPL lisansı kurulumu; kullanıcı XDG verilerini koruyan kaldırma davranışı; Arch kurulum ve ilk release tag'ine geçiş notları.
- Faz 28: PyInstaller one-folder tabanlı Debian/Ubuntu `.deb` build betiği; FHS `/usr/lib/izlek`, `/usr/bin`, desktop, hicolor simge ve copyright yerleşimi; Ubuntu 22.04/24.04 temiz kurulum/smoke/kaldırma CI akışı; kullanıcı XDG verilerini koruyan kaldırma davranışı.
- Faz 29: Açık kaynak repository belgeleri gözden geçirildi; README'de ürün, kurulum, paketleme, mimari, roadmap, gizlilik ve TMDb/JustWatch attribution bölümleri tamamlandı; CONTRIBUTING, CODE_OF_CONDUCT, SECURITY ve CHANGELOG güncellendi; Bug/Feature issue ve PR şablonları güçlendirildi.
- Faz 30: Push/PR Python 3.11 CI kalite kapısı; AppImage ve Debian paket workflow'larını reusable hale getiren `v*` tag release akışı; AppImage, `.deb`, checksum ve Arch package definition asset'leri; token gerektirmeyen mock test ve release dokümantasyonu.
- Faz 31: TMDB/JustWatch release öncesi uyumluluk denetimi; Hakkında ve detay ekranlarında TMDB kaynak ayrımı ve resmî bildirim; provider bölümlerinde doğrudan JustWatch attribution; 180 günlük görsel cache retention; resmî logo ve SQLite metadata retention release engellerinin belgelenmesi.
- Faz 32: 1.0 release adayı için 25 senaryolu QA matrisi; güncel kaynaktan temiz wheel build/install ve iki açılış smoke'u; SQLite bütünlük kontrolü; cache temizleme regresyonu. Uygulama senaryolarında crash/veri kaybı bulunmadı ancak TMDB uyumluluğu ve gerçek AppImage/`.deb`/AUR build doğrulamaları açık olduğundan karar NO-GO.
- Faz 33: Proje, fallback ve paket sürümleri `1.0.0` yapıldı; changelog ile v1.0.0 release notes hazırlandı; README ekran görüntüsü güncel dashboard başlangıç görünümüyle yenilendi. Tag workflow'u sürüm eşleşmesi, sabit adlı AppImage/`.deb`, tag source archive, checksum ve dosyadan release notes kullanacak şekilde güncellendi. Çalışma kopyasında Git repository/remote bulunmadığı, GitHub kimliği geçersiz olduğu ve Faz 31 engelleri sürdüğü için tag push ve GitHub Release yapılmadı.

Global arama, Keşfet, film ve dizi detay sayfaları TMDb ve görsel servisine bağlıdır; metadata ve kişisel aksiyonlar SQLite'ta ayrı ve kalıcıdır.

## Doğrulamalar

- Son otomatik kontrol: `.venv/bin/python scripts/quality.py` → **Ruff geçti, 147 pytest testi geçti**.
- Faz 5 istemci testleri `httpx.MockTransport` kullanır; gerçek TMDb API'sine istek göndermez.
- Faz 6 görsel testleri cache tekrar kullanımını, çevrimdışı poster erişimini, bozuk indirme fallback'ini ve eşzamanlı isteklerin tek indirmeye düşmesini doğrular.
- Faz 7 testleri Ctrl+K/Esc gezinmesini, debounce'u, film/dizi ayrımını, orijinal başlıkları, eski yanıt korumasını ve sonuçtan detay açmayı sahte TMDb ile doğrular.
- Faz 8 testleri altı TMDb film endpoint'ini mock HTTP ile, durum/favori/liste kalıcılığını SQLite yeniden açılışıyla, QML aksiyonlarını klavyeyle ve fragman URL'sini sahte tarayıcı çağrısıyla doğrular.
- Faz 9 testleri TMDb dizi endpoint'lerini mock HTTP ile, tekil/sezon/dizi ilerlemesini, metadata yenilemesi ve yeniden açılışta korunmasını, eksik sezonla toplu işlem korumasını ve QML onay akışını doğrular. Dizi sayfası offscreen 1366×768 ve 1920×1080 boyutlarında açılır; QML uyarısı oluşmaz.
- Faz 10 testleri otomatik durum kurallarını, manuel seçimlerin korunmasını, yeni bölümde `WATCHED` durumunun değişmemesini, UI modelindeki izlenmemiş bölüm göstergesini ve eski SQLite veritabanı yükseltmesini doğrular.
- Faz 15 testleri liste CRUD, çoklu üyelik, sıralama ve yeniden açılış kalıcılığını; Listeler sayfasını ve dizi detayındaki ekleme aksiyonunu doğrular.
- Faz 16 testleri boş dashboard, global arama çağrısı, hızlı girişler, Devam Et ve 1366×768/1920×1080 yerleşimini doğrular.
- Faz 17 testleri Discover Movie parametrelerini, 100 oy eşiğini, controller filtrelerini, kontrollü sayfalamayı ve 1366×768/1920×1080 QML düzenini doğrular.
- Faz 18 testleri provider gruplarını, güvenli TMDb linkini, boş sağlayıcı state'ini ve TV provider link cache sunumunu doğrular.
- Faz 19 testleri local istatistik hesaplarını, eksik runtime nedeniyle süre toplamının gizlenmesini ve dashboard ayrıntı dialogunu doğrular.
- Faz 20 testleri fresh ve stale metadata'yı, local-first arka plan yenilemesini, offline/timeout/404 fallback'ini, sezon freshness'ını ve ağ geri geldiğinde aynı oturumda aramayı doğrular.
- Faz 21 testleri export edilen JSON'da token/cache yolu olmadığını, temiz veritabanına import sonrası kullanıcı durumunun eşdeğerliğini, tekrar importta medya/liste üyeliklerinin çoğalmadığını, izlenmiş bölümün korunmasını ve geçersiz/yeni şemaların yazmadan reddedilmesini doğrular.
- Faz 21 offscreen smoke kontrolünde Ayarlar ve import/export kartı 1366×768 ile 1920×1080 boyutlarında açıldı; 0 QML ve 0 Qt uyarısı oluştu. Wheel ağsız `--no-build-isolation` ile oluşturuldu.
- Faz 22 doğrulaması: `.venv/bin/python -m pytest -q` → **99 geçti**; `.venv/bin/ruff check .` → **geçti**. Settings QML'i offscreen shell gezinmesinde uyarısız açıldı; cache işlemleri `ImageDiskCache` üzerinden UI thread'i dışında yürütülüyor.
- Faz 23 doğrulaması: `.venv/bin/python -m pytest -q` → **101 geçti**; `.venv/bin/ruff check .` → **geçti**. Offscreen klavye testi Ctrl+1–5, Ctrl+, Ctrl+K ve Esc'i; minimum 800×600 penceresini; ayrı bir `QT_SCALE_FACTOR=2` sürecinde QML/HiDPI açılışını doğrular.
- Faz 24 doğrulaması: `.venv/bin/python -m pytest -q` → **104 geçti**; `.venv/bin/ruff check .` → **geçti**. Büyük veri profilinde film/dizi kütüphanesi 1/2, Devam Et 1, film/dizi detay 4/5, sezon 3 ve özel listeler 3 sabit SQL sorgusunda kaldı. Film ve dizi ilk detay yükleri altışar TMDb isteğiyle sınırlandı; iptal sonrası geç sonuç UI'ya yazılmadı. Ayrıntılı süreler [Faz 24 performans profilinde](PHASE_24_PERFORMANCE.md).
- Faz 25 doğrulaması: `.venv/bin/python scripts/quality.py` → **Ruff geçti, 136 pytest testi geçti, uyarı yok**. Bütün TMDb endpoint testleri `httpx.MockTransport` kullanır; suite gerçek TCP bağlantısını reddeder ve CI workflow'u TMDb tokenı tanımlamaz. QML smoke testleri offscreen çalışır, screenshot eşleştirmesi kullanılmaz. Kapsam ayrıntıları [Faz 25 kalite notunda](PHASE_25_QUALITY.md).
- Faz 26 doğrulaması: `.venv/bin/python scripts/quality.py` → **Ruff geçti, 140 pytest testi geçti, uyarı yok**. Package smoke testi kaynak ortamında XDG data/config yazımlarını ve AppImage/AppDir konumuna yazılmadığını doğruladı. PyInstaller ve appimagetool bu sandbox'ta indirilemediği için gerçek one-folder/AppImage binary üretimi yerelde çalıştırılamadı; workflow aynı kontrolleri glibc 2.28 build container'ında zorunlu çalıştıracak ve yalnız başarı halinde artifact yükleyecek. Ayrıntılar [Faz 26 AppImage notunda](PHASE_26_APPIMAGE.md).
- Faz 27 doğrulaması: `makepkg --printsrcinfo` çıktısı `.SRCINFO` ile eşleşti, `namcap PKGBUILD` hatasız tamamlandı ve `desktop-file-validate src/izlek/resources/desktop/izlek.desktop` geçti. `.venv/bin/python scripts/quality.py` → **Ruff geçti, 140 pytest testi geçti, uyarı yok**. Yayımlanmış upstream URL/tag olmadığı için kaynak indirimi veya gerçek `makepkg` build'i çalıştırılamadı.
- Faz 28 doğrulaması: `python -m compileall scripts/build_deb.py`, Ruff ve `tests/test_packaging.py` (**5 geçti**) başarılı; `build_deb.py --help` ve `desktop-file-validate` geçti. Bu ortamda `dpkg-deb` bulunmadığından yerel `.deb` üretimi/kaldırma smoke'u çalıştırılamadı; `deb.yml` bunu Ubuntu 22.04 build ve 22.04/24.04 temiz host matrix'inde yapar.
- Faz 29 doğrulaması: README başlıkları ve gizlilik açıklamaları gözden geçirildi; issue/PR şablonları mevcut; `.venv/bin/python scripts/quality.py` → **Ruff geçti, 141 pytest testi geçti**.
- Faz 30 doğrulaması: Workflow YAML'leri ve reusable/release job bağımlılıkları gözden geçirildi; `.venv/bin/python scripts/quality.py` → **Ruff geçti, 141 pytest testi geçti**. Bu ortamda GitHub Actions runner çalıştırılamadığından gerçek tag/release denemesi GitHub üzerinde yapılacaktır.
- Faz 31 doğrulaması: TMDB resmî FAQ, API Terms, image ve watch-provider belgeleriyle denetim yapıldı. Hedefli Ruff geçti; image service, attribution ve UI smoke testleri (**11 geçti**) başarılı. Resmî TMDB logo dosyası bu ortamda DNS nedeniyle indirilemediği için logo doğrulaması yapılamadı.
- Faz 32 doğrulaması: İlk tam kalite kapısı Ruff ve **144 test** ile geçti; cache temizleme regresyonu eklendi ve hedefli **7 test** geçti. Güncel wheel temiz venv'e kuruldu, boş izole XDG dizininde iki kez açıldı; migration `0003_season_freshness`, SQLite integrity `ok`. AppImage build PyInstaller, `.deb` build `dpkg-deb`, AUR build ise release tarball/upstream bilgisi olmadığı için tamamlanamadı. Ayrıntılı sonuç ve 25 senaryonun tamamı [Faz 32 QA raporunda](PHASE_32_RELEASE_CANDIDATE_QA.md).
- Faz 33 doğrulaması: `izlek-1.0.0` wheel ve sdist ağsız üretildi. Wheel temiz venv'e kurularak izole XDG dizininde iki kez açıldı; paket sürümü `1.0.0`, migration `0003_season_freshness`, SQLite integrity `ok`. Packaging testleri **7 geçti**; workflow YAML ve tüm shell blokları parse edildi; `.SRCINFO` ile `makepkg --printsrcinfo` eşleşti, `namcap` ve desktop-file-validate temizdi. Gerçek AppImage/`.deb`, tag source archive ve GitHub Release yalnız tag workflow'unda üretilecektir.
- Faz 8 offscreen smoke testinde 1366×768 ve 1920×1080 açılışları geçti; 0 QML ve 0 Qt uyarısı. Film detay görünümü offscreen ekran görüntüsünde incelendi. Sandbox gerçek Wayland/X11 soketlerine erişemediği için bu oturumda canlı display testi yapılamadı.
- Faz 7 offscreen smoke testinde 1366×768 ve 1920×1080 açılışları geçti; 0 QML ve 0 Qt uyarısı. Bu sandbox Wayland soketine erişemediği ve X11 `:0` ekranına bağlanamadığı için gerçek display smoke testleri burada başlatılamadı.
- Ekran dışı onboarding ve ana pencere smoke testleri 1366×768 ile 1920×1080 boyutlarında geçti; **0 QML/Qt uyarısı**. Wheel paketlemesi geçti.
- Kullanıcı, Wayland ve X11/XWayland smoke testlerinde aynı iki pencere boyutunu doğruladı; masaüstü kaydı kurulduktan sonra her iki platformda **0 QML/Qt uyarısı** bildirdi.
- Kullanıcı `izlek.sqlite3` dosyasının oluştuğunu doğruladı.
- Kullanıcı gerçek TMDb tokenının kabul edildiğini ve uygulama yeniden açılınca onboarding yerine ana pencerenin geldiğini doğruladı. **Token değeri bu nota veya repository'ye kaydedilmedi.**

## Açık doğrulama sınırları

- Otomatik testler TMDb yanıtlarını ve keyring'i taklit eder. Kullanıcının canlı denemesi doğrulama ve yeniden açılışı kapsar; anahtarlığın mı yoksa yerel dosya fallback'inin mi kullanıldığı ayrıca bildirilmedi.
- Bu çalışma ortamında PyPI DNS erişimi olmadığı için `keyring` paketi kurulamadı. Yeni oturumda bağımlılıkları `./.venv/bin/python -m pip install -e '.[dev]'` ile kurup gerçek keyring backend'ini kontrol edin. Fallback çalışır ve UI bunu açıklar.
- Sandbox gerçek Wayland/X11 soketlerine erişmez. Gerekli masaüstü denemelerini kullanıcı kendi terminalinde yapmıştır.
- Bu oturumda PyPI DNS erişimi olmadığı, PyInstaller önceden kurulu olmadığı ve Docker soketine erişilemediği için Faz 26 binary'si yerelde üretilemedi. `.github/workflows/appimage.yml` GitHub üzerinde çalıştırılınca one-folder, AppDir ve iki temiz Ubuntu smoke adımını tamamlayıp artifact üretecektir.
- Faz 27 sırasında upstream URL/tag yoktu. Faz 33 sonrasında hedef repository `https://github.com/Teknoloji-Filozoflari/Izlek` olarak doğrulandı; AUR yayını öncesinde tag arşivinin gerçek SHA-256 değeri hâlâ yazılmalıdır.
- Faz 28 sırasında upstream/maintainer bilgisi yoktu. Faz 33 workflow'u Debian Homepage ve Maintainer alanlarını GitHub repository bağlamından üretir.
- Faz 29 sonrasında upstream `Teknoloji-Filozoflari/Izlek` olarak doğrulandı; özel security contact kanalı ayrıca etkinleştirilmemiştir.
- Faz 31 release engelleri: TMDB'nin onaylı, değiştirilmemiş logo SVG'si Hakkında ekranına eklenmemiştir. Ayrıca SQLite'taki TMDB metadata, sezon ve provider cache'i için en geç 180 günde yalnız uzak metadata'yı temizleyip kişisel tracking verisini koruyan retention işi henüz yoktur. Bu iki madde çözülmeden TMDB uyumluluğu release onayı verilmemelidir.
- Faz 32 release engelleri: AppImage ve `.deb` gerçek artefaktları bu revizyondan üretilip temiz sistemde doğrulanmadı; AUR gerçek tag tarball'ı ile build edilmedi. Bunlar ve Faz 31 engelleri kapanmadan 1.0 release yapılmamalıdır.
- Faz 33 yayın engelleri: Bu workspace'teki `.git` dizini boş olduğundan commit/tag/remote bilgisi yoktur; kayıtlı `gh` hesabının tokenı geçersizdir. PyInstaller, appimagetool ve `dpkg-deb` de yerelde yoktur, Docker socket erişimi reddedilir. Dolayısıyla `v1.0.0` tag workflow'u tetiklenmedi ve istenen GitHub Release binary artefaktları oluşturulmadı. Arch upstream URL'si doğrulandı; checksum tag arşivi yayımlanana kadar `SKIP` kalmıştır.

## 2026-10-04 — Listelere medya eklerken yerel arama

- **Yapılanlar:** Listeler medya ekleme alanına başlık arama girdisi, Ara ve
  Temizle düğmeleri eklendi. Enter aramayı uygular; büyük/küçük harf ve kenar
  boşlukları göz ardı edilir. Mevcut yerel adaylar controller'da filtrelenir;
  ağ/veritabanı isteği yapılmaz. Ekleme sonrası filtre korunur ve zaten
  listedeki içerikler mevcut servis davranışıyla adaylardan çıkarılır.
- **Değiştirilen önemli dosyalar:** `ListsPage.qml`,
  `custom_lists_controller.py`, `tests/test_custom_lists.py`.
- **Test sonucu:** `.venv/bin/python -m pytest -q`: 196 geçti;
  `.venv/bin/ruff check .`: başarılı. QML testi Ara, Enter, sonuçsuz aramada
  ekleme düğmesinin kapanması, filtrelenen filmin doğru eklenmesi ve Temizle
  akışını doğrular; mevcut iki pencere boyutu ve QML uyarı kontrolü korunur.
- **Manuel kontrol:** Gerçek masaüstü oturumunda manuel kontrol yapılmadı;
  Qt offscreen etkileşim testi başarılı.
- **Bilinen sorunlar:** Bu değişiklikte saptanmadı.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Kütüphane görsellerini indir ve tut

- **Yapılanlar:** Takip edilen film/dizilerin mevcut afiş ve backdrop yolları
  arka planda indirilir. Açılış, saatlik bakım, hızlı ekleme, detay değişikliği
  ve import sonrası eksikler tamamlanır. `.keep` dosyaları kütüphane görsellerini
  otomatik ve genel cache temizliğinden korur; kullanıcı isteği retention
  kuralına açık istisnadır.
- **Değiştirilen önemli dosyalar:** `services/library_images.py`,
  `cache/images.py`, `ui/controllers/cache_controller.py`, `app.py`,
  `SettingsPage.qml`, `tests/test_library_images.py`.
- **Test sonucu:** 197 test geçti, Ruff başarılı. Yeni test tüm takip edilen
  afiş/backdrop dosyalarını, takip dışı medyanın hariç tutulmasını, 200 gün
  sonra korunmayı, cache temizliğini ve tekrar indirmeden kullanımı doğrular.
- **Manuel kontrol:** Gerçek kullanıcı kütüphanesi senkronize edildi;
  ağ erişimiyle tekrar deneme sonrası 36 görsel saklandı, indirilemeyen 0.
  Gerçek masaüstü arayüzünde manuel kontrol yapılmadı.
- **Bilinen sorunlar:** Metadata içinde görsel yolu olmayan içerik için görsel
  uydurulmaz; ağ kesilince eksikler sonraki senkronizasyonda denenir.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Detay ekranından kütüphaneden kaldırma

- **Yapılanlar:** Film ve dizi detaylarına, takip durumlu içerikte görünen
  Kütüphaneden Kaldır düğmesi eklendi. Mevcut servis/repository akışıyla
  status `None` yapılır; favoriler, özel listeler, bölüm ilerlemesi, metadata
  ve görsel dosyaları korunur. İşlem sonrası Kütüphaneye Ekle yeniden görünür.
  Başarılı detay yazımları `libraryChanged` ile kütüphaneleri, istatistikleri
  ve hızlı ekleme üyelik bilgisini yeniler; kaldırılan içerik tekrar eklenebilir.
- **Değiştirilen önemli dosyalar:** Film/dizi detay QML sayfaları, ilgili
  controller ve servisler, `app.py`, film/dizi detay testleri.
- **Test sonucu:** 197 test geçti; Ruff başarılı. Film kaldırma ve
  tekrar ekleme, favori/liste korunması; dizi butonunun Space ile çalışması,
  bölüm ilerlemesinin korunması ve Ekle/Kaldır görünürlüğü test edildi.
- **Manuel kontrol:** Gerçek masaüstünde yapılmadı; Qt offscreen testi kullanıldı.
- **Bilinen sorunlar:** Bu değişiklikte saptanmadı. Özel listeler ve favoriler
  bağımsız olduklarından kaldırılan içerik bu alanlarda görünmeye devam eder.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Dizi detayında oyuncu fotoğrafları ve kompakt alt bilgiler

- **Yapılanlar:** Bölümlerden sonraki oyuncu listesi fotoğraflı, ad/rol içeren
  ve satır kaydıran kartlara dönüştürüldü. Fotoğraf yolu servis snapshot'ında
  korunur; controller mevcut ImageService üzerinden profile görselini ister.
  TMDb profile boyutları kullanılır; dosyalar mevcut disk cache'ine indirilir
  ve yeniden açılışta çevrimdışı okunur. Eksik fotoğrafta yer tutucu gösterilir.
  Sezon ve kişisel durum güncellemeleri oyuncu fotoğraflarını korur.
  Yaratıcılar/şirketler/ülkeler eşit üç sütunda, sağlayıcı/fragman iki sütunda,
  benzer/öneriler iki afiş şeridinde gösterilir. Dar pencerede tek sütuna geçer.
- **Değiştirilen önemli dosyalar:** `TvDetailPage.qml`, `tv_detail.py`,
  `tv_detail_controller.py`, `image_service.py`, `tmdb/models.py`, ilgili testler.
- **Test sonucu:** 198 test geçti; Ruff başarılı. Profile indirme boyutu,
  disk cache yeniden kullanımı, QML fotoğraf kaynağı, 1366×768 ve 1920×1080
  sütunları, dar pencere tek sütun geçişi ve Qt/QML uyarıları doğrulandı.
- **Manuel kontrol:** Örnek verilerle offscreen 1366×768 ekran görüntüsü
  `/tmp/izlek-tv-layout.png` üretilip incelendi; canlı masaüstü testi yapılmadı.
- **Bilinen sorunlar:** TMDb'de fotoğrafı olmayan oyuncuda fotoğraf gösterilemez.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Devam Et üyelik ve hızlı işlem denetimi

- **Yapılanlar:** Devam Et yalnız takip durumu dolu kütüphane dizilerini seçer;
  favori, liste veya eski bölüm ilerlemesi tek başına üyelik sayılmaz.
  Repository'nin `tracked_only` filtresi isteğe bağlıdır; TV kütüphanesinin
  favoriler/progress sorgusu korunur. Kaldırma bölüm ilerlemesini silmez;
  yeniden ekleme eski ilerlemeye göre sonraki bölümü bulur.
  Hızlı İzlendi yazımında BEGIN IMMEDIATE transaction içinde üyelik ve
  yayınlanmış normal bölüm kontrol edilir; eski kart kaldırılan diziyi
  tekrar takibe alamaz. Çift tıklama ve model dışı bölüm istekleri engellenir.
  Liste yenileme/gezinme başlatılmış yazımı iptal etmez; başarılı yazımın
  bildirimi generation değişse de gönderilir. İstatistik/favori/hızlı ekleme
  bilgileri yenilenir. Okuma hatasında eski kartlar temizlenir ve yeniden
  deneme düğmesi gösterilir. Özel, tarihsiz, gelecekteki bölümler ve bütün
  yayınlanmış bölümleri izlenmiş diziler hariçtir; adet sınırı yoktur.
- **Değiştirilen önemli dosyalar:** `repositories/local.py`,
  `services/continue_watching.py`, `services/tv_detail.py`,
  `ui/controllers/continue_watching_controller.py`, `LibraryPage.qml`,
  `app.py`, `tests/test_continue_watching.py`.
- **Test sonucu:** 211 test geçti; Ruff başarılı. Üyelik/durum/ilerleme
  kombinasyonları, favoriyle kaldırılan içerik, tekrar ekleme, eski karttan
  yazım engeli, yayınlanmamış/özel/tarihsiz bölüm yazım engeli ve eşzamanlı
  yenileme/çift tıklama regresyonları eklendi.
- **Manuel kontrol:** Gerçek SQLite kütüphanesi salt okunur kontrol edildi;
  eski ilerlemesi olan 1 kütüphane dışı dizi filtreleniyor, 1 uygun dizi kalıyor.
  Qt offscreen arayüz testi yapıldı; canlı masaüstü kontrolü yapılmadı.
- **Bilinen sorunlar:** Sonraki sezonun bölüm metadata'sı yerelde yoksa bölüm
  uydurulmaz; mevcut sezon yükleme akışıyla gelmesi gerekir.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Dizi önerileri ve film detay alt düzeni

- **Yapılanlar:** Dizi detayından Benzer Diziler kaldırıldı; yalnız Önerilen
  Diziler afiş şeridi kaldı. Gizli benzer dizi afişleri artık istenmiyor.
  Film detayına fotoğraflı oyuncu kartları, eşit üç sütunda yönetmen/şirket/ülke,
  iki sütunda sağlayıcı/fragman ve kompakt benzer/önerilen film afişleri eklendi.
  Dar pencerede alt bilgi sütunları teke iner. Mevcut dizi oyuncu kartları
  `CastGrid.qml` bileşenine taşınıp iki detay sayfasında kullanıldı.
  Film oyuncularının profilePath değerleri servis snapshot'ına dahil edildi;
  fotoğraflar mevcut profile indirme/cache akışıyla yüklenir ve durum
  değişikliklerinde korunur. Üst detay ve izleme işlemleri korunmuştur.
- **Değiştirilen önemli dosyalar:** `MovieDetailPage.qml`, `TvDetailPage.qml`,
  `CastGrid.qml`, film servis/controller, dizi controller, detay testleri,
  `docs/components.md`.
- **Test sonucu:** 212 test geçti; Ruff başarılı. Yeni film QML testi
  profile kaynağını, 1366×768 / 1920×1080 düzenini, dar pencereyi ve kayıt
  sonrası fotoğraf korunmasını kontrol eder; dizi testi tek öneri şeridine
  güncellendi. Qt/QML uyarı kontrolü korunur.
- **Manuel kontrol:** Örnek verilerle offscreen film alt düzeninin ekran
  görüntüsü `/tmp/izlek-movie-layout.png` üzerinden incelendi;
  canlı masaüstü kontrolü yapılmadı.
- **Bilinen sorunlar:** TMDb fotoğrafı olmayan oyuncuda yer tutucu gösterilir.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Filmlerde yalnız önerilen içerikler

- **Yapılanlar:** Film detayından Benzer Filmler kaldırıldı; yalnız Önerilen
  Filmler afiş şeridi kaldı. Benzer film afişleri artık istenmiyor.
- **Değiştirilen önemli dosyalar:** `MovieDetailPage.qml`,
  `movie_detail_controller.py`, `tests/test_movie_detail.py`.
- **Test sonucu:** 212 test geçti; Ruff başarılı. Film arayüz testi önerilen
  içeriğin tek şeritte gösterilmesini kontrol eder.
- **Manuel kontrol:** Qt offscreen arayüz testi; canlı masaüstünde yapılmadı.
- **Bilinen sorunlar:** Bu değişiklikte saptanmadı.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Süre istatistiklerinde bilinen içerikleri toplama

- **Yapılanlar:** Film/bölüm ve toplam ekran süreleri yalnız pozitif runtime
  değerlerini toplar. Süresi bilinmeyen, sıfır veya negatif içerikler toplamı
  gizlemez; bilinen süre yoksa 0 gösterilir. Toplam kartının açıklaması süreye
  katılmayan film/bölüm adetlerini belirtir. İzlenmiş içerik sayaçları korunur.
  En çok izlenen dizilerde bilinen dakika toplamı gösterilir; aylık/top dizi
  hesaplarının mevcut bilinmeyen süreyi dışlama davranışı korunur.
- **Değiştirilen önemli dosyalar:** `services/statistics.py`,
  `StatisticsPanel.qml`, `tests/test_statistics.py`, `README.md`, mimari belgesi.
- **Test sonucu:** 218 test geçti; Ruff başarılı.
  Karışık/tümü bilinmeyen süreler, None/0/negatif değerler,
  metadata tamamlandığında yeni toplam ve QML açıklaması doğrulandı.
- **Manuel kontrol:** Qt offscreen arayüz testi; canlı masaüstünde yapılmadı.
- **Bilinen sorunlar:** Gösterilen toplam, yalnız süresi bilinen içerikleri
  kapsar; dışarıda kalan içeriklerin süresi tahmin edilmez.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — İstatistiklerden Takibim ve Favorilerim kaldırıldı

- **Yapılanlar:** İstatistikler sayfasındaki Takibim hızlı girişleri ve
  Favorilerim şeridi kaldırıldı. Sayfa yalnız istatistik controller'ını
  yeniler; kaldırılan bölümlerin kullanılmayan QML bağları temizlendi.
  Favori ve takip kayıtları veritabanında korunur; detay/kütüphane kalpleri
  çalışmaya devam eder.
- **Değiştirilen önemli dosyalar:** `HomePage.qml`, `Main.qml`,
  `tests/test_dashboard.py`, `tests/test_favorites.py`, README ve mimari belgesi.
- **Test sonucu:** 218 test geçti; Ruff başarılı.
  Kaldırılan kontrollerin yokluğu ve kayıtlı favorilerin korunması doğrulandı.
- **Manuel kontrol:** Qt offscreen arayüz testi; canlı masaüstünde yapılmadı.
- **Bilinen sorunlar:** Bu değişiklikte saptanmadı.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## 2026-10-04 — Sekme geçişi, kart çakışması ve geciken görseller

- **Yapılanlar:** StackView geçiş/push/pop işlemleri Immediate oldu; iki
  sayfanın animasyonda üst üste görünmesi kaldırıldı. Kütüphane açılışındaki
  çift refresh engellendi. LoadingState yalnız boş modelin ilk yüklenmesinde
  görünür; grid çerçevesi clip kullanır. Kütüphane ve Devam Et'te görsel
  sonuçları bütün model/delegeleri sıfırlamak yerine ilgili kartı günceller;
  klavye odağı korunur. Başarılı afiş/backdrop URL'leri sekme dönüşlerinde
  tutulur; metadata'daki yol değişirse yeniden yüklenir, placeholder tekrar
  denemeyi engellemez. Disk-cache okumaları ve Devam Et anahtarlık/HTTP
  kurulumu worker'a taşındı. Ağ configuration kilidi pending istek kilidinden
  ayrıldı; yavaş configuration isteği UI'daki sonraki poster çağrısını
  bekletmez. Detay görselleri başına bulk artwork bakım tetiklemesi kaldırıldı;
  mevcut .keep dosyaları tekrar yazılmaz. Tüm kütüphane görsellerini indirme
  ve tutma davranışı korunur.
- **Değiştirilen önemli dosyalar:** `Main.qml`, `LibraryPage.qml`,
  `LibraryPosterGrid.qml`, `ContinueWatchingCard.qml`, library/continue
  controller'ları, `image_service.py`, `cache/images.py`, `app.py`, ilgili testler.
- **Test sonucu:** 222 test geçti; Ruff başarılı. Disk/cache ve keyring
  işinin UI dışında kalması, yavaş configuration sırasında diğer isteğin
  hemen sıraya alınması, gerçek JPEG ile kart odağının korunması, skeleton
  çakışmaması ve sekme dönüşünde gereksiz afiş isteği olmaması test edildi.
- **Manuel kontrol:** Offscreen 1366×768, 50 film + 50 dizi + 500 bölümle
  beş sekme geçişi ölçüldü. Önce toplam 103 afiş çağrısı vardı; sonra 44 oldu
  ve son geçişlerde artmadı. Sıcak Diziler dönüşleri önce yaklaşık 65–91 ms,
  sonra 49–58 ms ölçüldü. Yerel örnek JPEG ve software backend kullanıldığı
  için bu ölçüm gerçek ağ/Wayland performans garantisi değildir.
  `/tmp/izlek-tabs.png` ekran görüntüsü incelendi; canlı masaüstü yapılmadı.
- **Bilinen sorunlar:** İlk açılışta indirilmeyen görsel hâlâ ağ hızına bağlıdır;
  indirilenler yerelde tutulur. Büyük veri query bütçeleri mevcut testlerdedir.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## GitHub hazırlığı ve Linux paket denetimi — 2026-10-04

- **Yapılanlar:** GitHub kaynak aktarımı için mevcut upstream geçmişi ayrı
  checkout'ta korundu. Linux paket durum tablosu, Arch arşiv dizini ve eski
  detay/istatistik açıklamaları README/CHANGELOG'da güncellendi.
- **Değiştirilen önemli dosyalar:** README.md, CHANGELOG.md,
  packaging/arch/README.md, docs/HANDOFF.md.
- **Test sonucu:** 222 pytest testi ve Ruff geçti. Wheel/sdist üretildi;
  wheel ayrı sanal ortama no-deps kuruldu, QML/logo/migration kaynakları
  kontrol edildi ve izole XDG ile offscreen package smoke geçti.
- **Manuel kontrol:** GitHub Releases API'de yayımlanmış sürüm bulunmadı.
  Yüklenecek kaynaklarda credential taraması eşleşme bulmadı.
- **Bilinen sorunlar:** Bu ortamda PyInstaller yok; AppImage/.deb binary
  üretimi ve temiz dağıtım testi yapılmadı. AUR checksum SKIP; gerçek
  yayımlanmış tag için checksum ve .SRCINFO üretimi gerekir. Wheel smoke
  mevcut sistem bağımlılıklarını kullanır; bağımsız dağıtım testi değildir.
- **Sonraki faz:** Linux binary sürümü yayımlama.

## RPM ve Snap paketleme — 2026-10-04

- **Yapılanlar:** Mevcut PyInstaller build/smoke üzerinden RPM üretim betiği
  ve spec; core24 amd64 strict Snapcraft tanımı/launcher eklendi. Fedora 43
  RPM ve Snap için elle başlatılan build/kurulum smoke workflow'ları eklendi.
  Snap XDG verileri revizyonlardan bağımsız SNAP_USER_COMMON altında kalır.
  SNAP_USER_COMMON refresh/revert ile otomatik veri rollback'i yapmaz.
- **Değiştirilen önemli dosyalar:** scripts/build_rpm.py, packaging/rpm/,
  snap/, .github/workflows/{rpm,snap}.yml, MANIFEST.in, .gitignore,
  README/CHANGELOG ve release/mimari belgeleri, tests/test_linux_packages.py.
- **Test sonucu:** 225 pytest testi ve Ruff başarılı; YAML/shell syntax,
  RPM payload arşivi, launcher argüman/XDG davranışı doğrulandı. Wheel/sdist
  üretildi ve yeni paketleme/workflow kaynaklarının sdist içinde olduğu
  kontrol edildi.
- **Manuel kontrol:** RPM/Snap kurulum ve yayın komutları belgelendi.
  Masaüstü arayüzü değişmedi; canlı Wayland/X11 testi yapılmadı.
- **Bilinen sorunlar:** Yerelde rpmbuild/Snapcraft/PyInstaller yok;
  Docker socket erişimi yok. Gerçek RPM/Snap binary build ve confinement
  testleri çalıştırılmadı; CI tanımlarının başarılı koşusu henüz görülmedi.
  Snap devel grade ile başlar; Store adı/yayın ve anahtarlık interface
  bağlantısı ayrıca doğrulanmalı. openSUSE/aarch64 CI kapsamı yok.
- **Sonraki faz:** RPM/Snap binary ve masaüstü doğrulaması.

## README ve uygulama ekran görüntüleri — 2026-10-04

- **Yapılanlar:** README logo, durum rozetleri, kısa özellik tablosu, Linux
  paket seçenekleri, hızlı başlangıç ve belge bağlantılarıyla düzenlendi.
  Teknik ayrıntılar development.md; ayrıntılı kullanım user-guide.md içine
  taşındı. Güncel QML'den beş gerçek ekran görüntüsü eklendi.
- **Değiştirilen önemli dosyalar:** README.md, docs/development.md,
  docs/user-guide.md, docs/screenshots/{discover,movies,shows,lists,statistics}.png.
- **Test sonucu:** 225 pytest testi ve Ruff başarılı. README ve yeni
  rehberlerdeki tüm yerel dosya/görsel bağlantıları doğrulandı.
- **Manuel kontrol:** Beş görsel 1440x1000 offscreen/software backend ile
  yakalandı ve incelendi. Geçici SQLite/XDG dizinleri, mock TMDB ve projedeki
  örnek SVG afişleri kullanıldı; gerçek kütüphane/token kullanılmadı.
- **Bilinen sorunlar:** Görseller demo içerik gösterir; mevcut Linux binary
  yayın sınırlamaları README'de korunur. Uygulama kodu değiştirilmedi.
- **Sonraki faz:** Kullanıcının sonraki isteği.

## Devam ederken

Önce mevcut dosyaları ve bu notu inceleyin; çalışan önceki faz davranışlarını koruyun. Her faz sonunda pytest ve Ruff çalıştırın, istenen Türkçe faz raporunu verin. Kullanıcının bir sonraki faz promptunu bekleyin.

Model/oturum değişiminde `AGENTS.md` içindeki **Faz Kapsamı ve Model Değişiminde Devamlılık** kurallarını uygulayın. Tamamlanmış fazları yeniden tasarlamayın; yalnızca istenen fazın zorunlu değişikliklerini yapın. [Faz 16–18 mimari denetimi](PHASE_16_18_ARCHITECTURE_AUDIT.md) genel yapının korunduğunu ve Faz 17'deki ayrı servis olmadan TMDb client çağırma sapmasını kaydeder. Bu sapma denetim sırasında uygulama kodu değiştirilerek giderilmemiştir.
