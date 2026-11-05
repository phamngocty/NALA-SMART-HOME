import urllib.request, zipfile, io, sys
sys.stdout.reconfigure(encoding='utf-8')
url = 'https://www.lcdwiki.com/res/ES3C28P/2.8inch_IPS_ESP32-S3_ES3C28P_ES3N28P_Quick_Start.zip'
print('Downloading quick start zip...')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
data = urllib.request.urlopen(req, timeout=30).read()
print('Downloaded size:', len(data))
zf = zipfile.ZipFile(io.BytesIO(data))
for name in zf.namelist():
    print(name)
