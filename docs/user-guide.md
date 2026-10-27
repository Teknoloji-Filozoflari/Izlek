# Kullanım rehberi

[README’ye dön](../README.md)

## Global arama

Ana penceredeki her sayfadan **Ctrl+K** ile arama açılır, **Esc** ile kapanır. En az üç karakter girildiğinde 300 ms bekledikten sonra TMDb film ve dizi aramaları arka planda paralel çalışır. Sonuçlar ayrı başlıklarda orijinal ad, yıl, tür ve cache'lenmiş posterle gösterilir. Sonuca tıklamak medya detay sayfasını açar. Çevrimdışıyken açıklayıcı hata gösterilir.

## Keşfet

**Keşfet**, TMDb'nin yalnızca Discover Movie ve Discover TV uçlarını kullanır. Film veya dizi, yıl, tür, ülke ve puan aralığı seçilebilir. Sonuçlar popülerliğe (`popularity.desc`) göre sıralanır; en az oy eşiği 100'dür. Puan aralığı ve ülke filtreleri korunur. Kartlar Rahat/Sıkı görünümle gösterilir ve önceki/sonraki düğmeleriyle sayfalanır.

Ana sayfadaki aramada ve global aramada kütüphanene kaydettiğin, favoriye
aldığın, özel listene eklediğin veya izlediğin içerikler gizlenir. Yalnızca
detayını açmış olman kaydetmek sayılmaz. Film ve dizi kimlikleri ayrıdır.
Arama sonucundan yeni içerik kaydettiğinde sonuç hemen gizlenir; sorgu korunur.

Film ve dizi detaylarının altındaki önerilerde **İzlendi** durumundaki
içerikler gösterilmez. İzlenecek veya izlenmekte olan öneriler gösterilebilir.
Önerilen içeriği açtıktan sonra **Geri** veya **Esc** bir önceki içeriğe döner;
öneri zincirinin başına gelince arama/kütüphane sayfasına dönülür.

Keşfet aramasında **Yönetmen** veya **Oyuncu** seçeneğine geçip en az üç karakterlik bir ad
yazabilirsin (ör. Christopher Nolan). Eşleşen kişilerden birini seçince
yönettiği veya oynadığı yapımlar afişli kartlarla, en yeniden eskiye gösterilir.
Soldaki **Film / Dizi** seçimi aynı kişinin ilgili yapımlarını getirir.
**Değiştir** kişi seçimine döner; **İçerik** normal ad aramasına döner.
Kişi seçildiğinde varsayılan **Yeni keşifler** görünümü kaydettiğin ve izlediğin
yapımları gizler. **Tüm yapımları** seçince bunlar da görünür; kartlarda
**İzlendi**, **İzleniyor**, **İzlenecek** rozetleri yer alır. Yalnız favori veya
özel liste kaydı olanlarda **Kayıtlı** yazısı görünür. Görünüm değişimi yeniden
internet araması yapmaz; detayda durum değiştirdiğinde rozetler güncellenir.
Film/Dizi geçişi ve detaydan geri dönüş görünüm seçimini korur. Yeni bir kişi
seçince veya yeni kişi araması yapınca Yeni keşifler ile başlanır. Normal
içerik/global aramanın kayıtlıları gizleme davranışı korunur.

Film veya dizi detayının altındaki **oyuncu kartına tıklamak**, Keşfet'i
**Oyuncu** modunda doğrudan o kişinin kimliğiyle açar. Filmden geçince filmleri,
diziden geçince dizileri görürsün; soldan kategoriyi değiştirebilirsin.
Kartlara Tab ile odaklanıp Space ile de geçebilirsin.

Hızlı kütüphaneye ekleme korunur. Kişi modunda yıl/tür/ülke/puan filtreleri
uygulanmaz; bu kontroller normal Keşfet içindir.

Kişi araması seçtiğin alanı öne alır; diğer alanlarda bilinen kişileri
dışlamaz. Yönetmen modunda yalnız TMDb'nin **Director** görevi
kullanılır. Oyunculuk, senaristlik, yapımcılık ve dizi yaratıcılığı tek başına
yeterli değildir. Dizi sonuçları TMDb'nin kişi/dizi yönetmenlik kayıtlarıyla
sınırlıdır; bütün bölüm yönetmenliklerini taramaz. Oyuncu modunda kişinin
film/dizi **cast** kayıtları kullanılır; ekip görevleri dahil edilmez.

## Film detayı ve yerel takip

Film arama sonucundan açılan ekran; TMDb detay, oyuncu/yönetmen, video, öneri ve seçilen bölgenin izleme sağlayıcısı verilerini arka planda yükler. Poster ve backdrop görsel servisini kullanır. **Kütüphaneye Ekle** filmi `PLANNED` durumuyla yerel kütüphaneye ekler; takip durumu, favori ve özel liste üyeliği SQLite'ta kalıcıdır. Film metadata'sı aynı veritabanında kişisel durumdan ayrı saklanır. Detay açıldığında kayıtlı metadata hemen gösterilir; son başarılı sync 24 saatten eskiyse arka planda yenilenir. Offline, timeout veya TMDb'de silinmiş kayıt durumunda yerel kopya korunur. **Fragmanı İzle**, uygun YouTube fragmanını sistem tarayıcısında açar. İzleme sağlayıcısı verisi [TMDb'nin JustWatch ortaklığı](https://developer.themoviedb.org/reference/movie-watch-providers) kaynaklıdır.

Dizi detayında orijinal ad, yayın tarihleri, yaratıcılar, oyuncular, yapım bilgileri, Türkiye izleme sağlayıcıları, fragman ve öneriler gösterilir. Sezon seçimi bölüm listesini açar; her bölüm ayrı işaretlenebilir. Sezonun veya dizinin tüm bölümlerini izlendi/izlenmedi yapmak için onay gerekir. Dizi detayı ve her sezonun bölüm metadata'sı kendi son başarılı sync zamanına göre 24 saatlik freshness uygular. Bölüm ilerlemesi yalnızca yerel veritabanındadır ve metadata yenilemesiyle silinmez. Daha önce indirilen metadata çevrimdışı kullanılabilir. Diziler için durum ve favori de kalıcıdır.

Film ve dizi detaylarındaki **Nerede İzlenir** bölümü Ayarlar'daki izleme bölgesinin (varsayılan TR) TMDb watch-provider yanıtını gösterir. Abonelik, kiralama ve satın alma grupları boşsa seçilen bölge için açıklayıcı bir empty state görünür; geçerli TMDb bağlantısı varsa sağlayıcı seçenekleri sistem tarayıcısında açılır. Provider metadata'sı cache'lenir ve takip durumunun parçası değildir. Bölümde JustWatch attribution'ı görünür.

İlk izlenen bölüm otomatik olarak `WATCHING`, bütün bilinen yayınlanmış bölümler izlendiğinde durum `WATCHED` olur. Manuel status seçimi korunur; sonradan gelen yeni bölüm `WATCHED` durumunu sessizce değiştirmez. Ayrıntılar [durum otomasyonu kurallarında](status-automation.md).

## Favoriler

Film ve dizi favorileri SQLite içindeki `user_media.favorite` alanından okunur. Detay sayfalarında ve kütüphane kartlarında kalp düğmesi kullanılır. İstatistikler sayfasında Favorilerim bölümü bulunmaz. Favori ekleme ve çıkarma takip durumunu değiştirmez; durum olmadan da favori tutulabilir.

## Kişisel puan ve not

Film veya dizi detayında **Listeye Ekle** yanındaki **Puan ve not** düğmesine
basarak formu aç. Form işlem düğmelerinin altında görünür.
Form varsayılan olarak kapalıdır; aynı düğmeyle tekrar kapatabilirsin.
Kapatıp açmak yazdığın taslağı korur, otomatik kaydetmez.
**Puanım ve notum** bölümünden 1–10 arasında kendi
puanını ve en fazla 2000 karakterlik notunu girip **Kaydet** düğmesine bas.
**Puan yok** ve boş notla kaydetmek bu bilgileri temizler. TMDb puanı ayrı
kalır; kişisel puanın kütüphane kartında **Ben: 8/10** gibi görünür. Puan/not
vermek içeriği otomatik kütüphaneye eklemez ve izleme durumunu değiştirmez.
Notlar yalnız SQLite'ta tutulur; metadata yenilenince silinmez ve JSON
yedeğine dahil edilir. Notu değiştirdiğinde çıkmadan önce Kaydet'e bas.

## Kütüphane filtreleri ve toplu işlem

Filmler veya Diziler sayfasında **Filtreler** düğmesiyle izleme durumu, tür,
ilk/son yıl, en fazla süre ve en düşük TMDb puanını birlikte seçebilirsin.
**Uygula** sonuçları daraltır; **Temizle** bütün filtreleri kaldırır. Filtreler
yerelde kayıtlı bilgileri kullanır, ağdan bütün kütüphaneyi indirmez. Bilgisi
eksik bir içerik, o alanın etkin filtresiyle eşleşmez. Dizilerde süre,
kayıtlı bölüm sürelerinin en büyüğüdür; bilinmeyen süre uydurulmaz.

**Seç** düğmesine basıp kartları veya seçim kutularını işaretle. **Görünenlerin
tümü**, mevcut filtreyle eşleşen bütün kartları seçer; ekran dışında kalan
eşleşmeler de dahildir. **Toplu işlem** penceresinde izleme durumu değiştirme,
favorilere ekleme/çıkarma veya mevcut listeye ekleme seçilebilir. İzleme
durumunu değiştirmeden önce seçili içerik sayısını gösteren onay açılır.
Dizilerde toplu durum değişimi bölüm işaretlerini değiştirmez. İşlem aynı
transaction'da tamamlanır; bir kayıt geçersizse kısmi değişiklik yapılmaz.
Filtre değişince seçim temizlenir. Filtre veya seçim açıkken sürükleyerek
sıralama kapalıdır; özel sıran korunur. Ana grid filtrelenir, Favoriler ve
Devam Et bölümleri bağımsız kalır.

## Bir daha önerme

Keşfet'te normal öneri kartının sağ üstündeki **⊘** düğmesi veya detayın
kişisel puan/not bölümündeki **Bir daha önerme**, içeriği Keşfet ve film/dizi
önerilerinden gizler. Bu işlem takip durumunu, favoriyi veya listeleri
değiştirmez. **Ayarlar → Önerilerden gizlediklerim → Yeniden göster** ile ya
da detayda **Önerilerde yeniden göster** ile geri açabilirsin. Kendi
kütüphanen ve açık ad/oyuncu/yönetmen araması bu gizleme tercihinden etkilenmez;
aramadaki mevcut kayıtlıları gizleme kuralı ve Tüm yapımları seçimi korunur.

## Film ve dizi kartlarını sıralama

**Filmler** ve **Diziler** sayfalarında afişin veya başlığın üzerinden sol
fare tuşuyla kartı tutup başka bir kartın üzerine bırak. Ayrı sürükleme
tutamacı yoktur. Kısa tıklama detayı açar; hareket sürükleme eşiğini geçince
detay açılmadan sıralama başlar. Küçük bir afiş önizlemesi fareyi izler.
Görünen sıra kaydedilir ve **Özel Sıram** seçilir. Alanın üst/alt kenarına
yaklaşınca içerik otomatik kayar; fare tekerleği normal kaydırmayı sürdürür.
İki kategorinin sırası ayrıdır; uygulamayı kapatıp açınca korunur ve JSON
yedeğine dahil edilir. Sıralamayı başlık, yıl veya puan olarak değiştirmek
kaydettiğin özel sırayı silmez; **Özel Sıram** ile geri dönebilirsin.
Favori ve seçim düğmeleri bağımsız çalışır. Filtreler veya çoklu seçim modu
açıkken sıralama kapalıdır. Alanın dışına bırakmak sırayı değiştirmez.

## Özel listeler

**Listeler** sayfasında liste oluşturabilir, yeniden adlandırabilir ve silebilirsin. Sol panelde listeleri, sağ panelde seçilen listenin film ve dizilerini görürsün. Yerel veritabanında bilinen medyayı ekleyebilir, çıkarabilir; ok düğmeleriyle liste ve medya sırasını değiştirebilirsin. Aynı medya birden fazla listede bulunabilir. Film ve dizi detayındaki **Listeye Ekle**, mevcut liste adıyla eşleşir veya yeni liste oluşturur. Bütün liste verileri SQLite'ta kalır; TMDb liste API'si kullanılmaz.

**+ İçerik Ekle** afişli bir seçim penceresi açar. Yerelde bilinen film ve
diziler arasında ara, birden çok içeriği işaretle ve **Seçilenleri Ekle**
düğmesine bas. Başka bir arama yaptığında önceki seçimlerin korunur;
**Seçimi temizle** hepsini kaldırır. Aynı içerik iki kez eklenmez ve listede
zaten bulunanlar seçim penceresinde gösterilmez. **Esc** veya **Vazgeç**
eklemeden kapatır. Liste adlarını ve liste içindeki içerikleri **⠿**
tutamacından sürükleyerek de sıralayabilirsin; ok düğmeleri korunur.

Liste satırlarında **İzlendi**, **İzleniyor**, **İzlenecek** veya
**İzlenmedi** etiketi yerel takip durumunu gösterir. Takip durumu olmayan
kayıtlar İzlenmedi olarak gösterilir. Durumu detay ekranında değiştirdikten
sonra listene döndüğünde etiket güncellenir.

## İçe ve dışa aktarma

**Ayarlar → İçe / Dışa Aktarma** bölümünden tüm taşınabilir İzlek durumunu tek bir JSON dosyasına aktarabilirsin. Dosya film/dizi metadata'sını, takip durumlarını, bölüm ilerlemesini, favorileri ve özel listeleri içerir; TMDb tokenı ile indirilen görsel cache yollarını içermez. Aynı ekrandan **Trakt** dışa aktarma JSON dizileri (izlenen film/dizi, geçmiş, puan, izleme listesi) ve **Letterboxd** CSV dosyaları da içe aktarılabilir; Letterboxd satırlarında çevrimdışı eşleşme için `tmdbID` / `tmdb_id` sütunu gerekir. Import öncesinde dosya doğrulanır ve medya/liste özeti gösterilir. Aynı TMDb kimliği ve medya türü birleştirilir; izlenmiş bölüm ilerlemesi ile mevcut liste üyelikleri kaybolmaz. İzlek biçimi ve sürüm stratejisi [İzlek JSON belgesinde](izlek-json.md) açıklanır.

## Meta veri kaynakları ve izleme bölgesi

**Ayarlar → İzleme bölgesi** Nerede İzlenir verisinin ülke kodunu seçer (varsayılan Türkiye). **Ayarlar → Meta veri kaynakları** TMDb'yi varsayılan katalog olarak tutar; Trakt, TVmaze ve OMDb isteğe bağlıdır. Her kaynakta yalnız uygulamanın ihtiyaç duyduğu yetenekler (arama, keşfet, detay, sezon, kişi, görsel, fragman, sağlayıcı, başlık zenginleştirme) açılıp kapatılabilir. OMDb yalnızca kişisel / ticari olmayan kullanım onayıyla etkinleştirilir. Ayrıntılar [METADATA_SOURCES.md](METADATA_SOURCES.md) belgesindedir.
