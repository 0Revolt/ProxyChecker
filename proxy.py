import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import signal
import sys
from tqdm import tqdm
import os

class ProxyChecker:
    def __init__(self):
        self.working_proxies = []
        self.lock = threading.Lock()
        # Test için kullanılacak hedef site ve port
        self.test_host = "www.google.com"
        self.test_port = 80
        self.is_running = True
        self.checked_count = 0
        self.pbar = None
        
        # Ctrl+C sinyalini yakala
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        print("\nProgram durduruluyor... Lütfen bekleyin...")
        self.is_running = False
        self.save_working_proxies()
        if self.pbar:
            self.pbar.close()
        sys.exit(0)
        
    def save_working_proxies(self):
        with open('work.txt', 'w') as f:
            for proxy in self.working_proxies:
                f.write(proxy + '\n')
        print(f"\nÇalışan {len(self.working_proxies)} proxy work.txt dosyasına kaydedildi.")
    
    def update_progress(self):
        with self.lock:
            self.checked_count += 1
            self.pbar.update(1)
            # İstatistikleri güncelle
            self.pbar.set_postfix({
                'Çalışan': len(self.working_proxies),
                'Başarı Oranı': f'{(len(self.working_proxies) / self.checked_count * 100):.1f}%' if self.checked_count > 0 else '0%'
            })
    
    def check_proxy(self, proxy_ip, proxy_port):
        if not self.is_running:
            return
            
        try:
            # SOCKS4 bağlantısı oluştur
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # Timeout'u 5 saniyeye düşürdük
            
            # Proxy'ye bağlan
            sock.connect((proxy_ip, proxy_port))
            
            # SOCKS4 protokol başlığı
            packet = b"\x04\x01"  # SOCKS4 versiyonu ve CONNECT komutu
            packet += self.test_port.to_bytes(2, 'big')  # Port numarası
            
            # Hedef IP'yi dönüştür
            target_ip = socket.gethostbyname(self.test_host)
            packet += socket.inet_aton(target_ip)  # Hedef IP
            
            packet += b"\x00"  # Kullanıcı ID (boş)
            
            # Proxy'ye SOCKS4 isteği gönder
            sock.send(packet)
            
            # Yanıtı al
            response = sock.recv(8)
            
            if response[1] == 0x5A:  # Başarılı yanıt kodu
                with self.lock:
                    self.working_proxies.append(f"{proxy_ip}:{proxy_port}")
                    # Her çalışan proxy bulunduğunda dosyaya ekle
                    with open('work.txt', 'a') as f:
                        f.write(f"{proxy_ip}:{proxy_port}\n")
                print(f"[+] Çalışan proxy bulundu: {proxy_ip}:{proxy_port}")
                
            sock.close()
            
        except Exception as e:
            pass  # Hata mesajlarını göstermeyi kaldırdık
        finally:
            self.update_progress()
    
    def check_proxies_from_file(self, filename="proxy.txt", max_threads=200):
        try:
            with open(filename, 'r') as f:
                proxies = [x.strip() for x in f.readlines() if ':' in x.strip()]
            
            total_proxies = len(proxies)
            if total_proxies == 0:
                print("Geçerli proxy bulunamadı!")
                return
                
            # Terminal ekranını temizle
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Önceki work.txt dosyasını temizle
            open('work.txt', 'w').close()
            
            print(f"🚀 Proxy Checker Başlatılıyor...")
            print(f"📊 Toplam Test Edilecek Proxy: {total_proxies}")
            print("⚡ İşlem başlıyor...\n")
            
            # İlerleme çubuğunu başlat
            self.pbar = tqdm(
                total=total_proxies,
                desc="Kontrol Ediliyor",
                unit="proxy",
                ncols=80,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}{postfix}]'
            )
            
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = []
                for proxy in proxies:
                    if not self.is_running:
                        break
                        
                    try:
                        ip, port = proxy.split(':')
                        port = int(port)
                        futures.append(executor.submit(self.check_proxy, ip, port))
                    except ValueError:
                        self.update_progress()
                        continue
                
                for future in futures:
                    if self.is_running:
                        future.result()
            
            self.pbar.close()
            
            if self.is_running:
                print("\n✅ Test tamamlandı!")
                print(f"📊 Sonuçlar:")
                print(f"   • Toplam Test Edilen: {self.checked_count}")
                print(f"   • Çalışan Proxy: {len(self.working_proxies)}")
                print(f"   • Başarı Oranı: {(len(self.working_proxies) / self.checked_count * 100):.1f}%")
                print("\n💾 Çalışan proxyler 'work.txt' dosyasına kaydedildi.")
            
        except FileNotFoundError:
            print("❌ proxy.txt dosyası bulunamadı!")

if __name__ == "__main__":
    checker = ProxyChecker()
    checker.check_proxies_from_file()
