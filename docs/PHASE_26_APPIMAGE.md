# Faz 26 AppImage altyapısı

## Üretim sırası

`scripts/build_appimage.py` aşağıdaki sırayı zorunlu tutar:

1. `packaging/izlek.spec` ile PyInstaller one-folder build oluşturulur.
2. `dist/izlek/izlek --package-smoke-test` gerçek QML'i offscreen açar.
3. QML, ikonlar ve Alembic migration dosyalarının one-folder içinde olduğu
   doğrulanır.
4. `build/appimage/Izlek.AppDir` oluşturulur ve `AppRun` üzerinden tekrar
   smoke edilir.
5. appimagetool ile `dist/Izlek-<version>-x86_64.AppImage` üretilir.
6. AppImage yeniden smoke edilir ve `.sha256` dosyası yazılır.

`--appdir-only`, ilk dört adımı çalıştırır; böylece AppImage'a geçmeden önce
one-folder build doğrulanmış olur.

## Paket içeriği

- `AppRun`: `usr/lib/izlek/izlek` executable'ını başlatır.
- `izlek.desktop`: `Name=İzlek`, `Exec=izlek`, `Icon=izlek`,
  `Categories=AudioVideo;Video;` metadata'sını taşır.
- `izlek.svg` ve `.DirIcon`: mevcut İzlek vektör ikonuna bağlanır.
- `usr/lib/izlek`: PyInstaller one-folder Python, PySide6/Qt ve uygulama
  içeriğidir.
- `usr/share/doc/izlek/LICENSE`: GPL-3.0-or-later lisans dosyasıdır.

PyInstaller paket içindeki modüllerin `__file__` değerini bundle konumuna göre
ayarlar. Spec bu nedenle QML/resources/migration dosyalarını kaynak kodun
beklediği `izlek/...` yapısında tutar. Bu yaklaşım
[PyInstaller runtime belgesiyle](https://pyinstaller.org/en/stable/runtime-information.html)
uyumludur. AppDir kökündeki `AppRun`, desktop entry ve ikon düzeni
[AppDir specification](https://docs.appimage.org/reference/appdir.html)
ile uyumludur.

## glibc uyumluluğu

x86_64 build işi `quay.io/pypa/manylinux_2_28_x86_64` container'ında Python
3.11 ile çalışır. manylinux projesi bu image'ın glibc 2.28 ve daha yeni
dağıtımlar için hedeflendiğini belirtir. Normal geliştirme bağımlılıklarını
daraltmamak için yalnız AppImage build'inde
`packaging/constraints-appimage.txt` uygulanır; PySide6 6.8.2.1 x86_64 wheel'i
de manylinux_2_28 tabanlıdır.

AppImage aracı `AppImage/appimagetool` 1.9.1, runtime ise
`AppImage/type2-runtime` 20251108 sürümünden indirilir. Workflow GitHub release
API'sindeki SHA-256 digest'i doğrular; mutable `continuous` asset kullanılmaz.

## Kullanıcı verisi ve smoke testi

`AppRun` `HOME` veya XDG değişkenlerini değiştirmez. Uygulamanın mevcut XDG
çözümü korunur:

- database: `$XDG_DATA_HOME/izlek/izlek.sqlite3`
- config/token fallback: `$XDG_CONFIG_HOME/izlek/`
- image cache: `$XDG_CACHE_HOME/izlek/images/`
- log: `$XDG_STATE_HOME/izlek/logs/`

Paket smoke testi bu dizinleri geçici, birbirinden ayrı user dizinlerine
yönlendirir; database ve config'in orada oluştuğunu, one-folder/AppDir/AppImage
yanında yeni dosya oluşmadığını denetler.

## GitHub artifact

`.github/workflows/appimage.yml`, manuel `workflow_dispatch` ve release
workflow'unun `workflow_call` çağrılarında önce Faz 25 kalite kapısını çalıştırır.
Başarılı build sonucunda
AppImage, SHA-256 ve build ortamı sürüm bilgisini `izlek-appimage-x86_64`
artifact'ı olarak yükler. Ardından aynı artifact temiz Ubuntu 22.04 ve 24.04
runner'larında `APPIMAGE_EXTRACT_AND_RUN=1` ile test edilir.
