# Kullanım rehberi

[README’ye dön](../README.md)

## Global arama

Ana penceredeki her sayfadan **Ctrl+K** ile arama açılır, **Esc** ile kapanır. En az üç karakter girildiğinde 300 ms bekledikten sonra TMDb film ve dizi aramaları arka planda paralel çalışır. Sonuçlar ayrı başlıklarda orijinal ad, yıl, tür ve cache'lenmiş posterle gösterilir. Sonuca tıklamak medya detay sayfasını açar. Çevrimdışıyken açıklayıcı hata gösterilir.

## Keşfet

**Keşfet**, TMDb'nin yalnızca Discover Movie ve Discover TV uçlarını kullanır. Film veya dizi, yıl, tür, ülke ve puan aralığı seçilebilir. Sonuçlar `vote_average.desc` ile sıralanır; az sayıdaki oyun sıralamayı bozmasını önlemek için varsayılan en az oy eşiği 100'dür. Sonuçlar yoğun gridde gösterilir ve açık önceki/sonraki düğmeleriyle sayfalanır.

## Film detayı ve yerel takip

Film arama sonucundan açılan ekran; TMDb detay, oyuncu/yönetmen, video, öneri ve Türkiye izleme sağlayıcısı verilerini arka planda yükler. Poster ve backdrop görsel servisini kullanır. **Kütüphaneye Ekle** filmi `PLANNED` durumuyla yerel kütüphaneye ekler; takip durumu, favori ve özel liste üyeliği SQLite'ta kalıcıdır. Film metadata'sı aynı veritabanında kişisel durumdan ayrı saklanır. Detay açıldığında kayıtlı metadata hemen gösterilir; son başarılı sync 24 saatten eskiyse arka planda yenilenir. Offline, timeout veya TMDb'de silinmiş kayıt durumunda yerel kopya korunur. **Fragmanı İzle**, uygun YouTube fragmanını sistem tarayıcısında açar. İzleme sağlayıcısı verisi [TMDb'nin JustWatch ortaklığı](https://developer.themoviedb.org/reference/movie-watch-providers) kaynaklıdır.

Dizi detayında orijinal ad, yayın tarihleri, yaratıcılar, oyuncular, yapım bilgileri, Türkiye izleme sağlayıcıları, fragman ve öneriler gösterilir. Sezon seçimi bölüm listesini açar; her bölüm ayrı işaretlenebilir. Sezonun veya dizinin tüm bölümlerini izlendi/izlenmedi yapmak için onay gerekir. Dizi detayı ve her sezonun bölüm metadata'sı kendi son başarılı sync zamanına göre 24 saatlik freshness uygular. Bölüm ilerlemesi yalnızca yerel veritabanındadır ve metadata yenilemesiyle silinmez. Daha önce indirilen metadata çevrimdışı kullanılabilir. Diziler için durum ve favori de kalıcıdır.

Film ve dizi detaylarındaki **Nerede İzlenir** bölümü varsayılan olarak TR bölgesinin TMDb watch-provider yanıtını gösterir. Abonelik, kiralama ve satın alma grupları boşsa Türkiye için açıklayıcı bir empty state görünür; geçerli TMDb bağlantısı varsa sağlayıcı seçenekleri sistem tarayıcısında açılır. Provider metadata'sı cache'lenir ve takip durumunun parçası değildir. Bölümde JustWatch attribution'ı görünür.

İlk izlenen bölüm otomatik olarak `WATCHING`, bütün bilinen yayınlanmış bölümler izlendiğinde durum `WATCHED` olur. Manuel status seçimi korunur; sonradan gelen yeni bölüm `WATCHED` durumunu sessizce değiştirmez. Ayrıntılar [durum otomasyonu kurallarında](status-automation.md).

## Favoriler

Film ve dizi favorileri SQLite içindeki `user_media.favorite` alanından okunur. Detay sayfalarında ve kütüphane kartlarında kalp düğmesi kullanılır. İstatistikler sayfasında Favorilerim bölümü bulunmaz. Favori ekleme ve çıkarma takip durumunu değiştirmez; durum olmadan da favori tutulabilir.

## Özel listeler

**Listeler** sayfasında liste oluşturabilir, yeniden adlandırabilir ve silebilirsin. Sol panelde listeleri, sağ panelde seçilen listenin film ve dizilerini görürsün. Yerel veritabanında bilinen medyayı ekleyebilir, çıkarabilir; ok düğmeleriyle liste ve medya sırasını değiştirebilirsin. Aynı medya birden fazla listede bulunabilir. Film ve dizi detayındaki **Listeye Ekle**, mevcut liste adıyla eşleşir veya yeni liste oluşturur. Bütün liste verileri SQLite'ta kalır; TMDb liste API'si kullanılmaz.

## İçe ve dışa aktarma

**Ayarlar → İçe / Dışa Aktarma** bölümünden tüm taşınabilir İzlek durumunu tek bir JSON dosyasına aktarabilirsin. Dosya film/dizi metadata'sını, takip durumlarını, bölüm ilerlemesini, favorileri ve özel listeleri içerir; TMDb tokenı ile indirilen görsel cache yollarını içermez. Import öncesinde şema doğrulanır ve medya/liste özeti gösterilir. Aynı TMDb kimliği ve medya türü birleştirilir; izlenmiş bölüm ilerlemesi ile mevcut liste üyelikleri kaybolmaz. Biçim ve sürüm stratejisi [İzlek JSON belgesinde](izlek-json.md) açıklanır.
