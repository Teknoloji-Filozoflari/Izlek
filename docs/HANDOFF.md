# İzlek devir notu

Son durum: **Faz 33 release hazırlığı tamamlandı; v1.0.0 tag/release yayımlanmadı.** Yeni faz, kullanıcı açıkça istemeden başlatılmamalı. Uygulama Linux için Python/PySide6/QML masaüstü uygulamasıdır; web uygulaması değildir. Ana proje kuralları [AGENTS.md](../AGENTS.md) ve [mimari notlarında](architecture.md) yer alır.

## Tamamlanan işler

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

## Devam ederken

Önce mevcut dosyaları ve bu notu inceleyin; çalışan önceki faz davranışlarını koruyun. Her faz sonunda pytest ve Ruff çalıştırın, istenen Türkçe faz raporunu verin. Kullanıcının bir sonraki faz promptunu bekleyin.

Model/oturum değişiminde `AGENTS.md` içindeki **Faz Kapsamı ve Model Değişiminde Devamlılık** kurallarını uygulayın. Tamamlanmış fazları yeniden tasarlamayın; yalnızca istenen fazın zorunlu değişikliklerini yapın. [Faz 16–18 mimari denetimi](PHASE_16_18_ARCHITECTURE_AUDIT.md) genel yapının korunduğunu ve Faz 17'deki ayrı servis olmadan TMDb client çağırma sapmasını kaydeder. Bu sapma denetim sırasında uygulama kodu değiştirilerek giderilmemiştir.
