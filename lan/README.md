# LAN Sunucusu

Bu klasör, tüm oyunların kullanabileceği temel LAN sunucu altyapısını içerir.

## İçindekiler

- `lan_server.py` - WebSocket tabanlı temel sunucu

## Kullanım

Oyun dosyalarınızda bu modülü import edin:

```python
from lan.lan_server import create_app, run_server, broadcast, build_payload
```

## Özellikler

- WebSocket bağlantı yönetimi
- Oyuncu kayıt/çıkış işlemleri
- Mesaj yayınlama (broadcast)
- Oyun durumu senkronizasyonu
