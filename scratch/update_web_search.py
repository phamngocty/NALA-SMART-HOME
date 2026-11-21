import re

with open('server_nas_hub/app/extension_mcp_service.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_web_search = '''    async def web_search(self, query: str) -> str:
        """Tìm kiếm thông tin thời gian thực qua DuckDuckGo HTML Lite và Wikipedia tiếng Việt."""
        q = (query or "").strip()
        if not q:
            return "Không có từ khóa tìm kiếm."

        # 1. Thử DuckDuckGo Instant Answer API
        try:
            ddg_api = f"https://api.duckduckgo.com/?q={urllib.parse.quote(q)}&format=json&no_html=1&skip_disambig=1"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(ddg_api, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if resp.status_code == 200:
                    data = resp.json()
                    abstract = data.get("AbstractText", "").strip()
                    if abstract:
                        return f"[Kết quả tìm kiếm]: {abstract}"
        except Exception as e:
            logger.debug("[Extension] DDG Instant Answer not available: %s", e)

        # 2. Thử DuckDuckGo HTML Lite
        try:
            ddg_html = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                resp = await client.get(ddg_html, headers=headers)
                if resp.status_code == 200:
                    snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                    if snippets:
                        cleaned = []
                        for s in snippets[:3]:
                            clean_text = re.sub(r'<[^>]+>', '', s).strip()
                            if clean_text:
                                cleaned.append(clean_text)
                        if cleaned:
                            return "[Kết quả tìm kiếm]: " + " ".join(cleaned)
        except Exception as e:
            logger.debug("[Extension] DDG HTML fetch error: %s", e)

        # 3. Fallback: Wikipedia Vietnamese Summary
        try:
            wiki_url = f"https://vi.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(q)}"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(wiki_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    extract = data.get("extract", "").strip()
                    if extract:
                        return f"[Thông tin bách khoa]: {extract}"
        except Exception as e:
            logger.debug("[Extension] Wikipedia error: %s", e)

        return f"Dạ, em đã tìm kiếm về '{q}' nhưng chưa có dữ liệu tóm tắt phù hợp."'''

new_web_search = '''    async def web_search(self, query: str) -> str:
        """Tìm kiếm thông tin thời gian thực qua Google News RSS, Wikipedia Tiếng Việt và DuckDuckGo (100% Miễn phí)."""
        import xml.etree.ElementTree as ET
        q = (query or "").strip()
        if not q:
            return "Không có từ khóa tìm kiếm."

        results = []

        # 1. Tra cứu tin tức thời gian thực, giá cả, sự kiện mới nhất qua Google News VN RSS
        try:
            rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=vi&gl=VN&ceid=VN:vi"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(rss_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    items = root.findall(".//item")
                    if items:
                        for it in items[:3]:
                            t_node = it.find("title")
                            if t_node is not None and t_node.text:
                                results.append(t_node.text.strip())
        except Exception as e:
            logger.debug("[Extension] Google News RSS search error: %s", e)

        # 2. Tra cứu bách khoa Wikipedia Tiếng Việt
        try:
            wiki_search_url = f"https://vi.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&utf8=&format=json"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(wiki_search_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    search_items = data.get("query", {}).get("search", [])
                    if search_items:
                        top = search_items[0]
                        title = top.get("title", "")
                        snippet = re.sub(r'<[^>]+>', '', top.get("snippet", "")).strip()
                        if snippet:
                            results.append(f"{title}: {snippet}")
        except Exception as e:
            logger.debug("[Extension] Wikipedia search error: %s", e)

        # 3. Thử DuckDuckGo Instant Answer
        if not results:
            try:
                ddg_api = f"https://api.duckduckgo.com/?q={urllib.parse.quote(q)}&format=json&no_html=1&skip_disambig=1"
                async with httpx.AsyncClient(timeout=3.5) as client:
                    resp = await client.get(ddg_api, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    if resp.status_code == 200:
                        data = resp.json()
                        abstract = data.get("AbstractText", "").strip()
                        if abstract:
                            results.append(abstract)
            except Exception as e:
                logger.debug("[Extension] DDG error: %s", e)

        if results:
            return "[Thông tin thời gian thực]: " + " | ".join(results)

        return f"Dạ, em đã tìm kiếm về '{q}' nhưng chưa có dữ liệu tóm tắt phù hợp."'''

assert old_web_search in code, "old_web_search not found"
code = code.replace(old_web_search, new_web_search, 1)

with open('server_nas_hub/app/extension_mcp_service.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully updated web_search in extension_mcp_service.py!")
