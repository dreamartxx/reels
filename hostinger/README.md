# Hostinger Business kurulumu

Business planında PHP/MySQL barınır; Python, Whisper ve FFmpeg bilgisayardaki işçide çalışır. Bilgisayarın açık, internete bağlı ve `Bulut Motorunu Aç.command` / `.cmd` dosyasının çalışıyor olması gerekir. İşçi yalnızca dışarıya HTTPS bağlantısı kurar; port açma, tünel veya yönlendirici ayarı gerekmez.

## Sunucu yerleşimi

```text
domain-root/
  public_html/       # build/hostinger/public_html içeriği
    index.html
    assets/
    fonts/
    api/index.php
    .htaccess
    .user.ini
  reels-private/     # web kökünün DIŞINDA
    config.php       # GitHub'a ASLA eklenmez
    schema.sql
    storage/        # özgün ses, PNG, MP4, SRT, JSON
```

1. hPanel'de hedef site için MySQL veritabanı ve yalnızca o veritabanını kullanan kullanıcı oluşturun.
2. Yerelde frontend'i derleyin: `npm ci --prefix frontend && npm run build --prefix frontend`.
3. `.venv/bin/python scripts/package_hostinger.py` ile `build/reels-hostinger.zip` oluşturun.
4. `.venv/bin/python scripts/configure_cloud.py --url https://SITE --database DATABASE --user USER` çalıştırın. MySQL parolası terminalde gizli alınır. PHP CLI, parola özetini oluşturmak için gerekir.
5. Paketteki `public_html/` içeriğini hedef sitenin `public_html/` klasörüne; `schema.sql` ve `.private/config.php` dosyasını kardeş `reels-private/` klasörüne yükleyin. `config.php` veya `worker.json` dosyasını herkese açık klasöre koymayın.
6. HTTPS sitede oturum açın. Rastgele oluşturulan stüdyo parolası yalnızca yerel `.private/studio-access.txt` içindedir. MySQL tabloları ilk başarılı bağlantıda `schema.sql` ile oluşturulur.
7. `.venv/bin/python cloud/worker.py` başlatın. Motor tokeni `.private/worker.json` içindedir. Site üst kısmında “video motoru bağlı” görünmelidir.
8. Örnek MP3 yükleyin, gerçek metni girin, hizalayın ve önce 360×640 prova çıktısını deneyin; ardından final çıktıyı üretin.

`config.php` için `REELS_CONFIG` ortam değişkeniyle farklı bir özel dosya yolu belirtilebilir. Canlı ortam DSN'si mutlaka `mysql:` olmalıdır. `tests/run_cloud_integration.py` protokol testinde geçici SQLite kullanır; canlı MySQL ayrıca doğrulanmalıdır.

## Güvenlik ve iş yaşam döngüsü

- Tek sahipli, parola korumalı stüdyo. Parola PHP `password_hash` ile özetlenir; secure/HttpOnly/SameSite=Strict oturum çerezi kullanılır.
- Projeler, sesler, görseller ve çıktılar oturum veya işçi anahtarı olmadan indirilemez. Medya dosyaları web kökü dışındadır.
- Giriş denemeleri IP başına sınırlıdır. Yabancı Origin ile değişiklik istekleri reddedilir. API sorguları parametrelidir.
- İşçi anahtarı sunucuda SHA-256 özeti olarak tutulur. Anahtar hiçbir frontend dosyasına, GitHub'a veya URL sorgusuna yazılmaz.
- İşler MySQL'de kalıcıdır. Her işin kira anahtarı vardır; işçi 8 saniyede bir kalp atışı gönderir. Bağlantı koparsa 120 saniye sonra iş yeniden alınabilir; eski işçinin sonucu reddedilir.
- Site yenilense de devam eden iş yeniden gösterilir. Model indirme sırasında iptal gecikebilir. Hazır önizlemeler saklanır; tasarım değişince yeni önizleme işi oluşturulur.
- Sessizken tarayıcıda hazır sahnenin oynatımı devam eder; yeni ses analizi, hizalama, sahne ve MP4 üretimi bağlı motor gerektirir.
- İşçi durdurmak için Ctrl+C. Otomatik başlangıç kurulmaz; kullanıcı isterse ayrıca yapılandırılabilir.
- Yedek: MySQL veritabanı ile `reels-private/storage/` birlikte yedeklenir. Parola/anahtar değiştirme gerekiyorsa ilgili özel yapılandırma dosyaları birlikte güncellenir.

## VPS'e geçiş

PHP/MySQL katmanı aynı kalabilir; Python işçisi VPS üzerinde çalıştırılır. Böylece kişisel bilgisayar açık olmasa da işler üretilir. VPS satın alımı veya ücretli hizmet bu kurulumun parçası değildir.

### Mac'te otomatik video motoru

`Bulut Motorunu Aç.command` artık motoru macOS kullanıcı servisi olarak kurar ve arka planda başlatır. Terminali açık tutmanız gerekmez. Mac oturum açılışında motor yeniden başlar; beklenmedik kapanmadan sonra macOS tekrar başlatır. Bilgisayar uyurken veya kapalıyken işler sırada bekler. İnternet geri geldiğinde motor tekrar bağlanır.

Durum: `.venv/bin/python scripts/worker_service.py status`

Otomatik başlatmayı kapatmak için: `.venv/bin/python scripts/worker_service.py uninstall` (devam eden işlemi durdurur; proje/çıktıları silmez).

Servis tanımı `~/Library/LaunchAgents/com.reels.typography.worker.plist`, günlükler proje içindeki `.private/logs/` klasöründedir. Parolalar ve motor anahtarı servise kopyalanmaz; mevcut özel yapılandırmadan okunur. macOS kullanıcı hesabıyla çalışır; yönetici yetkisi gerekmez.
