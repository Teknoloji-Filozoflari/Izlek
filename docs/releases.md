# Release süreci

İzlek'in GitHub release'i yalnızca `v*` biçimindeki bir tag push edildiğinde
oluşturulur. Release workflow'u kişisel TMDb tokenı veya başka bir kullanıcı
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
güncellenir. `v1.0.0` release'i şu dosyaları içerir:

- `Izlek-1.0.0-x86_64.AppImage` ve SHA-256 dosyası
- `izlek_1.0.0_amd64.deb`
- `Izlek-1.0.0-source.tar.gz` ve SHA-256 dosyası

GitHub ayrıca tag için kendi otomatik source code `.zip` ve `.tar.gz`
bağlantılarını gösterir. Workflow'un ürettiği source archive sabit
`izlek-1.0.0/` kök diziniyle ayrıca release asset olarak yüklenir.

## Tag sonrası

GitHub release notlarını, artefact adlarını ve checksum'u gözden geçirin.
PKGBUILD, AUR'a gönderilecekse release asset'i yerine AUR repository'sindeki
doğrulanmış HTTPS tag kaynağı ve checksum ile güncel kalmalıdır.
