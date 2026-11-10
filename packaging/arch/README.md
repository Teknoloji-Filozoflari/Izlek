# Arch Linux paketi

`PKGBUILD`, uygulamanın Arch standartlarındaki adı olan `izlek` paketini
üretir. Çalışma zamanında gereken Python ve Qt bağımlılıkları `depends`, wheel
oluşturmak için gerekenler `makedepends`, kalite araçları ise `checkdepends`
altında ayrılmıştır. Masaüstü kaydı ve ölçeklenebilir simge sırasıyla
`/usr/share/applications` ve `hicolor` tema yoluna kurulur.

PKGBUILD, `Teknoloji-Filozoflari/Izlek` repository'sindeki `v1.1.0` tag
arşivini kullanır. `sha256sums` yayımlanmış GitHub tag arşivinin gerçek
SHA-256 değeridir (`SKIP` değildir). Yeni sürümde:

1. `pkgver` değerini güncelleyin.
2. Tag arşivini indirip `sha256sums` değerini değiştirin:
   `curl -sL "https://github.com/Teknoloji-Filozoflari/Izlek/archive/refs/tags/v${pkgver}.tar.gz" | sha256sum`
3. `.SRCINFO` dosyasını `makepkg --printsrcinfo > .SRCINFO` ile yenileyin.
4. `python scripts/verify_arch_pkgbuild.py` ile kaynak arşivi ve checksum'u
   doğrulayın.

Yerel kaynak ağaçtan paketi sınamak için release tag'inden arşiv üretip
PKGBUILD source URL'sini geçici olarak bu dosyaya yönlendirin veya tag
yayımlandıktan sonra doğrudan `makepkg` çalıştırın:

```bash
git archive --format=tar.gz --prefix=Izlek-1.1.0/ v1.1.0 \
  -o packaging/arch/izlek-1.1.0.tar.gz
cd packaging/arch
makepkg --syncdeps --install
```

Pacman yalnızca sistem paket dosyalarını kaldırır. İzlek'in XDG data, config
ve cache dizinlerindeki kullanıcı veritabanı, token ve görsel cache'i paket
kaldırıldığında silinmez.
