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

`Release Linux artifacts` workflow'u AppImage ve Debian workflow'larını
çağırır. Her ikisi de kalite kapısını çalıştırır, AppImage/.deb artefact'ını
üretir ve temiz Ubuntu 22.04 ile 24.04 hostlarında smoke test yapar.

Workflow, tag ile `pyproject.toml` sürümünün birebir eşleşmesini zorunlu tutar.
Başarılı adımların sonunda GitHub release, sürüme ait not dosyasıyla otomatik
oluşturulur veya aynı tag tekrar çalıştırıldıysa notlar ve asset'ler
güncellenir. `v1.0.1` release'i şu dosyaları içerir:

- `Izlek-1.0.1-x86_64.AppImage` ve SHA-256 dosyası
- `izlek_1.0.1_amd64.deb`
- `Izlek-1.0.1-source.tar.gz` ve SHA-256 dosyası

GitHub ayrıca tag için kendi otomatik source code `.zip` ve `.tar.gz`
bağlantılarını gösterir. Workflow'un ürettiği source archive sabit
`izlek-1.0.1/` kök diziniyle ayrıca release asset olarak yüklenir.

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

## v1.0.1 yayını

v1.0.0 tag'i korunmuştur; düzeltilmiş paketler ayrı v1.0.1 sürümündedir.
AppImage, DEB, RPM ve Snap elle başlatılan build workflow'larından alınır;
`Installed package X11 check` workflow'u başarılı build koşusunun
artifact'ini indirip temiz hedefte kurar ve sanal X11 penceresini açar.
Doğrulanmış dosyalar, kaynak arşivi, wheel/sdist ve SHA256SUMS aynı
GitHub release'ine yüklenir. Nix kullanıcıları v1.0.1 flake tag'ini kullanır.

AppImage tabanı Ubuntu 22.04 / glibc 2.35, RPM tabanı Fedora 43 / glibc 2.42'dir.
Snap GitHub'dan yerel dosyayla kurulabilir; Snap Store'a gönderilmemiştir.
AUR yayını bu işlemlere dahil değildir.
