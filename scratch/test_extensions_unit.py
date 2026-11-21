import asyncio
import json
import urllib.request
import urllib.parse

async def test_weather():
    print("Testing Open-Meteo Weather API...")
    loc = "Hà Nội"
    # 1. Geocoding
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(loc)}&count=1&language=vi&format=json"
    req = urllib.request.Request(geo_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
    with urllib.request.urlopen(req, timeout=5) as res:
        geo_data = json.loads(res.read().decode())
    
    results = geo_data.get("results", [])
    if not results:
        print("Geocoding failed, using fallback coordinates")
        lat, lon = 21.0285, 105.8542
    else:
        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        print(f"Geocoded {loc} -> lat: {lat}, lon: {lon}")
    
    # 2. Weather
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
    req = urllib.request.Request(weather_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
    with urllib.request.urlopen(req, timeout=5) as res:
        w_data = json.loads(res.read().decode())
    
    cur = w_data.get("current", {})
    temp = cur.get("temperature_2m")
    humidity = cur.get("relative_humidity_2m")
    wind = cur.get("wind_speed_10m")
    print(f"Weather Success: Temp={temp}°C, Humidity={humidity}%, Wind={wind} km/h")

async def test_search():
    print("\nTesting Wikipedia Search Fallback...")
    query = "Hà Nội"
    wiki_url = f"https://vi.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
    req = urllib.request.Request(wiki_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
            title = data.get("title", "")
            extract = data.get("extract", "")
            print(f"Wikipedia Success: {title} -> {extract[:120]}...")
    except Exception as e:
        print("Wiki error:", e)

if __name__ == "__main__":
    asyncio.run(test_weather())
    asyncio.run(test_search())
