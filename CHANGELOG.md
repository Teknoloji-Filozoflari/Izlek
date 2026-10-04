# Değişiklik Günlüğü

Bu dosya [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) yaklaşımını
izler ve proje [Semantic Versioning](https://semver.org/) kullanır.

## [Unreleased]

### Fixed

- Sekme geçişlerindeki sayfa çakışması, gereksiz model/afiş yenilemeleri
  ve görsel hazırlığının arayüzü bekletmesi.
- Devam Et yalnız kütüphanedeki dizileri gösterir; bilinmeyen süreler
  istatistik toplamlarına katılmaz.
- Film/dizi detaylarında oyuncu fotoğrafları ve ekranı kullanan bilgi düzeni;
  benzer içerik bölümü kaldırıldı, yalnız öneriler kaldı.

- Keşfet filtre seçeneklerinin metin/hover bağları ve açılır menü açıkken
  Escape'in genel gezinme kısayolu yerine menüyü kapatması.
- Kütüphane kartları model/görünürlük değişimlerinde eksik posterlerini yeniden
  ister; görsel servisi anahtarlık/HTTP hazırlığını UI thread'i dışında yapar.
  Geçici ağ/CDN hatalarında görseller bir kez yeniden indirilir.
  Poster indirilirken "Poster yok" yerine yükleme görünümü gösterilir.
- Ana sayfa aramasından detaya girerken odak geri yüklemesinin modal pencereyi
  yeniden açıp karartma katmanıyla tıklamaları engellemesi. Arama alanı yalnız
  tıklama, Enter veya Space ile açılır; yalnız odak almak pencere açmaz.
- Eski JSON yedeklerinin güncel bölüm metadata'sını ezmesi; tutarsız export
  snapshot'ları, geçersiz metadata/kimliklerin önizlemeden geçmesi ve büyük
  dizi import'larında bölüm listesinin tekrar tekrar okunması.
- Veritabanı hatalarında açık kalan detay/sezon yükleme ve kaydetme durumu,
  film değiştirirken kilitli aksiyonlar ve yenilemede sıfırlanan sezon seçimi.
- Menüde kalan detay geçmişi, geri düğmesinin iş iptalini atlaması, kütüphane
  filtrelerinin yanlış gösterilmesi ve Keşfet'in 500 sayfa sınırı.
- Worker bitmeden kapatılan veritabanı kaynakları, eşzamanlı ilk kullanımda
  birden fazla engine oluşturulması ve token değişiminde görsel kaynak sızıntısı.
- Gerçek kullanıcı verisine erişebilen test/smoke ortamları, eşzamanlı cache
  silme/ölçüm yarışı, eksik sdist kaynakları ve Arch arşiv dizini adı.

### Added

- PyInstaller bundle üzerinden RPM üretimi, core24 strict Snap tanımı ve
  iki biçim için elle başlatılabilir GitHub Actions build/smoke workflow'ları.

- Listeye medya eklerken yerel kütüphanede arama, detaydan kütüphaneden
  kaldırma ve kütüphane görsellerini indirip yerelde koruma.

- Keşfet ve arama ilk açılan Ana Sayfa'da; ayrı İstatistikler menüsü altında
  toplam süre kartı, sayaçlar, son 12 ay bölüm grafiği, tür dağılımı ve en çok
  zaman ayrılan diziler. Devam Et Diziler sekmesindedir; İstatistikler yalnız istatistikleri gösterir.
- Yazısız yuvarlak bölüm tikleri, dizi detayında ve kütüphane kartlarında
  izlenen/toplam bölüm sayacı ile sarı ilerleme çubukları.
- Global aramada Film ve Dizi / Film / Dizi tür seçimi; tür değişiminde eski
  istek sonuçları yok sayılır ve yalnız seçili kategorinin sorgusu çalışır.
- Resmî TMDB SVG logosu ve kişisel verileri koruyan 180 günlük metadata/görsel
  temizliği; başarısız opsiyonel endpoint'ler kendi eski sync tarihini korur.
- Ayrıntılı kod denetimi ve regresyon doğrulamaları:
  [2026-10-04 denetim raporu](docs/AUDIT_2026_10_04.md).

## [1.0.0] - 2026-10-04

### Added

- Linux öncelikli PySide6/Qt Quick masaüstü arayüzü, koyu tema, klavye
  kısayolları ve responsive film/dizi görünümleri.
- Film ve dizi araması, ayrıntılar, öneriler, fragmanlar, TMDB Discover ve
  Türkiye için JustWatch kaynaklı izleme sağlayıcıları.
- Yerel takip durumları, favoriler, özel listeler, bölüm ilerlemesi, toplu
  sezon/dizi işlemleri ve Devam Et akışı.
- Yerel istatistikler ile sürümlü, doğrulanan İzlek JSON import/export desteği.
- Sistem anahtarlığı öncelikli TMDB token saklama ve güvenli dosya fallback'i.
- AppImage, Debian/Ubuntu ve Arch paket tanımları; desktop entry ve uygulama
  simgesi.
- Ruff/pytest kalite kapısı, mock TMDB testleri ve tag tabanlı GitHub Release
  workflow'u.
- Açık kaynak proje belgeleri, katkı/güvenlik politikaları ve issue/PR
  şablonları.

### Security

- Takip verisi, favoriler, listeler ve bölüm ilerlemesi yalnızca kullanıcının
  yerel SQLite veritabanında tutulur; hesap, analytics veya cloud backend yoktur.
- TMDB tokenı loglara, SQLite'a, export dosyalarına veya CI secret'larına
  yazılmaz.
- İndirilen görseller XDG cache altında tutulur ve 180 günlük retention
  uygulanır.

### Known issues

- Resmî onaylı TMDB logosunun About/Credits ekranına eklenmesi ve prominence
  doğrulaması tamamlanmamıştır.
- SQLite'taki uzak TMDB metadata/provider cache'i için kişisel veriyi koruyan
  180 günlük fiziksel retention henüz uygulanmamıştır.
- İlk binary yayın yalnızca x86_64 AppImage ve amd64 Debian/Ubuntu hedefler.

[1.0.0]: https://github.com/Teknoloji-Filozoflari/Izlek/releases/tag/v1.0.0
