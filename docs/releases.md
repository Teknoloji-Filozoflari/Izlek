# Release süreci

İzlek'in GitHub release'i `v*` tag push workflow'u veya doğrulanmış
workflow artifact'leriyle GitHub CLI üzerinden oluşturulabilir. Release workflow'u kişisel TMDb tokenı veya başka bir kullanıcı
secret'ı kullanmaz. Test paketi gerçek TCP bağlantılarını engeller ve TMDb
yanıtlarını mock'lar.

## Tag öncesi

1. `pyproject.toml` sürümünü yayımlanacak sürümle eşleştirin ve
   `CHANGELOG.md` kaydını ve `docs/release-notes/vX.Y.Z.md` dosyasını
   tamamlayın.
2. Yerelde `python scripts/quality.py` ve
   `python -m pip wheel . --no-deps --wheel-dir dist` komutunu çalıştırın.
3. Arch yayını yapılacaksa `packaging/arch/PKGBUILD` içindeki upstream URL,
   tag kaynak adresi ve SHA-256 değerini gerçek release kaynağıyla güncelleyin;
   ardından `.SRCINFO` dosyasını `makepkg --printsrcinfo` ile yenileyin.
4. Token, SQLite verisi, cache veya başka kişisel bilgi içermezken imzalı ya da
   normal bir `vX.Y.Z` git tag'i oluşturup remote'a push edin.

## Otomatik akış

`Release desktop artifacts` workflow'u AppImage, Debian ve Windows EXE
workflow'larını çağırır. Linux paketleri kendi kalite/açılış kontrollerinden
geçer. Windows runner EXE'yi üretir; paketli QML, kurulum, açılış, kaldırma
ve kişisel veriyi koruma kontrollerinden sonra artifact olarak sunar.

Workflow, tag ile `pyproject.toml` sürümünün birebir eşleşmesini zorunlu tutar.
Başarılı adımların sonunda GitHub release, sürüme ait not dosyasıyla otomatik
oluşturulur veya aynı tag tekrar çalıştırıldıysa notlar ve asset'ler
güncellenir. v1.1.0 tag yayını beklenen dosyalar:

- `Izlek-1.1.0-x86_64.AppImage` ve SHA-256 dosyası
- `izlek_1.1.0_amd64.deb`
- `Izlek-1.1.0-windows-x64-setup.exe` ve SHA-256 dosyası
- `Izlek-1.1.0-source.tar.gz` ve SHA-256 dosyası

Windows iş akışı kaynak/paketleme push'unda veya elle de başlatılabilir;
[Windows rehberi](../packaging/windows/README.md) indirme adımlarını açıklar.

GitHub ayrıca tag için kendi otomatik source code `.zip` ve `.tar.gz`
bağlantılarını gösterir. Workflow'un ürettiği source archive sabit
`izlek-<sürüm>/` kök diziniyle ayrıca release asset olarak yüklenir.

## Tag sonrası

GitHub release notlarını, artefact adlarını ve checksum'u gözden geçirin.
PKGBUILD, AUR'a gönderilecekse release asset'i yerine AUR repository'sindeki
doğrulanmış HTTPS tag kaynağı ve checksum ile güncel kalmalıdır.

## RPM ve Snap geliştirme build'leri

`RPM package` ve `Snap package` workflow'ları `workflow_dispatch` ile elle
başlatılır. Çıktılar Actions artifact'i olarak saklanır; mevcut tag release
akışına otomatik eklenmez. RPM için Fedora 43 x86_64, Snap için core24 amd64
hedeflenir. Başarılı build/kurulum kontrollerinden sonra RPM release asset
olarak ayrıca yüklenebilir. Snap Store yayını için ad kaydı, gerçek masaüstü
sandbox kontrolü ve uygun grade/channel gerekir; Store upload otomasyonu yok.
Snap sürümü `snap/snapcraft.yaml` ve `pyproject.toml` içinde birlikte güncellenir.

## v1.1.0 yayını

v1.0.x tag'leri korunmuştur; özellik hattı v1.1.0'tadır. Tag push
`Release desktop artifacts` ile AppImage, DEB, Windows EXE ve kaynak
arşivini GitHub release'ine yükler. RPM ve Snap `workflow_dispatch` ile
ayrı üretilir; doğrulandıktan sonra aynı release'e eklenebilir.
Nix kullanıcıları `v1.1.0` flake tag'ini kullanır.

AppImage tabanı Ubuntu 22.04 / glibc 2.35, RPM tabanı Fedora 43 / glibc 2.42'dir.
Snap GitHub'dan yerel dosyayla kurulabilir; Snap Store'a gönderilmemiştir.
AUR yayını bu işlemlere dahil değildir.

## v1.0.1 yayını (tarihsel)

v1.0.0 tag'i korunmuştur; düzeltilmiş paketler ayrı v1.0.1 sürümündedir.
AppImage, DEB, RPM ve Snap elle başlatılan build workflow'larından alındı;
doğrulanmış dosyalar, kaynak arşivi, wheel/sdist ve SHA256SUMS aynı
GitHub release'ine yüklendi.
