# Faz 32 — 1.0 release adayı QA raporu

Tarih: 2026-10-04

## Karar

**NO-GO — mevcut durumla 1.0 release yapılmamalıdır.**

Uygulama katmanında otomatik olarak kapsanan akışlarda crash veya veri kaybı
bulunmadı. Güncel kaynaktan üretilen wheel temiz ve izole bir kullanıcı
dizininde iki kez açıldı; veritabanı migration'ı `0003_season_freshness`,
`PRAGMA integrity_check` sonucu `ok` oldu. Bununla birlikte AppImage, `.deb` ve
AUR paketlerinin gerçek build/install smoke testleri tamamlanamadı. Faz 31'den
kalan TMDB logo ve SQLite metadata retention uyumluluk engelleri de açıktır.

## Senaryo sonuçları

| # | Senaryo | Sonuç | Kanıt / kapsam |
| --- | --- | --- | --- |
| 1 | Uygulama ilk açılış | Geçti | Güncel wheel yeni venv ve boş XDG dizinlerinde `--package-smoke-test` ile açıldı; DB ve pencere ayarı oluştu. |
| 2 | Token setup | Geçti (mock) | `test_fresh_onboarding_and_settings_token_change`; geçersiz token reddi, geçerli token kaydı, maskeli alan ve onboarding geçişi. |
| 3 | Movie search | Geçti (mock) | `test_controller_separates_media_and_ignores_stale_results` ve TMDB search endpoint testleri. |
| 4 | Movie add | Geçti (mock) | `test_movie_sections_save_metadata_and_personal_state_survives_restart`; durum, favori ve liste verisi yeniden açılışta korunuyor. |
| 5 | TV search | Geçti (mock) | Global search film/dizi ayrımı ve TMDB TV search endpoint testleri. |
| 6 | TV add | Geçti (mock) | `test_tv_progress_bulk_refresh_and_restart`; dizi durumu SQLite'a yazılıyor ve yeniden açılışta korunuyor. |
| 7 | Episode mark | Geçti (mock) | Tek bölüm işaretleme ve geri alma servis/controller testleri. |
| 8 | Full season mark | Geçti (mock) | Sezon toplu işaretleme ve UI onay testi; eksik metadata durumunda kısmi yazma reddediliyor. |
| 9 | Full series mark | Geçti (mock) | Tüm dizi toplu işaretleme, geri alma ve restart testi. |
| 10 | Favorite | Geçti | Film/dizi favorileri, durumdan bağımsız kullanım ve bilinmeyen medya koruması. |
| 11 | Custom list | Geçti | CRUD, üyelik, sıra, doğrulama ve restart kalıcılığı. |
| 12 | Continue Watching | Geçti | Sonraki bölüm seçimi, özel/gelecek bölüm filtreleri ve hızlı aksiyon. |
| 13 | Discover | Geçti (mock) | Filtre, puan/oy eşiği ve kontrollü sayfalama. |
| 14 | Provider | Geçti (mock) | Abonelik/kiralama/satın alma grupları, güvenli TMDB linki ve JustWatch kaynak metni. |
| 15 | Offline startup | Geçti | TV verisi online doldurulduktan sonra DB yeniden açıldı; bağlantı hatasında cached metadata ve kişisel durumlar okundu. Boş XDG package smoke ağ gerektirmedi. |
| 16 | Metadata refresh | Geçti (mock) | Eski metadata yenilenirken status, favorite, list ve episode progress korundu; offline/timeout/404 fallback test edildi. |
| 17 | Export | Geçti | JSON şeması, `0600` izin, token/cache yolu sızıntısı olmaması ve atomik yazma testleri. |
| 18 | Clean database import | Geçti | Dolu kaynaktan temiz SQLite hedefe import sonrası kullanıcı durumunun eşdeğerliği doğrulandı. |
| 19 | Application restart | Geçti | Aynı izole XDG dizininde güncel wheel iki ardışık kez açıldı; SQLite bütünlüğü `ok`. |
| 20 | Cache clear | Geçti | `test_image_cache_clear_removes_only_disposable_entries`; yalnız disposable `.img` girdileri siliniyor. |
| 21 | Token change | Geçti (mock) | Ayarlar ekranından token değiştirme, yeniden doğrulama, alanı temizleme ve kalıcı kayıt. |
| 22 | Keyboard navigation | Geçti (offscreen) | Ctrl+1–5, Ctrl+`,`, Ctrl+K, Esc, odak ve dialog akışları QTest ile çalıştı. |
| 23 | AppImage | **Bloke** | Gerçek artefakt yok; yerel build `PyInstaller bulunamadı` ile status 2 döndü. `appimagetool` smoke'u çalışmadı. |
| 24 | `.deb` | **Bloke** | Gerçek artefakt yok; yerel build `dpkg-deb bulunamadı` ile status 2 döndü. Temiz Ubuntu install/launcher/uninstall smoke'u çalışmadı. |
| 25 | AUR build | **Bloke** | `.SRCINFO` güncel ve `namcap` temiz; gerçek `makepkg --verifysource` yerel release tarball'ı olmadığı için durdu. PKGBUILD'de upstream ve checksum yer tutucuları sürüyordu. |

`(mock)` işaretli ağ testleri `httpx.MockTransport` kullanır; kişisel TMDB tokenı
ve gerçek TCP bağlantısı kullanılmamıştır.

## Uygulanan release-blocker düzeltmesi

- `dist/izlek-0.1.0.dev0-py3-none-any.whl` eski bir fazdan kalmıştı ve güncel
  DB/service/QML dosyalarını içermiyordu. Wheel mevcut kaynaktan
  `python -m build --wheel --no-isolation` ile yeniden üretildi.
- Yeniden üretilen wheel temiz venv'e kuruldu, iki açılış yaptı ve veritabanı
  bütünlük kontrolünü geçti.
- Cache temizleme senaryosunun kalıcı regresyon testi eklendi.

## Açık release engelleri

1. Hakkında/Credits ekranında TMDB'nin resmî, onaylı ve değiştirilmemiş logosu
   yoktur. Logo eklenmeden ve İzlek markasından daha az baskın olduğu görsel
   olarak doğrulanmadan TMDB uyumluluk onayı verilmemelidir.
2. XDG görsel cache'i 180 günle sınırlı olsa da SQLite'taki TMDB metadata,
   sezon/bölüm metadata ve provider JSON'u için kişisel tracking verisini
   koruyan fiziksel 180 günlük retention işi yoktur.
3. AppImage ve `.deb` artefaktları bu kaynak revizyonundan üretilip temiz
   Ubuntu ortamında kurulum/açılış/kaldırma testinden geçmemiştir.
4. AUR kaynağı release tag URL'sine ve gerçek SHA-256 değerine bağlı değildir;
   gerçek `makepkg` build'i tamamlanmamıştır.
5. Release metadata henüz final değildir: proje sürümü `0.1.0.dev0`, Arch
   sürümü `0.1.0`; upstream ve Debian homepage/maintainer alanlarında yer
   tutucular vardır.

Retention düzeltmesi son dakika QA sırasında uygulanmadı: mevcut şemada
`media_item.original_title` zorunlu, bölüm ilerlemesi episode satırlarına bağlı
ve import/export eski metadata'yı yeniden getirebilir. Yetersiz kapsamlı bir
temizleme kişisel ilerleme veya liste verisi kaybı riski taşır. Bu risk 1.0 için
release'i durdurma nedenidir; veri silen hızlı bir yama için gerekçe değildir.

## Çalıştırılan kontroller

```text
.venv/bin/python scripts/quality.py
Ruff: PASS
pytest: 144 passed

.venv/bin/python -m pytest -q tests/test_image_service.py
7 passed

.venv/bin/python scripts/quality.py (nihai)
Ruff: PASS
pytest: 145 passed

.venv/bin/python -m build --wheel --no-isolation
PASS

fresh wheel install + package smoke, launch 1
PASS
fresh wheel install + package smoke, launch 2
PASS
SQLite migration: 0003_season_freshness
SQLite integrity: ok

makepkg --printsrcinfo vs packaging/arch/.SRCINFO
PASS, fark yok
namcap packaging/arch/PKGBUILD
PASS, uyarı/hata yok
makepkg --verifysource
BLOCKED, izlek-0.1.0.tar.gz yok

scripts/build_appimage.py --appdir-only
BLOCKED, PyInstaller yok
scripts/build_deb.py
BLOCKED, dpkg-deb yok
```

Test sayısı cache-clear regresyonu eklendikten sonra 145'e çıktı. Rapor ve devir
notu güncellendikten sonraki nihai kalite kapısı da geçti.

## Release için yeniden doğrulama kapısı

- Resmî TMDB logosunu resmî varlıktan değiştirmeden ekle; About/Credits ve
  prominence kontrolünü yap.
- Kişisel tracking/favorite/list/progress verisini asla silmeden 180 günlük
  SQLite TMDB metadata retention tasarımını migration ve veri kaybı testleriyle
  uygula.
- Gerçek upstream URL, bakımcı bilgisi ve `1.0.0` sürümünü belirle; `v1.0.0`
  kaynak arşivinin SHA-256 değerini PKGBUILD'e yaz.
- Release workflow'undan AppImage ve `.deb` üret; temiz Ubuntu 22.04/24.04
  ortamında install, launcher, restart ve uninstall-user-data-preservation
  smoke testlerini geçir.
- Gerçek tag tarball'ı ile temiz Arch ortamında `makepkg`, test, install,
  desktop launcher ve uninstall-user-data-preservation kontrollerini geçir.
- Son kez `python scripts/quality.py` çalıştır; crash veya veri kaybı görülürse
  release'i durdur.
