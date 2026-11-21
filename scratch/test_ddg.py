import urllib.request
import urllib.parse
import json
import re

def test_duckduckgo(query="giá vàng hôm nay"):
    print(f"Testing DuckDuckGo search for: {query}")
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
            abstract = data.get("AbstractText", "")
            heading = data.get("Heading", "")
            print("DDG Instant Answer:", heading, "->", abstract[:100] if abstract else "No instant answer")
    except Exception as e:
        print("DDG API error:", e)

    # Test DDG HTML Lite
    html_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req_html = urllib.request.Request(html_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    try:
        with urllib.request.urlopen(req_html, timeout=6) as res:
            html = res.read().decode('utf-8', errors='ignore')
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
            print(f"DDG HTML Snippets found: {len(snippets)}")
            for i, snip in enumerate(snippets[:2]):
                clean = re.sub(r'<[^>]+>', '', snip).strip()
                print(f" [{i+1}] {clean[:120]}...")
    except Exception as e:
        print("DDG HTML error:", e)

if __name__ == "__main__":
    test_duckduckgo()
