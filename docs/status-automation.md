# Dizi takip durumu otomasyonu

Takip durumu `user_media` tablosunda, bölüm ilerlemesi `episode_progress` tablosunda tutulur. `status_is_manual` kullanıcı seçimini otomatik durumdan ayırır. Eski veritabanındaki dolu durumlar migration sırasında manuel seçim olarak işaretlenir.

| Olay | Otomatik durum |
| --- | --- |
| İzlenen bölüm yok | Boş kalır. Son izlenen bölüm geri alınırsa otomatik durum temizlenir. |
| İlk bölüm izlendi; tüm yayınlanmış bölümler tamamlanmadı | `WATCHING` |
| Yerel sezon metadata'sı tam ve en az bir yayınlanmış bölüm var; tamamı izlendi | `WATCHED` |
| Kullanıcı status'u manuel seçti | Seçim korunur; bölüm işlemleri değiştirmez. |
| Yeni bölüm metadata'sı geldi | Status değiştirilmez. Yayınlanmış izlenmemiş bölüm sayısı ayrıca gösterilir. |
| Otomatik `WATCHED` durumunda bölüm açıkça izlenmedi yapıldı | Kalan ilerlemeye göre `WATCHING` veya boş durum. |

Yayınlanmış bölüm, yayın tarihi bugün veya daha önce olan bölümdür. Tarihi bilinmeyen ve gelecekte yayınlanacak bölümler tamamlanma kararına katılmaz. `WATCHED` kararı için TMDb'nin bildirdiği sezon bölüm sayıları kadar bölüm metadata'sının yerelde bulunması gerekir. Eksik sezonda uygulama `WATCHING` durumunda kalır; bilmediği bölümleri izlenmiş varsaymaz.

Otomatik durum yalnızca tekil veya toplu bölüm ilerlemesi değiştiğinde, aynı SQLite transaction içinde güncellenir. Metadata yüklemesi/yenilemesi status'a veya izleme ilerlemesine yazmaz. Otomatik `WATCHED` durumundaki bir diziye yeni bölüm gelirse `WATCHED` korunur; kullanıcı bölümün izlenmediğini detay ekranında görür.
