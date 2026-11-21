import urllib.request

resp = urllib.request.urlopen('http://192.168.1.114:8765/?v=v3.0.4', timeout=5)
html = resp.read().decode('utf-8', errors='ignore')
print('Status:', resp.status)
print('Has v3.0.4:', 'v3.0.4' in html)
print('Ends with </script></body></html>:', html.rstrip().endswith('</script>\n</body>\n</html>'))
print('Has active in openVoiceprintModal:', "modal.classList.add('active')" in html)
print('Has active removal in closeVoiceprintModal:', "modal.classList.remove('active')" in html)
