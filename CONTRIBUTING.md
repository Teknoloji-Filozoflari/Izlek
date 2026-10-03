# Katkı Rehberi

Önce [README.md](README.md) içindeki geliştirici kurulumunu yapın ve
[mimariyi](docs/architecture.md) okuyun. Küçük, tek amaçlı değişiklikler
önerin; yeni özelliklerde önce ilgili issue ile kapsamı netleştirin. Yeni bir
dalı `feature/`, `fix/` veya `docs/` önekiyle açın.

Python için type hint, dört boşluk girinti ve `snake_case` kullanın. İş
mantığını QML içinde tutmayın; mevcut servis, repository ve tema tokenlarını
yeniden kullanın. Değişikliğe uygun pytest testlerini ekleyin. PR açmadan önce
şu kalite kapısını çalıştırın:

```bash
python scripts/quality.py
python -m pip wheel . --no-deps --wheel-dir dist
```

PR açıklamasında değişikliğin amacı, test sonucu ve ilgili issue bağlantısı
bulunsun. Görünür arayüz değişikliğine ekran görüntüsü ekleyin. Commit
başlıklarını kısa ve emir kipinde yazın. Kullanıcı verisi, token veya cache
dosyalarını commit etmeyin. Katılımda [davranış kurallarına](CODE_OF_CONDUCT.md)
uyun.
