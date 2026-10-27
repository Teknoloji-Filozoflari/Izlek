# Güvenlik Politikası

## Desteklenen sürümler

| Sürüm | Destek |
| --- | --- |
| 1.1.x | Desteklenir (kararlı) |
| 1.0.x | Güvenlik düzeltmeleri (mümkün olduğunca) |
| < 1.0 | Desteklenmez |

İzlek **1.1.x** kararlı sürüm hattındadır. Güvenlik düzeltmeleri mümkün
olduğunca bu hatta yayımlanır; sürüm notları ve `CHANGELOG.md` içinde
açıklanır.

## Güvenlik açığı bildirimi

Güvenlik açığı bulursanız herkese açık issue veya PR içinde exploit, token ya
da kişisel veri paylaşmayın. Repository'nin GitHub **Report a vulnerability** /
özel güvenlik bildirim kanalını kullanın. Bu kanal etkin değilse hassas
ayrıntı vermeden bakımcılardan özel iletişim kanalı isteyin.

Bildirimde etkilenen sürümü, işletim sistemi ve ortamı, yeniden üretme
adımlarını, olası etkiyi ve geçici azaltmayı belirtin. TMDb token'larını,
SQLite dosyalarını veya gerçek kullanıcı verilerini eklemeyin; gerekiyorsa
maskelenmiş ve en küçük örneği paylaşın.

## Yanıt süreci

Bakımcılar bildirimi aldıklarını **makul bir süre içinde** (hedef: 7 gün)
teyit eder; etkiyi inceler, düzeltmeyi planlar ve kullanıcıları uygun bir
release / changelog notuyla bilgilendirir. Kritik açıklamalar için düzeltme
hazır olduktan sonra makul bir açıklama penceresi hedeflenir. Public issue
yalnızca düzeltme yayımlandıktan sonra veya bakımcıların yönlendirmesiyle
açılmalıdır.

## Tehdit modeli (özet)

İzlek yerel öncelikli, tek kullanıcılı bir masaüstü uygulamasıdır. Hesap,
telemetri veya bulut senkronu yoktur. TMDb token'ı keyring (veya kısıtlı dosya
yedek yolu) ile saklanır; dışa aktarılan JSON token ve cache yollarını
içermez. SQLite kütüphane/not/etiket verisi dosya sistemi erişimine açıktır—
paylaşılan makinelerde işletim sistemi kullanıcı yalıtımına güvenilir.
