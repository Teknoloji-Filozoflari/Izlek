# RPM paketi

`scripts/build_rpm.py`, AppImage ile aynı PyInstaller one-folder çıktısını
offscreen doğrular ve `packaging/rpm/izlek.spec` ile RPM üretir. Python/Qt
paketin içinde bulunur; sistem bağımlılıkları spec içinde açıkça tanımlıdır.
Özel bundle kütüphaneleri sistem için Provides/Requires olarak dışa aktarılmaz;
diğer RPM paketlerinin gerçek sistem kütüphanelerine ihtiyacı doğru çözülür.
Uygulama `/usr/lib/izlek`, başlatıcı `/usr/bin/izlek` altına kurulur.

Fedora build ortamında:

```bash
sudo dnf install python3 python3-pip gcc binutils rpm-build \
  mesa-libEGL mesa-libGL fontconfig libX11 libX11-xcb libxcb \
  libxkbcommon libxkbcommon-x11
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,package]'
python scripts/quality.py
python scripts/build_rpm.py
sudo dnf install ./dist/izlek-*.rpm
```

`--skip-onedir-build`, aynı hedef sistem için önceden üretilmiş `dist/izlek`
çıktısını kullanır; açılış kontrolünü atlamaz. `--output-dir` çıktı dizinini
değiştirir. Build işlemi sistem dizinlerine yazmaz; rpmbuild geçici bir
çalışma dizini kullanır.

GitHub Actions **RPM package** workflow'u Fedora 43 x86_64 üzerinde üretim
ve ayrı temiz container'da kurulum/açılış/kaldırma kontrolü yapacak şekilde
tanımlıdır. Workflow elle başlatılır; GitHub Releases'a otomatik yüklemez.
Betik aarch64 build hostunu da kabul eder; aarch64 CI doğrulaması yoktur.

RPM dağıtımlarında aynı dosyanın her yerde çalışacağı varsayılmaz: bundle'ın
glibc tabanı build ortamına bağlıdır. openSUSE ve eski Fedora sürümleri için
ayrı build/kurulum testi gerekir. Bu tarif Fedora'nın resmî paket deposuna
kabul edilmiş bir kaynak paket tarifi değildir. Kullanıcı XDG verileri paket
kaldırıldığında silinmez.

Tarif referansı: [RPM spec belgeleri](https://rpm.org/docs/4.20.x/manual/spec.html).
