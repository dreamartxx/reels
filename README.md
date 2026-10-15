# Reels Typography Studio

Türkçe seslendirme ve **kullanıcının verdiği gerçek metinden** cümle cümle akan, 9:16 tipografik videolar üreten stüdyo. Yerel sürümde ses bilgisayarda kalır; Hostinger sürümünde sesler kullanıcının Hostinger hesabında saklanır. ElevenLabs API anahtarı gerekmez; ElevenLabs'ten indirdiğiniz MP3/WAV yeterlidir.

## Hostinger Business web sürümü

Web arayüzü, parola korumalı PHP API ve MySQL veritabanı Hostinger'da; Python/FFmpeg işçisi bilgisayarda çalışır. İşçi yeni işler için HTTPS üzerinden siteyi kontrol eder. Bilgisayar kapalıyken işler sırada bekler. Kurulum: [hostinger/README.md](hostinger/README.md).

Kaynak deposu: https://github.com/dreamartxx/reels

## Yerel sürümü açma

`Stüdyoyu Aç.command` dosyasını çalıştırın veya proje klasöründe:

```sh
.venv/bin/python start.py
```

Tarayıcı adresi: **http://127.0.0.1:8765**. Sunucu açık kalmalıdır. Durdurmak için terminalde Ctrl+C. Port doluysa `start.py --port 8766` kullanın. Uygulama yalnızca loopback adresine bağlanır; internete yayımlanmaz.

Örnek ses ve metin `examples/` içinde. Kişisel kayıtlar, model ağırlıkları, parolalar ve üretilen videolar GitHub deposuna dahil edilmez.

## Özellikler

- MP3/WAV doğrulama, süre/kanal/örnekleme hızı, gerçek ses dalga formu.
- stable-ts ile Türkçe **forced alignment**: `model.align(audio, supplied_text, language='tr')`. Metni üretmek/değiştirmek için transkripsiyon kullanılmaz.
- Noktalama ve kıta bazında bölme; tek satır sonu zorunlu cümle sınırı değildir. İstenirse her satır ayrı işlenebilir.
- Köşeli parantezli performans etiketleri hizalamadan ve görüntüden temizlenir.
- Kelime skorları ve sıfır/çok kısa/çok uzun kelime süreleri üzerinden kontrol işaretleri. Skorlar doğruluk garantisi değildir.
- Cümle başlangıç/bitişini sayısal düzenleme; dalga formunda taşıma ve kenarlardan boyutlandırma; 1–8× yakınlaştırma. Cümle seçicisinden çok kısa bloklara da ulaşılır.
- Kelimeye tıklayıp o konuma gitme ve kelime zamanını elle düzeltme. Cümlenin tamamını taşıyınca eski kelime zamanları temizlenir; yanlış kesinlik gösterilmez.
- Aynı anda en çok üç cümle; smoothstep dikey hareket; merkezde büyük aktif metin. Uzun duraklamalarda sahne sabittir. Geçiş süresi yaklaşan cümlenin başlangıcına göre kısaltılır.
- Dark Editorial, Cinematic Gold, Minimal Paper, Typewriter. Hepsi aynı dikey akışı kullanır.
- Yerel Lora, Manrope, IBM Plex Mono fontları; font boyutu, satır aralığı, üç renk, vurgu, konum, doku ve dört kenarın güvenli alan ayarları.
- Sesin gerçek `currentTime` değerini izleyen Canvas önizleme; play/pause, başa dönme, sürüklenebilir oynatma konumu, tam ekran.
- Final: **1080 × 1920, 30 FPS, H.264/yuv420p + AAC 192 kbps, faststart MP4**.
- Hızlı prova: 360 × 640, 30 FPS. SRT ve JSON zamanlama dosyaları her çıktıya eşlik eder.
- Otomatik yerel proje kaydı, yeniden açma, son kullanılan tasarım ayarları, ilerleme ve iptal. Açık sunucudaki işler sayfa yenilendiğinde yeniden izlenir.

## Kurulum — macOS

Önerilen ortam: Python **3.11 veya 3.12**, Node.js **22+**, FFmpeg/ffprobe. Python 3.14 için PyTorch/Whisper uyumluluğu kuruluma göre değişebilir; 3.11 ile test edilmiştir.

```sh
brew install python@3.11 node ffmpeg
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
python start.py
```

Bu çalışma alanında Python 3.11 proje içindeki `.python/` konumuna, kütüphaneler `.venv/` konumuna kuruludur. Bu sanal ortam başka bilgisayara kopyalanmaz; yeni bilgisayarda tekrar oluşturulur.

## Kurulum — Windows

Python 3.11, Node.js LTS ve FFmpeg kurun. `python`, `node`, `npm`, `ffmpeg` ve `ffprobe` PATH'te olmalı. FFmpeg için resmi indirme sayfasındaki Windows derlemelerini kullanabilirsiniz: https://ffmpeg.org/download.html

PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm.cmd ci
npm.cmd run build
cd ..
.venv\Scripts\python.exe start.py
```

Sonraki kullanımlarda `Studyoyu Ac.cmd` dosyasını açın. Windows kurulumu için taşınabilir kod sağlanmıştır; bu sürümün gerçek çalışma testi macOS üzerinde yapılmıştır.

## Modeller ve GPU

İlk hizalamada seçilen Whisper modeli `data/models/` içine indirilir; ilk kullanım internet ister. Model indirildikten sonra yükleme, hizalama, önizleme ve dışa aktarma çevrimdışıdır. Base yaklaşık 139 MiB, Small yaklaşık 461 MiB'dir. Türkçe şiirde daha güvenilir sonuç için Small seçilebilir; CPU üzerinde daha yavaştır. Model boyutu değişince bellekte tek model tutulur.

Varsayılan CPU'dur; Apple Silicon'da da CPU yolu test edilmiştir. Uyumlu NVIDIA GPU + CUDA PyTorch kurulumu olan Windows/Linux ortamlarında hizalama seçeneklerinden CUDA seçilir. CUDA yoksa uygulama açık hata verir. MPS ve donanımlı video kodlama bu sürümde kullanılmaz; FFmpeg `libx264` CPU ile çalışır. CUDA kurulumu: https://pytorch.org/get-started/locally/

## Kullanım

1. MP3/WAV dosyasını bırakın (100 MB / 10 dakika sınırı).
2. Seslendirmede gerçekten kullanılan şiiri yapıştırın. Etiketler kalabilir.
3. Cümle veya satır bölme biçimini, gerekirse modeli seçin; **Sesle hizala** deyin.
4. Önizlemeyi oynatın. Sarı cümleleri seçin; kelime skorlarını ve sürelerini dinleyerek kontrol edin. Kelimeye tıklayınca zaman düzenleyicisi açılır. Metin sesle birebir aynı değilse hizalamayı zorlamayın.
5. Şablon, font, renk ve kadrajı ayarlayın. Vurgu için Cümle panelindeki kutuyu kullanın.
6. **MP4 dışa aktar** deyin; MP4, SRT ve JSON bağlantılarından indirin. Prova kalitesi sağ panelin altından seçilir.

“Zamanları kendim düzenleyeceğim” seçeneği yalnızca **açıkça işaretli bir elle zamanlama taslağı** oluşturur. Kelime sayısıyla dağıtılan bu taslak, forced alignment sonucu gibi gösterilmez. Otomatik hizalama başarısız olunca sessizce bu yönteme geçilmez.

## Mimari

- `backend/main.py`: FastAPI, doğrulama, yerel proje deposu, sıra hâlinde çalışan hizalama/render işleri. Yerel API belgeleri `/docs` adresinde. Hostinger API aynı arayüz sözleşmesini PHP ile uygular.
- `backend/alignment.py`: stable-ts modeli, gerçek metinden kelime zamanları, kalite işaretleri.
- `backend/text.py`: etiket temizleme, şiir bölme, SRT.
- `backend/render.py`: tam çözünürlüklü Pillow metin sprite'ları, sabit film dokusu, güvenli yerleşim, animasyon, FFmpeg ham kare akışı.
- `frontend/src/Preview.tsx`: **backend'in ürettiği aynı metin görselleri ve arka plan** ile düşük çözünürlüklü Canvas. Tarayıcı font ölçümleri yüzünden satırlar değişmez.
- `frontend/src/motion.ts`: Python'daki hareket fonksiyonunun birebir karşılığı; çok sayıda zaman örneğinde eşitliği test edilir. Tarayıcı ve Pillow ölçekleme algoritmaları nedeniyle kenar yumuşatmada küçük farklar olabilir.
- `frontend/src/Timeline.tsx`: dalga formu, taşıma, yeniden boyutlandırma ve yakınlaştırma.
- `data/<proje-kimliği>/project.json`: proje, özgün ses, 16 kHz analiz kopyası, görseller ve çıktı klasörleri. `REELS_DATA_DIR` ile veri konumu değiştirilebilir. Projeler tarayıcı önbelleğine bağlı değildir; son proje/font tercihleri localStorage'dadır.

JSON içinde her cümlenin konuşma başlangıç/bitişi, sonraki duraklaması ve merkezde aktif kalma aralığı yer alır. İlk cümle ilk kareden itibaren gösterilir; son cümle ses bitene kadar kalır. SRT zamanları konuşma aralıklarıdır; SRT formatı dikey tipografi animasyonunu taşımaz.

Ses FFmpeg'e özgün dosyadan girer. Hizalama için oluşturulan mono 16 kHz kopya videoda kullanılmaz. Hız/ton değiştirilmez; MP4 uyumluluğu için AAC'ye yeniden kodlanır, dolayısıyla dosya bit düzeyinde aynı değildir.

## Geliştirme ve test

```sh
# API
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
# Ayrı terminal: Vite, /api isteklerini FastAPI'ye yönlendirir
cd frontend
npm run dev
# Tip denetimi + üretim derlemesi
npm run build
# Proje kökünde
.venv/bin/python -m pytest -q
```

Testler etiket/Türkçe ayrıştırma, SRT, geçersiz sesler, zaman çakışmaları, proje kalıcılığı, HTTP ses aralığı, fontların sığması, üç cümle sınırı, geçiş sürekliliği ve Python/TypeScript animasyon eşitliğini kapsar. Gerçek ElevenLabs dosyasıyla HTTP entegrasyon testi `tests/run_real_example.py` (sunucu açık olmalı; yeni bir örnek proje oluşturur). Kontrol sonuçları `examples/verification.json` dosyasında bulunur.

## Sınırlar ve hata durumları

- Forced alignment kusursuz değildir. Müzik, ses efektleri, fısıltı, sesle uyuşmayan metin ve kısa kelimeler elle düzeltme gerektirebilir. Herhangi bir model skoru garanti olarak sunulmaz.
- Şiir bölme sezgiseldir: kısaltmalar/üç noktalar tercihlerinize uymuyorsa “Her satır ayrı” seçeneğini kullanın ve metnin satırlarını düzenleyin.
- Çok uzun cümlelerde font otomatik küçülür. En küçük boyutta da sığmıyorsa açık hata verilir; cümleyi bölün. Sayfa fontu yüklenmesi ile video fontu birbirinden bağımsızdır.
- CPU render hızı bilgisayara bağlıdır; aynı anda tek ağır iş çalışır. En fazla üç iş sıraya alınır. İptal, model indirme/hesaplama işleminin güvenli kontrol noktasında gerçekleşir; anlık durmayabilir.
- Sunucu kapanırsa devam eden iş kesilir. Tamamlanmış projeler/çıktılar korunur; yarım video tamamlanmış çıktılar arasında listelenmez. Sonraki açılışta tekrar dışa aktarın.
- “Kaydedildi” yerel proje kaydını ifade eder. Yedek için uygulama kapalıyken `data/` klasörünü kopyalayın. Taşınabilir arşiv içe/dışa aktarma bu sürümde yoktur.
- Uygulama masaüstü düzenleme için tasarlanmıştır; dar ekranlarda paneller alt alta geçer.

## Lisanslar ve başvuru

Fontlar SIL Open Font License ile dağıtılır; özgün lisanslar `assets/fonts/*-LICENSE.txt` içindedir. Test şiiri kullanıcı tarafından sağlanmıştır; örnek sesin paylaşım haklarını kullanıcı belirler.

- stable-ts API: https://github.com/jianfch/stable-ts — `align`, `original_split`, `language`, kelime skorları.
- FastAPI dosya yükleme: https://fastapi.tiangolo.com/tutorial/request-files/
- FFmpeg: https://ffmpeg.org/documentation.html
