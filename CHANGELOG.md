# Değişiklik Günlüğü

Bu dosya [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) yaklaşımını
izler ve proje [Semantic Versioning](https://semver.org/) kullanır.

## [Unreleased]

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
