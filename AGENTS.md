# Repository Guidelines

## Proje Yapısı ve Mimari

İzlek, Linux öncelikli, açık kaynak, local-first bir Python masaüstü uygulamasıdır; web sunucusu, Docker, hesap veya cloud backend eklemeyin. Kod `src/izlek/` altında; `core/`, `db/`, `repositories/`, `services/`, `tmdb/`, `security/`, `cache/`, `ui/` ve `resources/` alanlarında düzenlenmelidir. QML dosyalarını `ui/qml/`, testleri `tests/` altında tutun. Akış `QML → Controller/ViewModel → Service → Repository/TMDb Client → SQLite/TMDb` olmalıdır. QML içinde SQL, HTTP veya iş mantığı yazmayın. Basit constructor injection kullanın; dependency injection framework eklemeyin.

## Faz Kapsamı ve Model Değişiminde Devamlılık

Model veya oturum değişmesi yeni bir proje başlangıcı değildir. Her yeni fazdan önce `docs/HANDOFF.md`, `docs/architecture.md`, ilgili mevcut kod ve testleri okuyun; tamamlanmış fazları çalışan temel olarak kabul edin. Kullanıcının son faz promptu yalnızca o fazın kapsamını belirler.

Mevcut Python/PySide6/QML, SQLite, merkezi TMDb client, katman akışı, constructor injection, tema tokenları ve ortak bileşenleri koruyun. Önce mevcut servis, repository ve bileşenleri kullanın veya fazın gerektirdiği kadar genişletin. Yeni faz için zorunlu olmadıkça tamamlanmış sayfaları yeniden tasarlamayın, katmanları taşımayın, public API'leri değiştirmeyin, bağımlılık veya alternatif altyapı eklemeyin. Genel refactor, mimari yenileme ve önceki fazların tekrar uygulanması ayrıca kullanıcı tarafından istenmelidir.

Önceki faza dokunmak yeni fazı tamamlamak için zorunluysa değişikliği en küçük kapsamda tutun, gerekçesini açıklayın ve mevcut davranışların korunduğunu ilgili testlerle doğrulayın. Kapsam dışı bulguları raporlayın; yeni faz bahanesiyle toplu düzeltme yapmayın. Önceden mevcut bir mimari sapmayı yeni kod için örnek kabul etmeyin.

Faz sonunda devir notunu tamamlanan değişiklikler, doğrulamalar ve bilinen sapmalarla güncelleyin. Sonraki modelin devam edebilmesi için eski faz geçmişini koruyun; yalnızca yeni fazın gerektirdiği değişiklikleri uygulayın.

## Kurulum, Çalıştırma ve Kontrol

Bağımlılıkları `pyproject.toml` ile yönetin. Standart sanal ortam kullanın: `python -m venv .venv`, ardından `source .venv/bin/activate` ve `python -m pip install -e '.[dev]'`. Qt Quick penceresini `python -m izlek` ile doğrulayın; mevcut medya sayfaları ve tamamlanmış işlevler için `docs/HANDOFF.md` dosyasını esas alın. Her faz sonunda `python -m pytest` ve `ruff check .` çalıştırın. Komutları ve ön koşulları `README.md` ile uyumlu tutun.

Tekrar kullanılabilir QML öğelerini `ui/qml/components/` altında tutun ve `python -m izlek --gallery` ile 1366×768 ve 1920×1080 düzenlerini kontrol edin. Bileşenlerde renkleri sabit yazmayın; `ui/qml/theme/Theme.qml` tokenlarını kullanın. Bileşen API'lerini `docs/components.md` içinde güncel tutun.

Gerçek Wayland/X11 oturumu varsa `scripts/smoke_display.py --platform wayland` ve `--platform xcb` ile açılış, gezinme ve yeniden boyutlandırmayı doğrulayın.

## Kodlama ve Test Kuralları

Python kodunda dört boşluk girinti, type hint ve anlamlı `snake_case` adları kullanın; sınıfları `PascalCase` adlandırın. Public API ve karmaşık kararları kısa docstring ile açıklayın. Test dosyalarını `test_*.py` biçiminde adlandırın. `pytest` ile servis, repository, import/export ve hata davranışlarını; `pytest-qt` ile gerekli UI etkileşimlerini sınayın. QML odağını ve klavye gezintisini manuel olarak da kontrol edin. Gereksiz soyutlama ve henüz istenmemiş özellik eklemeyin.

## Ürün ve Veri Sınırları

Yalnızca `MOVIE` ve `TV`; yalnızca `PLANNED`, `WATCHING`, `WATCHED` durumları vardır. Favoriler durumdan bağımsızdır. Bölüm ilerlemesi ve diğer kişisel veriler yalnızca SQLite'ta tutulur; metadata yenilemesi bunları değiştiremez. TMDb tek çevrimiçi metadata kaynağıdır. Ağ ve ağır disk işleri UI thread dışında yürütülmeli; offline kütüphane çalışmalıdır. Token önce sistem keyring'inde saklanmalı, loglara veya export'a girmemelidir. Arayüz Türkçe, içerik başlıkları orijinal dilinde ve ilk sürüm yalnızca koyu temalıdır; QML tasarım tokenlarını merkezileştirin.

## Katkı, Lisans ve Faz Teslimi

Git geçmişi henüz yoktur; commit başlıklarını kısa ve emir kipinde yazın. PR açıklamasına amaç, test sonucu, ilgili issue ve görünür UI değişikliğinde ekran görüntüsü ekleyin. Lisans `GPL-3.0-or-later`dır. Faz sonunda **Yapılanlar**, **Değiştirilen önemli dosyalar**, **Test sonucu**, **Manuel kontrol**, **Bilinen sorunlar** ve **Sonraki faz** başlıklarıyla rapor verin. Sonraki fazın yalnızca adını belirtin; kullanıcı yeni prompt verene kadar onu uygulamayın.
