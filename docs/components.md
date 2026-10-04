# QML Bileşenleri

QML bileşenleri `src/izlek/ui/qml/components/` altındadır. Her biri QML'de `import "components"` ile ayrı kullanılabilir. Renkler, boşluklar, yazı boyutları, süreler ve kart ölçüleri `theme/Theme.qml` içinden alınır. Galeriyi yerel örnek veriyle `python -m izlek --gallery` komutuyla açın; bu komut ana pencerenin kayıtlı boyutunu değiştirmez.

| Bileşen | Temel özellikler ve olay |
| --- | --- |
| `IzlekButton`, `IconButton` | `text`/`variant` veya `iconSource`/`toolTipText`; standart `clicked` |
| `SegmentedControl` | `options`, `currentIndex`; `selected(index)` |
| `StatusSelector` | `status`: boş, `PLANNED`, `WATCHING`, `WATCHED`; `statusSelected(status)` |
| `SearchField` | `text`, `placeholderText`; yerleşik temizleme butonu |
| `FilterComboBox`, `FilterTextField` | Koyu tema filtre girişleri; standart `ComboBox`/`TextField` API'leri; combo QtQuick Templates tabanlıdır, KDE'nin gizli menu/repeater davranışından bağımsızdır; sıfır başlangıç konumu ve sabit satır yüksekliği kullanır |
| `FilterSpinBox` | `value`, `from`, `to`, `stepSize`, `textFromValue`; oklar veya klavyeyle değişen puan, salt okunur etiket. Odak kaybında metin yeniden sayıya dönüştürülmez; `editable: false` |
| `GlobalSearch` | `controller`: `SearchController`; `open()`/`close()`, `resultActivated(kind, itemId)`; giriş için 300 ms debounce; Film ve Dizi / Film / Dizi seçimi `mediaType` ve `setMediaType(kind)` üzerinden yalnız ilgili endpoint'i sorgular |
| `SearchResultCard` | `media`: `{id, mediaType, title, year, poster}`; `activated(kind, itemId)` |
| `LibraryPosterGrid` | `items`: yerel film/dizi nesneleri (`tmdb_id`, `title`, `year`, `poster`, `status`, isteğe bağlı `progress` ve `progress_text`); `mediaActivated(tmdbId)`, `favoriteToggled(tmdbId, favorite)`; genişliğe göre sık poster sütunları |
| `ContinueWatchingCard` | `itemData`: dizi ve sıradaki bölüm verisi (`tmdb_id`, `title`, `poster`, `backdrop`, `episodeCode`, `episode_title`, `watched_count`, `aired_count`, `season_number`, `episode_number`); `busy`; `opened(tmdbId)`, `watched(tmdbId, seasonNumber, episodeNumber)` |
| `PosterCard` | `posterSource`, `posterLoading` (indirme sürerken skeleton), `mediaTitle`, `year`, `status`, isteğe bağlı `progress` (0–1) ve `progressText`; `favorite`, `favoriteEnabled`; `activated()`, `favoriteToggled(bool)` |
| `EpisodeCheck` | `episodeName`, standart `checked`/`clicked`; yazısız yuvarlak tik, klavye odağı, erişilebilir ad ve tooltip |
| `EpisodeProgressBar` | `watched`, `total`, salt okunur `fraction`; bölüm sayacı ve sarı ilerleme çubuğu |
| `StatisticsPanel` | `stats`: yerel istatistik snapshot'ı; toplam süre, sayaçlar, tür halkası ve posterli ilk beş dizi |
| `MediaGrid`, `HorizontalMediaStrip` | `items` medya nesneleri dizisi; `mediaActivated(media)` |
| `SectionHeader` | `title`, `subtitle`, `actionText`; `actionTriggered()` |
| `CastGrid` | `cast`: `{name, character, profilePath, poster}` dizisi; `photoObjectName`: görsel test adı. Fotoğraflı ad/rol kartları genişliğe göre satır kaydırır; eksik görselde yer tutucu gösterir. |
| `Badge`, `FavoriteButton` | `text`/`tone` veya `checked`; `toggledFavorite(bool)` |
| `StatCard` | `label`, `value`, `detail` |
| `EmptyState`, `ErrorState` | `title`, `description`, `actionText`; `actionRequested()` |
| `ProviderSection` | `groups`, `providerLink`; Türkiye abonelik/kiralama/satın alma görünümü, JustWatch attribution ve TMDb izleme bağlantısı |
| `Skeleton`, `LoadingState` | Yükleme yer tutucuları; `LoadingState.count` ve `skeletonPosterHeight` |
| `IzlekDialog` | `title`, `message`, isteğe bağlı `bodyComponent`; `confirmed()` |
| `Toast` | `show(message, tone)`; `tone`: `neutral`, `success`, `danger` |

Grid ve yatay şerit şu veri biçimini kullanır: `{id, title, year, poster, status, progress, progressText}`. Son üç alan isteğe bağlıdır; `poster` boşsa kart yer tutucu gösterir. İki liste de aynı `MediaCardDelegate` bağlamasını kullanır. `MediaGrid`, görünür genişliğe göre sütun sayısını hesaplar ve `GridView` sayesinde yalnızca görünür kartları oluşturur.

`MediaGrid.quickLibraryController` isteğe bağlıdır; ana sayfada verilince
her kartın altında sarı çerçeveli `+ Kütüphaneye Ekle` düğmesi gösterir ve
satır yüksekliğini genişletir. `MediaCardDelegate` bu controller'ın
`states[mediaType + ':' + id]` değerini okur: `adding` yükleme, `added`
devre dışı `✓ Kütüphanede` durumudur. Düğme kartı/detayı açmaz;
`add(media)` yalnız yerel worker işlemini başlatır. Diğer grid/şeritler değişmez.

```qml
MediaGrid {
    anchors.fill: parent
    items: [{ id: 1, title: "Örnek", year: "2026", poster: "", status: "PLANNED" }]
    onMediaActivated: function(media) { console.log(media.title) }
}
```

Kartlar ve butonlar Tab ile odaklanır; odak halkası görünürdür. Poster kartı fare, Enter ve Space ile etkinleşir. `GlobalSearch` ve `IzlekDialog` modal odak sırasını içeride tutar, yalnızca Esc ile kapanır ve açıldığında ilk uygun denetime odaklanır. Poster yüklenirken kart ölçüsü sabit kalır ve skeleton gösterilir. QML bileşenleri kendi başına ağ veya veritabanı isteği yapmaz.

Kütüphane poster kartındaki `FavoriteButton` odaklanabilir; kalp aksiyonu kartı açmaz. Favori durumu controller tarafından SQLite verisinden beslenir.

`LibraryPosterGrid.controller` isteğe bağlıdır; `posterAvailable(tmdbId, url)`
bildirimi ilgili kartın afişini model/delege yeniden oluşturmadan günceller.
`ContinueWatchingCard.controller` da isteğe bağlıdır;
`imageAvailable(tmdbId, role, url)` afiş ve arka planı günceller.
`posterSource` / `backdropSource` bu kartın yerel görsel kaynaklarıdır.
Bu güncellemeler kartın klavye odağını ve yerleşimini korur.
