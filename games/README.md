# Oyunlar

Bu klasör, LAN üzerinden oynanabilen çok oyunculu oyunları içerir.

## Mevcut Oyunlar

### 🎲 Tombala (Bingo)
- **Dosya:** `tombala_game.py`
- **Açıklama:** Klasik Türk tombala oyunu - 3 satır, 9 sütunluk kartlarla
- **Başlatma:** `python games/tombala_game.py`
- **Oyuncu:** 2+ kişi

### 💋 Kiss · Kill · Marry (Valorant Edition)
- **Dosya:** `kkm_game.py`
- **Açıklama:** 3 karakter arasından seçim yapma oyunu
- **Başlatma:** `python games/kkm_game.py`
- **Oyuncu:** 2+ kişi
- **Özelleştirme:** `character.txt` dosyasını düzenleyerek karakter listesini değiştirebilirsiniz

### 🕵️ Trust No One
- **Dosya:** `trustnoone_game.py`
- **Açıklama:** Sosyal dedüksiyon oyunu - Saboteur'ü bul!
- **Başlatma:** `python games/trustnoone_game.py`
- **Oyuncu:** 3+ kişi (minimum)

## Yeni Oyun Ekleme

1. Bu klasörde `yeni_oyun_game.py` adında dosya oluşturun
2. Dosya adı `*_game.py` formatında olmalıdır
3. `main()` fonksiyonu eklemeyi unutmayın
4. Oyun otomatik olarak ana menüde görünecektir

## Şablon

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lan.lan_server import create_app, run_server

INDEX_HTML = """
<!doctype html>
<html>
  <head><title>Oyun Adı</title></head>
  <body>Oyun içeriği buraya</body>
</html>
"""

def main():
    print("🎮 Oyun Adı")
    app = create_app(INDEX_HTML)
    run_server(app, port=8080)

if __name__ == "__main__":
    main()
```
