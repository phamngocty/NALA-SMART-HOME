import urllib.request, re, sys
sys.stdout.reconfigure(encoding='utf-8')
url = 'http://www.lcdwiki.com/2.8inch_ESP32-S3_Display'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
for m in set(re.findall(r'https?://[^\s"\'<>]+(?:\.zip|\.rar)', html)):
    print(m)
