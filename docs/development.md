# Geliştirme ve doğrulama

[README’ye dön](../README.md)

Python 3.11 veya daha yeni bir sürüm, `pip` ve PySide6'nın Linux sistem gereksinimleri gerekir:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m izlek
python -m izlek --gallery
python scripts/quality.py
python -m pip wheel . --no-deps --wheel-dir dist
```

`python scripts/quality.py`, önce `ruff check .`, ardından tüm `pytest` testlerini
offscreen Qt ayarlarıyla çalıştıran tek kalite kapısıdır. Test paketi gerçek ağ
bağlantılarını engeller; TMDb yanıtları `httpx.MockTransport` ile sağlandığı için
CI ortamında gerçek token gerekmez. Tek tek çalıştırmak için `python -m pytest`
ve `ruff check .` komutları da kullanılabilir.

`python -m izlek` masaüstü penceresini açar. İlk açılan **Ana Sayfa**, Keşfet filtreleri ve Film/Dizi seçilebilen global aramayı içerir. **İstatistikler** (Ctrl+5) altında toplam ekran süresi, izleme sayaçları, son 12 ay bölüm grafiği, tür halkası ve en çok zaman ayrılan diziler toplanır. Aylık grafik yalnız gerçek izleme tarihi ve süresi kayıtlı bölümleri kullanır; film izleme tarihi tutulmadığı için filmler grafiğe dahil edilmez. Toplam süre yalnız süresi bilinen film ve bölümlerden hesaplanır; süresi bilinmeyen içerikler süre toplamına katılmaz ve kaç içerik dışarıda kaldığı gösterilir. **Devam Et** Diziler sekmesindedir; İstatistikler sayfası yalnız istatistikleri gösterir.

Filmler ve Diziler yerel kütüphaneleri, Listeler özel listeleri gösterir. Dizi kartı ve detay ekranında bölüm sayacı ile ilerleme çubuğu bulunur; özel sezonlar ana ilerleme çubuğuna katılmaz. Bölüm satırlarındaki yazısız yuvarlak tik fare veya Space ile değiştirilir. `--gallery`, [bileşen kütüphanesini](components.md) çevrimdışı örnek veriyle gösterir. Pencere boyutu ve büyütülmüş durumu XDG config dizininde saklanır; diğer XDG yolları [mimari belgesinde](architecture.md) açıklanır. Ekransız CI için `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python -m pytest` kullanın.

İlk açılışta Alembic migration'ları otomatik uygulanır. Kişisel veritabanı `$XDG_DATA_HOME/izlek/izlek.sqlite3` konumundadır; değişken tanımlı değilse `~/.local/share/izlek/izlek.sqlite3` kullanılır. Komut satırından migration çalıştırmak için kurulu sanal ortamda `python -m alembic -c alembic.ini upgrade head` kullanın. SQLite dosyasını yedeklemeden elle değiştirmeyin.

`No module named izlek` hatasında proje kökünde `.venv/bin/python -m izlek` çalıştırın; paket sanal ortama kurulmamışsa yukarıdaki `pip install -e '.[dev]'` adımını uygulayın. `No module named PySide6` hatasında da bağımlılık kurulumu eksiktir. İnternet erişimi yoksa ve PySide6 dağıtımınızda kuruluysa sanal ortamı `python -m venv --system-site-packages .venv` ile oluşturup `./.venv/bin/python -m pip install --no-deps --no-build-isolation -e .` çalıştırabilirsiniz.

Wayland veya X11 oturumunda gerçek pencere açılışını ve sidebar gezinmesini sınamak için normal masaüstü terminalinde şu komutları çalıştırın:

```bash
./.venv/bin/python scripts/smoke_display.py --platform wayland
./.venv/bin/python scripts/smoke_display.py --platform xcb
```

Test, kullanılan Qt platformunu ve QML uyarı sayısını yazar; isteğe bağlı `--gallery`, `--onboarding` ve `--screenshot /tmp/izlek.png` seçenekleri vardır. Normal gezinme denemesi örnek token durumu kullanır; `--onboarding` ilk açılış ekranını sınar. Ekransız doğrulama için `--platform offscreen` kullanılabilir.

Wayland ve X11 oturumlarında `App info not found for 'izlek'` portal uyarısı görünürse geliştirme başlatıcısını kullanıcı hesabınıza kurun:

```bash
./.venv/bin/python scripts/install_desktop_entry.py
```

Bu komut `$XDG_DATA_HOME` (varsayılan `~/.local/share`) altına `applications/izlek.desktop` ile `icons/hicolor/scalable/apps/izlek.svg` yazar. Masaüstü menüsünden **İzlek** başlatılabilir. Var olan, bu geliştirme betiğinin oluşturmadığı bir `izlek.desktop` dosyasını değiştirmez. Kurulumdan sonra Wayland ve X11 testlerini yeniden çalıştırın; test artık QML ve diğer Qt uyarılarını ayrı raporlar.

## TMDb API istemcisi

`izlek.tmdb.client.TmdbClient(token=...)` arayüzden bağımsız olarak configuration, film/dizi araması, film/dizi detayı ve dizi sezonu uç noktalarını çağırır. Yanıtlar `izlek.tmdb.models` içindeki Pydantic modellerine çevrilir. İstemciyi ağ çağrıları için UI thread'i dışında kullanın. Timeout, HTTP ve bozuk yanıt hataları `izlek.tmdb.client` içindeki güvenli domain exceptionlarına dönüşür. Bir 429 yanıtında en fazla bir kez, en çok iki saniyelik beklemeyle tekrar denenir. Testler gerçek TMDb'ye bağlanmaz; `httpx.MockTransport` kullanır.

## Görsel servisi ve cache

`ImageService(TmdbClient(token=...))`, `poster(path, "grid")`, `poster(path, "detail")` ve `backdrop(path)` çağrıları için yerel dosya yoluyla sonuçlanan `Future[Path]` döndürür. Ağ çağrıları servis işçi havuzunda yapılır; UI bu sonucu hazır olduğunda kullanmalıdır. Görsel boyutları TMDb configuration yanıtından seçilir ve `original` indirilmez. Geçerli görseller `$XDG_CACHE_HOME/izlek/images` altında hash anahtarlı dosyalarda tutulur. Cache okunamaz veya ağ kullanılamazsa servis poster/backdrop placeholder SVG yollarını döndürür. `cache_size_async()` ileride Ayarlar'da kullanılabilecek byte cinsinden cache boyutunu verir. Bu dizin yalnızca yeniden indirilebilir görseller içindir; kişisel takip verisi SQLite veri dizininde kalır.
