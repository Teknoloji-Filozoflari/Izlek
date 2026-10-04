# Snap paketi

`snap/snapcraft.yaml`, core24 tabanlı amd64, strict confinement kullanan
bir geliştirme paketi üretir. PyInstaller bundle QML, Qt/Python, ikon ve
migration kaynaklarını içerir. Build sırasında Ruff, pytest ve offscreen
bundle kontrolü çalışır.

Snapcraft ve LXD build ortamı hazırlanmış bir makinede proje kökünden:

```bash
snapcraft
sudo snap install --dangerous ./izlek_1.0.1_amd64.snap
izlek
```

`--dangerous`, Store imzası bulunmayan yerel build içindir; paket strict
confinement kullanmaya devam eder. GitHub Actions **Snap package** workflow'u
elle başlatıldığında build, yerel snap kurulumu ve offscreen açılış kontrolü
çalışır; çıktı workflow artifact'i olarak saklanır.

Veritabanı, ayarlar, cache ve loglar launcher tarafından
`~/snap/izlek/common/{data,config,cache,state}/izlek` dizinlerine yönlendirilir.
Bu yollar revizyon güncellemelerinde kalır. Sistem paketiyle Snap kurulumu
ayrı kütüphaneler kullanır; taşımak için uygulamanın JSON import/export'unu
kullanın. Snap kaldırmadan önce export alın; `snap remove --purge` Snap
kullanıcı verilerini de kaldırabilir.

İnternet, X11/Wayland, OpenGL, masaüstü ve JSON import/export için home
interface'leri tanımlıdır. Sistem anahtarlığına erişim otomatik
bağlanmayabilen `password-manager-service` interface'ini kullanır:

```bash
sudo snap connect izlek:password-manager-service
```

Anahtarlık kullanılamazsa mevcut uygulama davranışı geçerlidir: token yalnız
kullanıcıya açık dosyada saklanır ve arayüz bunu bildirir. `home` interface'i
ev dizinindeki gizli dosyalara veya çıkarılabilir disklere genel erişim vermez.

Snap Store'a yayın otomatik yapılmaz. Önce `izlek` adının Store'da kaydı ve
sahipliği doğrulanmalı, gerçek masaüstü/sandbox testleri tamamlanmalı,
`grade: devel` yayın hedefine göre düzenlenmelidir. Sürümü pyproject.toml ile
birlikte güncelleyin.

Referanslar: [Snap build action](https://github.com/canonical/action-build),
[anahtarlık interface'i](https://snapcraft.io/docs/reference/interfaces/password-manager-service-interface/).

## Hazır paket

[v1.0.1 GitHub sürümünden](https://github.com/Teknoloji-Filozoflari/Izlek/releases/tag/v1.0.1)
`izlek_1.0.1_amd64.snap` indirilebilir. Store imzası bulunmadığından
yukarıdaki `--dangerous` kurulum komutunu kullanın.
[Build ve strict kurulum](https://github.com/Teknoloji-Filozoflari/Izlek/actions/runs/37213775236)
ve [sanal X11 pencere kontrolü](https://github.com/Teknoloji-Filozoflari/Izlek/actions/runs/37214317330)
başarılıdır.
