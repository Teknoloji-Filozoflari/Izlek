# Faz 24 performans profili

## Senaryo

`tests/test_performance.py` geçici SQLite veritabanında 500 film, 200 dizi,
200 sezon, 10.000 bölüm, 2.000 izlenmiş bölüm ve 20 özel liste üretir. Senaryo
tamamen yereldir; TMDb istemcisi ağ çağrısı yapılırsa testi bilerek düşürür.

Ölçümler bu geliştirme ortamında, sıcak Python süreci ve soğuk servis çağrılarıyla
alındı. Süreler farklı makinelerde değişebilir; otomatik regresyonun asıl sabit
bütçesi SQL sorgu sayısıdır.

| Akış | Süre | SQL sorgusu |
| --- | ---: | ---: |
| 500 filmlik kütüphane snapshot | 8,7 ms | 1 |
| 200 dizi + 10.000 bölüm ilerlemesi | 214,6 ms | 2 |
| 10.000 bölümden Devam Et hesabı | 208,5 ms | 1 |
| Film detayının yerel kopyası | 4,6 ms | 4 |
| Dizi detayının yerel kopyası | 3,3 ms | 5 |
| 50 bölümlük sezon görünümü | 1,3 ms | 3 |
| 20 liste + 700 medya snapshot | 6,3 ms | 3 |

Sentetik verinin oluşturulması 338,3 ms sürdü. Bu süre kullanıcı akışının parçası
değildir.

## Profil sonucu ve uygulanan sınırlar

- Dizi ilerlemesi sezon ve bölüm başına sorgu yerine tek join ile okunur.
- Detay sayfalarındaki liste üyelikleri liste başına sorgu yerine tek join kullanır.
- Liste ekranı bütün üyelikleri ve medya adaylarını üç sabit sorguyla hazırlar.
- Kütüphane controller'ı 500 poster isteği başlatmaz. Yalnızca GridView/ListView
  tarafından oluşturulan görünür delegeler thumbnail ister; aynı medya isteği bir
  generation içinde yinelenmez.
- Poster güncellemeleri 16 ms pencere içinde birleştirilir. QML GridView delegeleri
  sanallaştırılır; bölüm görünümü de `reuseItems` kullanan sınırlı yükseklikte bir
  ListView'dır.
- QML `Image.sourceSize`, ekrandaki hedef ölçü ve device pixel ratio ile
  sınırlandırılır; thumbnail için gereksiz büyük decode yüzeyi ayrılmaz.
- Film, dizi, Keşfet, kütüphane, dashboard ve arama görevleri generation ile
  geçersiz kılınır. Sayfadan çıkışta başlamamış Future'lar iptal edilir; başlamış
  senkron HTTP çağrıları timeout sınırına kadar sürebilir ancak sonuçları UI'ya
  yazamaz.
- Film ve dizi detayının ilk çevrimiçi yükü ana endpoint dahil altı TMDb isteğidir;
  testler yinelenen istek olmadığını doğrular.

## Yaşam döngüsü denetimi

Controller nesneleri QML engine'e parent edilir ve uygulama kapanışında `close()`
çağrısı alır. Sahip olunan executor, ImageService, HTTP client ve SQLAlchemy engine
yalnızca sahibi tarafından kapatılır. Future callback'leri generation kontrolünden
geçer; kapatılan veya görünmez sayfanın QML durumunu değiştiremez. StackView sayfa
örnekleri Component üzerinden üretildiği için `replace`/`pop` sonrasında kalıcı bir
QML sahiplik döngüsü bulunmadı.

Gerçek Wayland/X11 compositor altında kare süresi bu sandbox'ta ölçülemedi. Scroll
akıcılığı için otomatik koruma; görünür-delege lazy load, GridView/ListView
sanallaştırması, arka plan I/O ve sorgu bütçeleridir.
