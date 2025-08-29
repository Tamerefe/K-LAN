# Kiss Kill Marry — Valorant Edition

Bu proje, Valorant ajanları ile "Kiss / Kill / Marry" (Öp / Öldür / Evlen) oyununu eğlenceli ve özelleştirilebilir bir şekilde oynayabilmenizi sağlar. Proje Python ile yazılmıştır ve ajan listesi `character.txt` dosyasından çekilir.

## Özellikler

- `character.txt` içindeki ajanlardan rastgele seçimler
- Oyunun akışını yöneten Python betiği: `lan_kkm.py`
- Terminal/PowerShell üzerinden kolay kurulum ve çalıştırma
- Kolayca özelleştirilebilir içerik (ajan listesi ve oyun kuralları)

## Gereksinimler

- Python 3.8+ (Windows, macOS veya Linux)

## Kurulum

1. Bu projeyi indirin veya klonlayın.
2. Bilgisayarınızda Python yüklü olduğundan emin olun.

Windows PowerShell üzerinden örnek kullanım:

```powershell
# Proje klasörüne girin
cd "C:\Users\polis\Desktop\KissKillMarryValorantEdition"

# (Opsiyonel) Sanal ortam oluşturun
python -m venv .venv
./.venv/Scripts/Activate.ps1

# Gerekli bağımlılıkları yükleyin
pip install -r requirements.txt

# Ardından çalıştırın
python lan_kkm.py
```

> Not: Eğer güvenlik politikası nedeniyle `Activate.ps1` çalışmıyorsa, PowerShell'de geçici olarak izin verebilirsiniz:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

## Kullanım

```powershell
python lan_kkm.py
```

Komut çalıştırıldığında oyun başlar ve sizden seçimler yapmanız istenir.

## Ajan Listesini Düzenleme

- Ajanlar `character.txt` dosyasında satır satır bulunur.
- Yeni ajan eklemek için dosyanın sonuna yeni bir satır ekleyin.
- Bir ajanın oyunda yer almamasını istiyorsanız ilgili satırı silebilir veya başına `#` koyarak pasifleştirebilirsiniz (eğer betik yorum satırlarını atlayacak şekilde yapılandırıldıysa).

## Proje Yapısı

```
KissKillMarryValorantEdition/
├─ lan_kkm.py        # Oyun akışını yöneten ana Python dosyası
├─ character.txt     # Ajan isimleri (her satırda bir ajan)
├─ README.md         # Proje açıklaması ve kullanım talimatları
└─ LICENSE           # Lisans metni (MIT)
```

## Katkıda Bulunma

Katkılarınızı memnuniyetle karşılıyoruz:

1. Bir fork oluşturun
2. Yeni bir dal (branch) açın: `git checkout -b feature/yenilik`
3. Değişikliklerinizi yapın ve commit atın
4. Bir Pull Request (PR) oluşturun

Kod yazarken okunabilirliği ve tutarlılığı korumaya özen gösterin.

## Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır. Ayrıntılar için `LICENSE` dosyasına bakın.

## Teşekkürler

- Valorant ve tüm ajanlar, ilgili sahiplerine aittir. Bu proje tamamen topluluk amaçlıdır ve ticari bir kullanım hedeflemez.
