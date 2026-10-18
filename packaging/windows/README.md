# Windows EXE

Hedef Windows 10/11 x64'tür. Aynı Python/PySide6 uygulaması PyInstaller ile
Windows üzerinde derlenir; Inno Setup kullanıcıya ait bir kurulum EXE'si üretir.
Linux'ta Windows EXE üretilmez. İlk gerçek Windows Actions koşusu henüz
doğrulanmadı; kaynak testlerinin geçmesi Windows binary doğrulaması değildir.

## GitHub'dan üretme ve indirme

Kaynak/paketleme değişikliği push edilince **Windows EXE** workflow'u başlar.
Ayrıca **Actions → Windows EXE → Run workflow** ile elle çalıştırılabilir.
Başarılı koşuda **Artifacts → izlek-windows-x64** arşivi şunları içerir:

- `Izlek-<sürüm>-windows-x64-setup.exe`
- Aynı dosyanın `.sha256` doğrulaması

Artifact arşivini açıp EXE'yi çalıştır. GitHub Actions artifact'ini indirmek
için GitHub oturumu gerekir. Yeni `v*` release etiketinde Windows workflow'u
Linux paketleriyle birlikte çalışır ve başarılı EXE release'e yüklenir.
Mevcut v1.0.1 release'inde Windows dosyası varmış gibi indirme bağlantısı verilmez.

## Yerelde üretme

Windows'ta x64 Python 3.11+, PyInstaller ve Inno Setup gerekir:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,package]"
python scripts/build_windows.py --iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

Inno Setup 7 kullanıyorsan kendi `ISCC.exe` yolunu ver. Sonuç `dist/windows/`
altına yazılır. Build betiği QML, ikonlar, SQLite migration'ları ve
`qwindows.dll` varlığını; paketli uygulamanın açılışını; geçici klasörde sessiz
kurulum/başlatma/kaldırmayı ve kişisel verinin korunmasını kontrol eder.
Derleme girdileri yalnız uygulama kaynakları ve lisansıdır; deneme kütüphanesi,
API tokenı, geliştirme raporları ve README ekran görüntüleri EXE'ye eklenmez.

## Kurulum ve veri

Yönetici yetkisi istemeyen kurulum `%LOCALAPPDATA%\Programs\Izlek` altındadır.
Ayarlar `%APPDATA%\izlek`, kütüphane `%LOCALAPPDATA%\izlek` içindedir.
Kaldırıcı kişisel veri klasörlerine dokunmaz. Mutlak `XDG_*` değişkenleri
ayrıca geliştirme ve test izolasyonu için desteklenir.

Token önce Windows anahtarlığında saklanır. Anahtarlık kullanılamazsa profil
ayar klasöründe düz metin fallback dosyası kullanılır; erişim Windows ACL'leri
ile yönetilir, POSIX 0600 bitleri Windows'ta erişim denetimi sayılmaz.

İlk paket imzasızdır; kod imzalama sertifikası bu projeye eklenmedi.

Kaynaklar: [PyInstaller](https://pyinstaller.org/en/stable/usage.html#supporting-multiple-operating-systems),
[Inno Setup kullanıcı kurulumu](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm).
