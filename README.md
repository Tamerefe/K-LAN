# 🎮 K-LAN - LAN Çok Oyunculu Oyun Platformu

Yerel ağ (LAN) üzerinden arkadaşlarınızla çok oyunculu oyunlar oynayabileceğiniz modüler bir platform. Tombala, Trust No One ve diğer klasik oyunları LAN üzerinden oynayın!

## 🚀 Hızlı Başlangıç

### Windows Kullanıcıları İçin (Python'suz!)

1. **K-LAN.exe** dosyasını çift tıklayın
2. Oyun menüsünden bir oyun seçin
3. Başlayın!

*Not: .exe dosyası yoksa `build.bat` dosyasına çift tıklayarak oluşturabilirsiniz.*

### Python ile Başlatma

**Seçenek 1 - Hızlı Başlatma (.bat dosyası)**
- **K-LAN.bat** dosyasına çift tıklayın

**Seçenek 2 - Manuel**
```powershell
python main.py
```

## 📁 Proje Yapısı

```
K-LAN/
├── main.py                    # Ana arayüz - oyun seçici
├── K-LAN.bat                  # Hızlı başlatma dosyası
├── build.bat                  # .exe oluşturma scripti
├── logo.jpg                   # Proje logosu
├── requirements.txt           # Python bağımlılıkları
├── LICENSE                    # Lisans
├── README.md                  # Bu dosya
├── build-tools/               # .exe oluşturma araçları
│   ├── build_exe.py          # Ana build scripti
│   ├── convert_logo_to_icon.py  # Logo dönüştürücü
│   ├── BUILD_INSTRUCTIONS.md # Detaylı kılavuz
│   └── README.md             # Build tools dökümantasyonu
├── games/                     # Oyun modülleri
│   ├── tombala_game.py       # Tombala (Bingo) oyunu
│   ├── kkm_game.py           # Kiss-Kill-Marry oyunu
│   ├── trustnoone_game.py    # Trust No One (sosyal dedüksiyon)
│   └── README.md             # Oyun dökümantasyonu
└── lan/                       # LAN server altyapısı
    ├── lan_server.py         # WebSocket sunucu
    └── README.md             # Sunucu dökümantasyonu
```

## ✨ Özellikler

- **Tek Tıkla Başlatma**: Windows .exe desteği - Python yüklemeye gerek yok!
- **Modüler Oyun Sistemi**: Yeni oyunlar kolayca eklenebilir
- **LAN Desteği**: Aynı ağdaki tüm cihazlardan oynanabilir
- **WebSocket Tabanlı**: Gerçek zamanlı çok oyunculu deneyim
- **Web Arayüzü**: Tarayıcıdan oynanır, kurulum gerektirmez
- **Cross-Platform**: Windows, macOS, Linux desteği
- **Özelleştirilebilir**: `character.txt` ile karakter listesini düzenleyin

## 📋 Gereksinimler

### .EXE Dosyası Kullanıyorsanız
- ❌ Hiçbir şey gerekmez! Sadece çift tıklayın.

### Python ile Çalıştırıyorsanız
- Python 3.8+ (Windows, macOS veya Linux)

## 📦 Kurulum

### Windows - .EXE Kullanıcıları (Python Gerektirmez!)

1. **`build.bat`** dosyasına çift tıklayın
2. .exe oluşturulmasını bekleyin
3. **`dist\K-LAN.exe`** dosyası oluşacak
4. Bu dosyayı çift tıklayın - hazır!

**Veya:** Hazır .exe dosyasını edinin ve çift tıklayın.

Detaylı bilgi için: [build-tools/BUILD_INSTRUCTIONS.md](build-tools/BUILD_INSTRUCTIONS.md)

### Python ile Kullanım

#### Windows PowerShell

```powershell
# Proje klasörüne girin
cd "C:\Users\polis\Desktop\K-LAN"

# Gerekli bağımlılıkları yükleyin
pip install -r requirements.txt

# Hızlı başlatma
.\K-LAN.bat

# Veya manuel
python main.py
```

#### Linux/macOS

```bash
# Proje klasörüne girin
cd ~/Desktop/K-LAN

# Gerekli bağımlılıkları yükleyin
pip install -r requirements.txt

# Ana menüyü başlatın
python3 main.py
```

## 🎯 Kullanım

### 🖱️ Yöntem 1: Tek Tıklama (ÖNERİLEN)

**Windows .exe ile:**
- **K-LAN.exe** dosyasına çift tıklayın

**Python .bat ile:**
- **K-LAN.bat** dosyasına çift tıklayın

### ⌨️ Yöntem 2: Komut Satırı

**Ana Menüden Oyun Başlatma:**
```powershell
python main.py
```

Ana menü açılır ve mevcut oyunları listeler. Oynamak istediğiniz oyunu seçin.

**Doğrudan Oyun Başlatma:**
```powershell
# KKM oyunu
python games/kkm_game.py

# Tombala oyunu
python games/tombala_game.py

# Trust No One
python games/trustnoone_game.py
```

### 3️⃣ Oyuna Katılma

1. Sunucu başladığında terminalde görünen LAN adresini kopyalayın
2. Aynı ağdaki diğer cihazlardan tarayıcı ile bu adrese gidin
3. İsminizi yazıp "Odaya Katıl" butonuna tıklayın
4. Host "Yeni Tur Başlat" dediğinde oyun başlar!

## 🎮 Mevcut Oyunlar

### 🕵️ Trust No One

Among Us tarzı sosyal dedüksiyon oyunu! Crew üyeleri görevleri tamamlamaya çalışırken, Saboteur onları sabote etmeye çalışır.

**Rol Sistemi:**
- **Crew (Mürettebat)**: Görevleri tamamla, Saboteur'ü bul
- **Saboteur**: Görevleri sabote et, yakalanma!

**Nasıl Oynanır:**
1. Minimum 3 oyuncu gerekli
2. Rastgele bir oyuncu Saboteur rolünü alır
3. Her turda görev kartları gösterilir
4. Oyuncular "DO" veya "SKIP" seçebilir (Saboteur "SABOTAGE" yapabilir)
5. Sabotaj olursa ilerleme azalır
6. Her turdan sonra oylama - kim şüpheli?
7. Saboteur'ü bulun veya görevleri tamamlayın!

**Kazanma Koşulları:**
- **💋 Crew Kazanır**: İlerleme %100'e ulaşırsa VEYA Saboteur elenir
- **Saboteur Kazanır**: Crew sayısı 1 veya daha aza inerse

### 🎲 Tombala (Bingo)

Klasik Türk tombala oyunu! Her oyuncu 3 satır, 9 sütunluk bir kart alır. Sayılar çekilir ve kartınızdaki sayıları işaretlersiniz.

**Kazanma Koşulları:**
- **1. Çinko**: İlk satırı tamamlayan (10 puan)
- **2. Çinko**: İki satırı tamamlayan (20 puan)  
- **Tombala**: Tüm kartı tamamlayan (50 puan)

**Nasıl Oynanır:**
1. Oyuna katılın
2. "Oyunu Başlat" butonuna tıklayın
3. Otomatik olarak sayılar çekilmeye başlar (3 saniyede bir)
4. Kartınızda çekilen sayılar yeşil ile işaretlenir
5. Bir satırı tamamladığınızda "1. Çinko!" butonuna tıklayın
6. İki satırı tamamladığınızda "2. Çinko!" butonuna tıklayın
7. Tüm kartı tamamladığınızda "TOMBALA!" butonuna tıklayın

### Kiss · Kill · Marry (Valorant Edition)

3 karakter arasından birini öpmek, birini öldürmek, biriyle evlenmek için seçim yapın. Diğer oyuncularla aynı seçimleri yaparsanız puan kazanırsınız!

**Puan Sistemi:**
- Aynı Kiss seçimi: 1 puan
- Aynı Kill seçimi: 1 puan  
- Aynı Marry seçimi: 2 puan

## 🔧 Yeni Oyun Ekleme

1. `games/` klasöründe `yeni_oyun_game.py` dosyası oluşturun
2. `lan.lan_server` modülünü import edin
3. Oyun mantığınızı yazın ve `main()` fonksiyonu ekleyin
4. Ana menüden otomatik olarak görünecektir!

Örnek şablon:

```python
# games/yeni_oyun_game.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lan.lan_server import create_app, run_server

# Oyun HTML'i
INDEX_HTML = """<!doctype html>
<html>...</html>
"""

def main():
    app = create_app(INDEX_HTML)
    run_server(app, port=8080)

if __name__ == "__main__":
    main()
```

## 🛠️ Sorun Giderme

**Bağlantı problemi yaşıyorsanız:**

1. Windows Güvenlik Duvarı'nı kontrol edin
2. Port 8080'in açık olduğundan emin olun
3. Aynı WiFi ağına bağlı olduğunuzdan emin olun

**Karakter listesini değiştirmek için:**

`character.txt` dosyasını düzenleyin. Her satıra bir karakter adı yazın.

## 🤝 Katkıda Bulunma

Yeni oyun fikirleri ve geliştirmeler için pull request göndermekten çekinmeyin!

1. Bir fork oluşturun
2. Yeni bir dal (branch) açın: `git checkout -b feature/yenilik`
3. Değişikliklerinizi yapın ve commit atın
4. Bir Pull Request (PR) oluşturun

## 📝 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

---

**İyi oyunlar! 🎮✨**

