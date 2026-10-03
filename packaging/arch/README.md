# Arch Linux paketi

`PKGBUILD`, uygulamanın Arch standartlarındaki adı olan `izlek` paketini
üretir. Çalışma zamanında gereken Python ve Qt bağımlılıkları `depends`, wheel
oluşturmak için gerekenler `makedepends`, kalite araçları ise `checkdepends`
altında ayrılmıştır. Masaüstü kaydı ve ölçeklenebilir simge sırasıyla
`/usr/share/applications` ve `hicolor` tema yoluna kurulur.

PKGBUILD, `Teknoloji-Filozoflari/Izlek` repository'sindeki `v1.0.0` tag
arşivini kullanır. Tag yayımlandığında AUR'a göndermeden önce:

1. `updpkgsums` çalıştırıp `sha256sums` içindeki `SKIP` değerini gerçek SHA-256
   değeriyle değiştirin; ardından `.SRCINFO` üretin.

Yerel kaynak ağaçtan paketi sınamak için release tag'inden arşiv üretip
PKGBUILD source URL'sini geçici olarak bu dosyaya yönlendirin veya tag
yayımlandıktan sonra doğrudan `makepkg` çalıştırın:

```bash
git archive --format=tar.gz --prefix=izlek-1.0.0/ v1.0.0 \
  -o packaging/arch/izlek-1.0.0.tar.gz
cd packaging/arch
makepkg --syncdeps --install
```

Pacman yalnızca sistem paket dosyalarını kaldırır. İzlek'in XDG data, config
ve cache dizinlerindeki kullanıcı veritabanı, token ve görsel cache'i paket
kaldırıldığında silinmez.
