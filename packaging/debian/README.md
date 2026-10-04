# Debian ve Ubuntu paketi

`scripts/build_deb.py`, PyInstaller one-folder uygulamasını
`/usr/lib/izlek` altına, başlatıcıyı `/usr/bin/izlek` altına, masaüstü
kaydını `/usr/share/applications` altına ve SVG simgesini hicolor temasına
yerleştirerek bağımsız bir `.deb` üretir.

Bu yaklaşım sistem Python paketlerini paketlemez: Ubuntu 22.04/24.04
depolarındaki PySide6/Pydantic sürümleri proje gereksinimleriyle aynı değildir.
Paketin yalnızca paylaşılan Linux/Qt kütüphaneleri `Depends` alanındadır;
Python uygulaması ve Python bağımlılıkları one-folder bundle içindedir.

Build ortamında Python 3.11, PyInstaller ve proje paket bağımlılıkları
kurulduktan sonra:

```bash
python -m pip install --constraint packaging/constraints-appimage.txt -e '.[package]'
python scripts/build_deb.py \
  --homepage "$REPOSITORY_URL" \
  --maintainer "$DEBIAN_MAINTAINER"
sudo apt install ./dist/izlek_1.0.1_amd64.deb
```

Build betiği `dpkg-deb` gerektirir ve `dist/` altında paketi üretir. Kurulumun
ardından uygulama menüsünde **İzlek** görünür. `apt remove izlek` yalnızca
paket dosyalarını kaldırır; `$XDG_DATA_HOME/izlek`, `$XDG_CONFIG_HOME/izlek`
ve `$XDG_CACHE_HOME/izlek` altındaki kullanıcı verileri silinmez.

`REPOSITORY_URL` gerçek HTTPS upstream adresi, `DEBIAN_MAINTAINER` ise
`Ad <eposta>` biçimindeki paket sorumlusudur. Build betiği bu metadata olmadan
paket üretmez; tag workflow'u değerleri GitHub repository bağlamından geçirir.

## Hazır paket

[v1.0.1 GitHub sürümünden](https://github.com/Teknoloji-Filozoflari/Izlek/releases/tag/v1.0.1)
`izlek_1.0.1_amd64.deb` indirip `sudo apt install ./izlek_1.0.1_amd64.deb`
ile kurabilirsiniz. Ubuntu 22.04 ve 24.04 üzerinde
[build, temiz kurulum ve açılış](https://github.com/Teknoloji-Filozoflari/Izlek/actions/runs/37213773457)
kontrolleri başarılıdır. Diğer Debian türevleri ayrıca doğrulanmalıdır.
