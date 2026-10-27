# QML Bileşenleri

QML bileşenleri `src/izlek/ui/qml/components/` altındadır. Her biri QML'de `import "components"` ile ayrı kullanılabilir. Renkler, boşluklar, yazı boyutları, süreler ve kart ölçüleri `theme/Theme.qml` içinden alınır; `mode` (`dark` / `light`) Ayarlar'daki görünüm tercihine bağlanır. Galeriyi yerel örnek veriyle `python -m izlek --gallery` komutuyla açın; bu komut ana pencerenin kayıtlı boyutunu değiştirmez.

| Bileşen | Temel özellikler ve olay |
| --- | --- |
| `IzlekButton`, `IconButton` | `text`/`variant` veya `iconSource`/`toolTipText`; standart `clicked` |
| `SegmentedControl` | `options`, `currentIndex`; `selected(index)` |
| `StatusSelector` | `status`: boş, `PLANNED`, `WATCHING`, `WATCHED`; `statusSelected(status)` |
| `SearchField` | `text`, `placeholderText`; yerleşik temizleme butonu |
| `FilterComboBox`, `FilterTextField` | Koyu tema filtre girişleri; standart `ComboBox`/`TextField` API'leri; combo QtQuick Templates tabanlıdır, KDE'nin gizli menu/repeater davranışından bağımsızdır; sıfır başlangıç konumu ve sabit satır yüksekliği kullanır. Kütüphane **Sırala** da bunu kullanır (boş Controls popup yerine). |
| `FilterSpinBox` | `value`, `from`, `to`, `stepSize`, `textFromValue`; oklar veya klavyeyle değişen puan, salt okunur etiket. Odak kaybında metin yeniden sayıya dönüştürülmez; `editable: false` |
| `GlobalSearch` | `controller`: `SearchController`; `open()`/`close()`, `resultActivated(kind, itemId)`; giriş için 300 ms debounce; Film ve Dizi / Film / Dizi seçimi `mediaType` ve `setMediaType(kind)` üzerinden yalnız ilgili endpoint'i sorgular |
| `SearchResultCard` | `media`: `{id, mediaType, title, year, poster}`; `activated(kind, itemId)` |
| `LibraryPosterGrid` | `items`: yerel film/dizi nesneleri (`tmdb_id`, `title`, `year`, `poster`, `status`, isteğe bağlı `score`, `progress` ve `progress_text`); `compact` (varsayılan `false`, sabit rahat sunum); `mediaActivated(tmdbId)`, `favoriteToggled(tmdbId, favorite)` |
| `ContinueWatchingCard` | Yatay şerit kartı: `itemData` dizi ve sıradaki bölüm verisi (`tmdb_id`, `title`, `poster`, `backdrop`, `episodeCode`, `episode_title`, `watched_count`, `aired_count`, `season_number`, `episode_number`); `busy`; bölüm rozeti (`S2B4`), alt ilerleme çubuğu; `opened(tmdbId)`, `watched(tmdbId, seasonNumber, episodeNumber)` |
| `PosterCard` | `posterSource`, `posterLoading` (indirme sürerken skeleton), `mediaTitle`, `year`, `score` (negatifse gizli), `status`, isteğe bağlı `progress` (0–1) ve `progressText`; `favorite`, `favoriteEnabled`; `footerHeight` alt eylem alanı; `activated()`, `favoriteToggled(bool)` |
| `EpisodeCheck` | `episodeName`, standart `checked`/`clicked`; yazısız yuvarlak tik, klavye odağı, erişilebilir ad ve tooltip |
| `EpisodeProgressBar` | `watched`, `total`, salt okunur `fraction`; bölüm sayacı ve sarı ilerleme çubuğu |
| `StatisticsPanel` | `stats`: yerel istatistik snapshot'ı; toplam/film/bölüm süre kartları, sayaçlar (yeniden izleme dahil), son 12 ay aktivite çubukları, adet/yüzde etiketli tür halkası, bölüm/süre etiketli ilk beş dizi ve son izlemeler günlüğü. 900 piksel altında süre kartları ve grafikler tek sütuna geçer. |
| `MediaGrid`, `HorizontalMediaStrip` | `items` medya nesneleri dizisi; `mediaActivated(media)`. `MediaGrid.compact` varsayılan `false`; sık görünüm kart genişliğini ve grid satır yüksekliğini birlikte değiştirir. |
| `SectionHeader` | `title`, `subtitle`, `actionText`; `actionTriggered()` |
| `CastGrid` | `cast`: `{id, name, character, profilePath, poster}` dizisi; `actorActivated(personId, name)`; `photoObjectName`: görsel test adı. Fotoğraflı ad/rol kartları fare ve klavye ile etkinleştirilir; kimliği olmayan eski kayıtlar tıklanamaz. |
| `Badge`, `FavoriteButton` | `text`/`tone` veya `checked`; `toggledFavorite(bool)` |
| `StatCard` | `label`, `value`, `detail`, `accented` (vurgu kenarlık/değer); dar alanda metinler kısaltılır, tam metin erişilebilir adda korunur |
| `EmptyState`, `ErrorState` | `title`, `description`, `actionText`; `actionRequested()` |
| `ProviderSection` | `groups`, `providerLink`; Türkiye abonelik/kiralama/satın alma görünümü, JustWatch attribution ve TMDb izleme bağlantısı |
| `Skeleton`, `LoadingState` | Yükleme yer tutucuları; `LoadingState.count` ve `skeletonPosterHeight` |
| `IzlekDialog` | `title`, `message`, isteğe bağlı `bodyComponent`; `confirmed()` |
| `MediaPickerDialog` | `controller`: `CustomListsController`, `listId`, `selections`, salt okunur `selectionCount`; afişli yerel arama ve medya türü/kimliğiyle çoklu seçim; başarılı `batchAdded(listId)` sonrasında kapanır |
| `PersonalReview` | `kind`, `mediaId`, `mediaTitle`, `backend`: PersonalMediaController; `expanded` varsayılan false, form görünürlüğünü yönetir. Film/dizi sayfasının işlem satırındaki Puan ve not düğmesi bu değeri değiştirir. 1–10 puan, 2000 karakter not, kaydet/temizle ve öneri gizleme; `filterPopupOpen`. Kapatıp açmak taslağı korur; başarılı kayıt `reviewSaved` ile eşitler; hata/gizleme taslağı silmez. Yeni detay kapalı başlar. |
| `LibraryFiltersPanel` | `controller`, `kind`; durum/tür/yıl aralığı/süre/puan filtreleri, `applied()`, `filterPopupOpen`; `filterValues` başlangıç değerleri ve `genres` seçeneklerini kullanır. |
| `LibraryBulkDialog` | `controller`, `selectedIds`; durum için ikinci onay, favori ve liste eylemleri; yalnız `bulkCompleted` sonrası kapanır; işlem sırasında düğmeler kapalıdır. |
| `ReorderHandle` | `label`, `showHandle` (varsayılan true), isteğe bağlı `previewSource`; salt okunur `dragging`, `scenePosition`; `moved(point)`, `dropped(point)`, `pressStarted()`, `tapped()`. showHandle=false aynı işleyiciyi görünmez kart alanına dönüştürür; sürüklenmiş basış tapped üretmez. |
| `ReorderAutoScroll` | `view`: GridView/ListView, `active`, `scenePosition`; kenara yakın sürüklemede görünümü içerik sınırları içinde kaydırır |
| `Toast` | `show(message, tone)`; `tone`: `neutral`, `success`, `danger` |

Grid ve yatay şerit şu veri biçimini kullanır: `{id, title, year, poster, score, status, progress, progressText}`. Puan/durum/ilerleme alanları isteğe bağlıdır; `poster` boşsa kart yer tutucu gösterir. İki liste de aynı `MediaCardDelegate` bağlamasını kullanır. `MediaGrid`, görünür genişliğe göre sütun sayısını hesaplar ve `GridView` sayesinde yalnızca görünür kartları oluşturur.

`MediaGrid.quickLibraryController` isteğe bağlıdır; ana sayfada verilince
her kartın içinde ayrılmış alt alanda vurgu renkli çerçeveli
`+ Kütüphaneye Ekle` düğmesi gösterir ve satır yüksekliğini genişletir.
`MediaCardDelegate` bu controller'ın
`states[mediaType + ':' + id]` değerini okur: `adding` yükleme, `added`
devre dışı `✓ Kütüphanede` durumudur. Düğme kartı/detayı açmaz;
`add(media)` yalnız yerel worker işlemini başlatır. Diğer grid/şeritler değişmez.

Kartların başlık alanı tek veya iki satırlı başlıkta aynı yüksekliği korur;
yıl ve ilerleme metni aynı satıra hizalanır. TMDb puanı afişin sol üstünde,
durum sol altında ve favori düğmesi sağ üstünde gösterilir. Uzun başlığın
tamamı tooltip ve erişilebilir adda bulunur. `Theme.cardWidth` (164),
`cardCompactWidth` (142), `cardTitleHeight` (40) ve `cardInfoHeight` (90)
ölçüleri Keşfet ve kütüphane tarafından paylaşılır. Kart sunumu sabit rahat
(`compact: false`) düzendir; filtre, sıralama ve kişisel veri yazmaz.

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

`PosterCard.reorderEnabled` ve `reorderView` isteğe bağlı tam kart sürüklemesini
açar; `reorderDragging` aktif sürüklemeyi, `reorderDropped(scenePosition)`
bırakmayı bildirir. `LibraryPosterGrid`
bunu `reorderRequested(sourceId, targetId)` olayına dönüştürür. Controller
yazarken sürükleme devre dışıdır; karta tıklama ve favori işlemi
korunur. Kartın içerik öğesi görünmez sürükleme alanının üzerindedir; favori
ve seçim düğmeleri önce olayı alır. Kısa basış Button.clicked, sürüklenmiş
basış yalnız dropped üretir. Platform sürükleme eşiği kullanılır; kaynak kart
soluklaşır, afiş önizlemesi Overlay üzerinde gösterilir. Liste sayfası aynı
bileşeni görünür tutamaçla kullanmayı sürdürür.
Medya seçicisinde `Components.SearchField` açık yerel import'u kullanılır;
böylece Qt Controls'ün aynı adlı sistem kontrolü koyu tema yerine seçilmez.

`DiscoverPage` aramasındaki İçerik/Yönetmen/Oyuncu seçimi sayfanın `searchMode`
değerini (`title/director/actor`) değiştirir. `SearchController.people` kişi
adaylarını, `selectedPerson` seçilen kişinin id/adını verir;
`searchPeople(query, role)` ve `selectPerson(personId, kind, role)` arka plan
işlerini başlatır. Önceki `directors/selectedDirector/searchDirectors/selectDirector`
API'si uyumluluk için korunur. `openActor(personId, name, kind)` tam kimliği
ad araması yapmadan açar. Yapımlar
mevcut `movies`/`shows` ve `MediaGrid` üzerinden sunulur. Yeni sorgu veya mod
değişimi önceki generation'ı geçersiz kılar. Bu seçim global aramaya yeni
bir kişi modu eklemez; global arama mevcut içerik aramasını kullanır.

`includeSaved`/`setIncludeSaved(bool)` yalnız seçili kişinin tam yapım
snapshot'ından Yeni keşifler/Tüm yapımları görünümünü üretir. Yeni kişide
varsayılan false, aynı kişide kategori geçişinde korunur. Kişisel bilgiler
worker'da okunur; kart `status` alanına iletilir. `SAVED` yalnız sunum
etiketidir (Kayıtlı); SQLite takip durumuna yeni enum değeri eklenmez.
Detay sayfaları `actorSelected(id, name)` sinyalini Main'e iletir; Main Keşfet'i
açıp `DiscoverPage.showActor(id, name, kind)` çağırır.

`PosterCard.personalRating` 0'dan büyükse TMDb rozetinden ayrı Ben: N/10
rozeti gösterir. `selectionEnabled`, `selected`, `selectionToggled()` kartın
seçim kutusunu denetler. `LibraryPosterGrid.selectionMode/selectedIds`
seçim sırasında kart açmak yerine `selectionToggled(tmdbId)` bildirir;
yenilemede görünümden çıkan kimlikler seçimden çıkarılır. Filtre/çoklu seçim
sırasında kart sürüklemesi devre dışıdır. `MediaGrid.dismissController` isteğe
bağlıdır; verilirse kartın ⊘ düğmesi `setDismissed(media, true)` çağırır.
Keşfet bunu yalnız normal önerilerde verir; global arama/galeri etkilenmez.
