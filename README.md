<div align="center">

<img src="src/izlek/resources/icons/izlek.svg" width="80" alt="İzlek simgesi">

# İzlek

**Film ve dizilerini yerelde takip et — kaldığın bölüm, listelerin ve notların cihazında kalsın.**

Linux öncelikli masaüstü uygulaması; Windows 10/11 için EXE kurulum paketi de
yayımlanır. Hesap, reklam veya analytics yok. İçerik bilgisi için kendi
**TMDB API Read Access Token**’ın yeterli.

[![CI](https://github.com/Teknoloji-Filozoflari/Izlek/actions/workflows/ci.yml/badge.svg)](https://github.com/Teknoloji-Filozoflari/Izlek/actions/workflows/ci.yml)
[![Sürüm](https://img.shields.io/badge/Sürüm-1.1.0-62C7B4)](https://github.com/Teknoloji-Filozoflari/Izlek/releases/tag/v1.1.0)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-62C7B4)](#kurulum-ve-indirme)
[![Lisans](https://img.shields.io/badge/Lisans-GPL--3.0--or--later-blue)](LICENSE)

[Yenilikler · 1.1](#yenilikler--11) · [İndir](#kurulum-ve-indirme) ·
[Özellikler](#özellikler) · [Ekran görüntüleri](#ekran-görüntüleri) ·
[Belgeler](#belgeler)

</div>

![Film kütüphanesi, izleme durumları ve kişisel puanlar](docs/screenshots/card-direct-1366.png)

<p align="center">
  <a href="https://github.com/Teknoloji-Filozoflari/Izlek/releases/tag/v1.1.0"><strong>v1.1.0’ı indir</strong></a>
  ·
  <a href="#kaynak-koddan-çalıştır">Kaynak koddan çalıştır</a>
</p>

## Yenilikler · 1.1

**1.1.0**, birleşik roadmap sonrası ilk özellik sürümüdür. Kaynak kod ve
yayımlanan paketler aynı sürümü işaret eder.

| | 1.1 ile gelenler |
| --- | --- |
| **Sağlayıcı grupları** | Detayda izleme seçenekleri Abonelik, Ücretsiz, Reklamlı, Kiralama ve Satın Alma olarak ayrılır; ücretsiz/reklamlı satırlar bilgilendirme amaçlıdır. |
| **Meta veri kaynakları** | TMDb varsayılan; isteğe bağlı Trakt, TVmaze ve OMDb. İzleme bölgesi Ayarlar’dan seçilir; OMDb/Trakt ile canlı zenginleştirme. |
| **Sana özel öneriler** | Keşfet’te DiscoverService tabanlı öneri şeridi; kayıtlı/izlenmiş içerikler ayıklanır. |
| **Çok dilli arayüz** | Ayarlar’dan dil seçimi: Türkçe, İngilizce, Azerbaycan, İspanyolca, Kazak, Rusça, Türkmence, Özbek. |
| **Koleksiyon listeleri** | Film detayında TMDb koleksiyon/serisindeki yapımları özel listeye ekle (liste-only; kütüphane durumu elle kalır). |
| **Akıllı listeler ve etiketler** | İzlenmemiş favoriler, favoriler, izleniyor, izlenecek, yüksek puanlı; kullanıcı etiketleri sanal liste olarak görünür. |
| **Açık / koyu tema** | Ayarlar’dan tema seçimi; ışık token’larıyla tutarlı arayüz. |
| **İzleme kronolojisi** | `watched_at` ve yeniden izleme sayacı; film aktivitesi, son 12 ay grafiği ve son izlemeler günlüğü. |
| **İçe aktarma** | Trakt ve Letterboxd içe aktarma; JSON yedek şema v4. |
| **Windows EXE** | Tag yayınıyla birlikte x64 kurulum paketi release’e eklenir. |

Ayrıntılı kayıt: [CHANGELOG](CHANGELOG.md) · [sürüm notları](docs/release-notes/v1.1.0.md).

## Kurulum ve indirme

Hazır paketler **[v1.1.0 GitHub Release](https://github.com/Teknoloji-Filozoflari/Izlek/releases/tag/v1.1.0)**
sayfasındadır. Tag akışı AppImage, DEB, Windows EXE ve kaynak arşivini yükler;
RPM / Snap doğrulanmış build sonrası ayrıca eklenebilir.

| Biçim | Hedef | Kurulum |
| --- | --- | --- |
| **Windows EXE** | Windows 10/11 x64 | `Izlek-1.1.0-windows-x64-setup.exe` dosyasını çalıştır. |
| **AppImage** | x86_64 Linux, glibc 2.35+ | `chmod +x Izlek-1.1.0-x86_64.AppImage`, ardından çalıştır. |
| **DEB** | Ubuntu 22.04 / 24.04 amd64 | `sudo apt install ./izlek_1.1.0_amd64.deb` |
| **RPM** | Fedora 43 x86_64 | `sudo dnf install ./izlek-1.1.0-1.fc43.x86_64.rpm` (asset varsa) |
| **Snap** | snapd bulunan amd64 | `sudo snap install --dangerous ./izlek_1.1.0_amd64.snap` (asset varsa) |
| **Nix / NixOS** | x86_64 Linux | `nix run github:Teknoloji-Filozoflari/Izlek/v1.1.0` |
| **Wheel / kaynak** | Python 3.11+ | Release dosyaları; sistem Qt bağımlılıkları gerekir. |
| **Arch / AUR** | Arch Linux | [PKGBUILD rehberi](packaging/arch/README.md); AUR yayını yok. |

AppImage için FUSE yoksa:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./Izlek-1.1.0-x86_64.AppImage
```

Snap’te anahtarlık için `sudo snap connect izlek:password-manager-service`.
Ubuntu’da Qt runtime gerekirse:

```bash
sudo apt install libegl1 libgl1 libfontconfig1 libx11-6 libx11-xcb1 \
  libxcb1 libxkbcommon0 libxkbcommon-x11-0
```

Checksum için release’teki `SHA256SUMS` (veya dosya yanındaki `.sha256`)
kullanılabilir. Rehberler: [release süreci](docs/releases.md),
[Windows](packaging/windows/README.md), [DEB](packaging/debian/README.md),
[RPM](packaging/rpm/README.md), [Snap](snap/README.md),
[Nix](packaging/nix/README.md).

### Kaynak koddan çalıştır

Python **3.11+**, `pip` ve PySide6 çalışma zamanı gerekir.

```bash
git clone https://github.com/Teknoloji-Filozoflari/Izlek.git
cd Izlek
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/run_dev.py
```

Windows PowerShell: `python -m venv .venv`, sonra
`.venv\Scripts\Activate.ps1`. `run_dev.py` kurulu uygulamadan ayrı
`.dev-data/` kullanır; sistem kütüphanesi ve tokenı paylaşılmaz.

### İlk açılış

1. TMDB hesabından **API Read Access Token** al.
2. İzlek’te tokenı gir → **Tokenı Test Et** → **Kaydet**.
3. Ana Sayfa’dan keşfet veya ara; isteğe bağlı Ayarlar’dan dil, tema, meta veri
   kaynağı ve izleme bölgesini seç.

Token cihazında saklanır (**Ayarlar → TMDb → Tokenı Değiştir**). İzlek için
ayrıca hesap gerekmez.

## Özellikler

| | İzlek ile |
| --- | --- |
| **Kütüphanen** | Film ve dizilerini İzlenecek / İzleniyor / İzlendi durumlarıyla düzenle; favori seç. |
| **Kaldığın bölüm** | Bölümleri işaretle, sezon ilerlemesini gör; Devam Et kartlarından sürdür. |
| **Keşfet ve ara** | Popüler içerikleri filtrele; film, dizi, oyuncu veya yönetmen ara (`Ctrl+K`). |
| **Oyuncu / yönetmen** | Yapımlara git; Yeni keşifler veya Tüm yapımları arasında geç. |
| **Detay ve sağlayıcılar** | Fragman, öneriler ve bölgesel izleme seçenekleri (gruplu). |
| **Özel + akıllı listeler** | Afişli çoklu ekleme, sürükleyerek sıra; akıllı listeler ve etiketler. |
| **Kişisel puan ve not** | 1–10 puan ve 2000 karaktere kadar not; etiket yönetimi. |
| **Filtre ve toplu işlem** | Tür/yıl/süre/durum/puan süz; kart seçip durum, favori veya liste uygula. |
| **Öneri tercihleri** | Bir daha önerme ile gizle; Ayarlar’dan geri aç. |
| **İstatistikler** | Toplam / film / bölüm süreleri, tür grafikleri, son izlemeler. |
| **Tema ve dil** | Koyu/açık tema; çok dilli arayüz. |
| **Çevrimdışı** | Kayıtlı kütüphane; afiş ve arka planlar yerelde korunabilir. |
| **Veri aktarımı** | JSON dışa/içe aktarma; Trakt / Letterboxd içe aktarma. |

Normal arama kayıtlı ve izlenmiş yapımları gizler; önerilerde İzlendi
gösterilmez. Ayrıntılar: [kullanım rehberi](docs/user-guide.md).

## Ekran görüntüleri

Görseller mevcut depo dosyalarından (**1366 × 768**); demo kütüphane ile
alınmıştır, gerçek kullanıcı verisi içermez. Tam boyutta açmak için tıkla.

<table>
  <tr>
    <td width="50%"><strong>Ana Sayfa · Keşfet</strong><br>Oyuncu/yönetmen araması ve yeni keşifler.<br><a href="docs/screenshots/actor-new-1366.png"><img src="docs/screenshots/actor-new-1366.png" alt="Keşfet oyuncu araması ve yeni keşifler" width="100%"></a></td>
    <td width="50%"><strong>Film kütüphanesi</strong><br>Özel sıra, durum ve kişisel puanlar.<br><a href="docs/screenshots/card-direct-1366.png"><img src="docs/screenshots/card-direct-1366.png" alt="Sürüklenebilir film kartları" width="100%"></a></td>
  </tr>
  <tr>
    <td width="50%"><strong>Özel listeler</strong><br>Afişli arama ve çoklu ekleme.<br><a href="docs/screenshots/multi-picker-1366.png"><img src="docs/screenshots/multi-picker-1366.png" alt="Listeye çoklu medya ekleme" width="100%"></a></td>
    <td width="50%"><strong>İstatistikler</strong><br>Süre kartları ve grafikler.<br><a href="docs/screenshots/design-statistics-1366.png"><img src="docs/screenshots/design-statistics-1366.png" alt="İstatistik paneli" width="100%"></a></td>
  </tr>
  <tr>
    <td width="50%"><strong>Puan ve not</strong><br>İşlem satırından açılan form.<br><a href="docs/screenshots/review-actions-movie-open-1366.png"><img src="docs/screenshots/review-actions-movie-open-1366.png" alt="Puan ve not formu" width="100%"></a></td>
    <td width="50%"><strong>Filtre ve toplu işlem</strong><br>Kütüphaneyi süz, kartları birlikte düzenle.<br><a href="docs/screenshots/personal-library-1366.png"><img src="docs/screenshots/personal-library-1366.png" alt="Kütüphane filtreleri" width="100%"></a></td>
  </tr>
</table>

> 1.1 arayüz yeniliklerinin (sağlayıcı grupları, dil seçici, açık tema, akıllı
> listeler) güncel ekran görüntüleri henüz depoda yok; yukarıdaki mevcut
> görseller korunmuştur.

## Verilerin nerede?

| Veri | Varsayılan konum |
| --- | --- |
| Kütüphane, listeler, ilerleme, puan/not, etiketler, sıralar | `~/.local/share/izlek/izlek.sqlite3` |
| Pencere / tema ayarları | `~/.config/izlek/window.ini` |
| Meta veri kaynağı ayarları | `~/.config/izlek/metadata-sources.json` |
| İndirilen görseller | `~/.cache/izlek/images` |
| Loglar | `~/.local/state/izlek/logs` |

`XDG_*` tanımlıysa ilgili dizinler kullanılır. Snap yolları
[Snap rehberinde](snap/README.md). Windows’ta ayarlar `%APPDATA%\izlek`,
veri `%LOCALAPPDATA%\izlek`; EXE kaldırma kişisel klasörleri silmez.

Token önce sistem anahtarlığında tutulur; yoksa `~/.config/izlek/tmdb-token`
dosyasına yalnız kullanıcıya açık izinlerle yazılır. Token veritabanına,
loglara ve JSON export’a girmez. Kişisel takip verisi bir İzlek sunucusuna
gönderilmez; arama/metadata istekleri seçili sağlayıcılara gider.

## Belgeler

- [Kullanım rehberi](docs/user-guide.md) · [Geliştirme](docs/development.md)
- [Mimari](docs/architecture.md) · [QML bileşenleri](docs/components.md)
- [Meta veri kaynakları](docs/METADATA_SOURCES.md)
- [Release süreci](docs/releases.md) · [CHANGELOG](CHANGELOG.md)

## Katkı

[Issue aç](https://github.com/Teknoloji-Filozoflari/Izlek/issues) ·
[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)

```bash
python scripts/quality.py
```

Ruff ve pytest; mock TMDB, gerçek token gerekmez.

## TMDB ve JustWatch

Film, dizi, kişi, puan ve görseller **TMDB** kaynaklıdır. İzleme sağlayıcısı
bilgisi TMDB’nin **JustWatch** ortaklığından gelir. Ek kaynaklar (Trakt,
TVmaze, OMDb) Ayarlar’dan açılır; kendi API anahtarların gerekebilir.

> This product uses the TMDB API but is not endorsed or certified by TMDB.

[TMDB / JustWatch uyumluluk notu](docs/TMDB_JUSTWATCH_COMPLIANCE.md)

## Lisans

İzlek, [GNU GPL v3 veya sonrası](LICENSE) altında yayımlanır.
Python paket adı `izlek`, GitHub depo adı `Izlek`tir.
