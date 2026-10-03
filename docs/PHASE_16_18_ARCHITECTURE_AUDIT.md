# Faz 16–18 mimari kontrolü

Kontrol tarihi: 2026-10-03. Kapsam: mevcut kaynak kodun `AGENTS.md` ve `docs/architecture.md` ile karşılaştırılması. Repository'de Git geçmişi bulunmadığı için tarihsel diff çıkarılamadı; sonuçlar mevcut kod ve testlere dayanır.

## Sonuç

Ana teknoloji ve veri mimarisi korunmuştur: Python/PySide6/Qt Quick masaüstü uygulaması, SQLAlchemy/SQLite kişisel veri deposu, merkezi TMDb client, işçi havuzlarında ağ/veritabanı işlemleri ve merkezi QML tema tokenları kullanılmaktadır. İncelenen sayfalarda SQL veya HTTP yoktur. Web sunucusu, cloud backend, hesap sistemi, Docker ya da alternatif UI framework bulunmamıştır. Takip, favori, liste ve bölüm ilerlemesi akışları mevcut servisler üzerinden sürmektedir.

| Faz | Mevcut uygulama | Mimari değerlendirme |
| --- | --- | --- |
| 16 | `HomePage.qml`, Devam Et, favoriler ve film/dizi kütüphane controller'larını birleştirir. Yerel seçim kuralları servis/repository katmanında, responsive yerleşim ve özetler QML'dedir. | Mevcut katmanlar ve ortak bileşenler kullanılmıştır. Dashboard düzeni bu fazın istenen kapsamıdır. |
| 17 | `DiscoverPage.qml`, `DiscoverController`, merkezi `TmdbClient.discover_movie/discover_tv` ve `ImageService` kullanır. Ağ çağrıları işçi havuzundadır; eski yanıtlar generation kontrolüyle elenir. | Genel yapı korunmuştur; ancak controller filtre doğrulama ve minimum oy kuralını taşır, TMDb client'ı ayrı bir Discover servisi olmadan çağırır. Yazılı `Controller → Service → Client` akışına tam uymaz. Eski `SearchController` da doğrudan client kullanır; bu benzerlik sapmayı ortadan kaldırmaz. |
| 18 | Ortak `ProviderSection.qml` ve `services/provider_presentation.py`, mevcut film/dizi detail servislerine bağlanır. TR provider metadata'sı `media_item.metadata_json` üzerinden sunulur. | Mevcut detail ve metadata cache yapısı genişletilmiştir. Provider verisi takip durumuna veya bölüm ilerlemesine yazılmaz. Şema veya yeni depolama altyapısı eklenmemiştir. |

## Sınırlar ve bulgular

- Faz 17'nin tür/ülke seçenekleri `DiscoverPage.qml` içinde sabit listelerdir. QML ağ çağrısı yapmıyor, ancak metadata seçeneklerinin UI dosyasında tutulması bakım açısından sınırlamadır.
- Faz 16 QML'de servislerin verdiği istatistikler toplanır ve boş dashboard görünürlüğü belirlenir. Bunlar sunum hesaplarıdır; takip veya veritabanı kuralları QML'ye taşınmamıştır.
- Faz 18'de sağlayıcı adları kullanılır; logolar isteğe bağlı olduğu için bu bir mimari sapma değildir.
- Mimari dokümanı ve repository talimatlarındaki eski placeholder ifadeleri mevcut tamamlanmış sayfaları yansıtmıyordu; bu kontrol sırasında güncellendi.

Bu denetimde uygulama kodu yeniden tasarlanmamıştır. Discover servis katmanı sapması kayıt altına alınmıştır; ayrıca istenen bir düzeltme kapsamında ele alınabilir. Model/oturum değişiminde mevcut mimariyi ve tamamlanmış fazları koruma talimatları `AGENTS.md` içine eklenmiştir.

## Doğrulama

Denetim sonunda `.venv/bin/python -m pytest -q`: **88 geçti**. `.venv/bin/ruff check .`: **başarılı**. Testlerde sistem GI/GLib bağımlılığından bir deprecation uyarısı var. Bu kontrol kaynak kod incelemesi ve otomatik testlerle sınırlıdır; yeni manuel ekran testi yapılmadı.
