# Dizi takip durumu otomasyonu

Takip durumu `user_media` tablosunda, bölüm ilerlemesi `episode_progress` tablosunda tutulur. Eski veritabanındaki dolu durumlar migration sırasında manuel seçim olarak işaretlenir. 2026-10-04 kullanıcı isteğiyle bölüm işlemleri artık bu eski seçimleri de ilerlemeye göre günceller ve `status_is_manual` alanını kapatır. Yalnızca metadata yenilemesi kişisel durumu değiştirmez.

| Olay | Otomatik durum |
| --- | --- |
| İzlenen bölüm yok | Takip edilmiyorsa boş kalır; kütüphanedeki dizi `WATCHING` kalır, kütüphaneden silinmez. |
| İlk bölüm izlendi; tüm yayınlanmış bölümler tamamlanmadı | `WATCHING` |
| Yerel sezon metadata'sı tam ve en az bir yayınlanmış bölüm var; tamamı izlendi | `WATCHED` |
| Eski manuel status'u olan dizide bölüm işlemi | Yeni ilerlemeye göre `WATCHING` veya `WATCHED`; eski `PLANNED` tamamlanmayı engellemez. |
| Metadata tam ve var olan tüm bölümler izlendi | Tarihi bilinmeyen bölümler dahil `WATCHED`. |
| Yeni bölüm metadata'sı geldi | Status değiştirilmez. Yayınlanmış izlenmemiş bölüm sayısı ayrıca gösterilir. |
| `WATCHED` durumunda bölüm açıkça izlenmedi yapıldı | Kalan ilerlemeye göre `WATCHING`; tamamı geri alınsa da kütüphane üyeliği korunur. |

Yayınlanmış bölüm, yayın tarihi bugün veya daha önce olan bölümdür. Tarihi bilinmeyen ve gelecekte yayınlanacak bölümler tamamlanma kararına katılmaz. `WATCHED` kararı için TMDb'nin bildirdiği sezon bölüm sayıları kadar bölüm metadata'sının yerelde bulunması gerekir. Eksik sezonda uygulama `WATCHING` durumunda kalır; bilmediği bölümleri izlenmiş varsaymaz.

Otomatik durum yalnızca tekil veya toplu bölüm ilerlemesi değiştiğinde, aynı SQLite transaction içinde güncellenir. Metadata yüklemesi/yenilemesi status'a veya izleme ilerlemesine yazmaz. Otomatik `WATCHED` durumundaki bir diziye yeni bölüm gelirse `WATCHED` korunur; kullanıcı bölümün izlenmediğini detay ekranında görür.
