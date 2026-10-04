# Nix / NixOS paketi

İzlek, Nixpkgs Python/Qt bağımlılıklarıyla kaynak koddan paketlenir.
PyInstaller veya pip ile sistem Python'una kurulum gerekmez. Flake çıktıları
`x86_64-linux` ve `aarch64-linux` için tanımlıdır; CI x86_64 üzerinde çalışır.
Bu paket henüz resmî Nixpkgs deposuna eklenmiş değildir.

## Çalıştırma ve kullanıcı kurulumu

NixOS'ta flake komutlarını etkinleştirmek için sistem yapılandırmasına:

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

Ardından normal NixOS yapılandırma yenilemesini uygulayın. Kaynak depoyu
indirmeden çalıştırmak veya kullanıcı profiline kurmak için:

```bash
nix run github:Teknoloji-Filozoflari/Izlek/v1.0.1
nix profile install github:Teknoloji-Filozoflari/Izlek/v1.0.1
```

Proje kökünde yerel build ve kontrol:

```bash
nix build
nix flake check --print-build-logs
./result/bin/izlek
```

Flake desteği olmayan Nix kullanımında, Nixpkgs kanalı tanımlıysa:

```bash
nix-build
./result/bin/izlek
```

`default.nix` mevcut Nixpkgs kanalını kullanır; flake bağımlılık kilidini
kullanmaz. Kanalın Python/Qt sürümleri pyproject.toml gereksinimlerini
karşılamalıdır. Flake varsayılanı NixOS 25.11 dalıdır; `flake.lock`, tam
Nixpkgs revizyonunu sabitler. Güncellemek için `nix flake update nixpkgs`
sonrasında `nix flake check` çalıştırın ve lock dosyasını commit edin.

## NixOS sistem yapılandırması

Mevcut sistem flake'inize İzlek girdisi ve paketi ekleyin. Aşağıdaki parça
örnektir; `myhost` ve configuration.nix sizin sisteminizdeki ad/yola karşılık
gelmelidir. Mevcut diğer ayarlarınızı koruyun.

```nix
{
  inputs.izlek.url = "github:Teknoloji-Filozoflari/Izlek/v1.0.1";

  outputs = { nixpkgs, izlek, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./configuration.nix
        {
          environment.systemPackages = [
            izlek.packages.x86_64-linux.default
          ];
        }
      ];
    };
  };
}
```

Home Manager'da flake girdisini modüle geçirdiğinizde aynı paket
`home.packages` içine eklenebilir. ARM64 sistemlerde `aarch64-linux`
çıktısını kullanın; bu mimaride gerçek build doğrulaması henüz yapılmadı.

## Masaüstü ve veri

Qt plugin/QML yolları Python başlatıcısına sarılır; Qt Quick, SVG ve Wayland
modülleri açık bağımlılıklardır. `.desktop` ve simge paket çıktısının `share/`
dizinine kurulur. Wayland/X11 masaüstünde `izlek` veya uygulama menüsünden
başlatılır. Uygulama dosyaları salt okunur Nix store'dadır; SQLite, ayarlar
ve görseller normal XDG kullanıcı dizinlerine yazılır. Nix profilinden
paketi kaldırmak kişisel XDG verilerini kaldırmaz.

TMDB için kendi API Read Access Tokenınız gerekir. Sistem anahtarlığı için
masaüstünüzün Secret Service/KWallet hizmeti çalışmalıdır; kullanılamazsa
uygulamanın kullanıcıya açık token dosyası fallback'i geçerlidir.

## Doğrulama durumu

[2026-10-04 CI koşusu](https://github.com/Teknoloji-Filozoflari/Izlek/actions/runs/37212410490)
x86_64 Linux üzerinde başarılı: Nix build, 226 pytest testi, Ruff ve kurulu
paketin Qt/QML offscreen açılış kontrolü geçti. Bu kontrol Ubuntu runner'daki
Nix sandbox'ında yapıldı; gerçek NixOS masaüstü testi değildir.


Nix package workflow'u paket build'inde Ruff/pytest çalıştırır; ayrı bir
kontrol kurulu ve Qt yolları sarılmış `izlek` başlatıcısını izole XDG ile
offscreen açar, migration/veritabanı ve pencere ayarlarının oluştuğunu sınar.
Gerçek NixOS Wayland/X11 masaüstü kontrolü ayrıca gerekir.

Referanslar: [Nixpkgs Qt paketleme](https://github.com/NixOS/nixpkgs/blob/nixos-25.11/doc/languages-frameworks/qt.section.md),
[Python paketleme](https://wiki.nixos.org/wiki/Python).
