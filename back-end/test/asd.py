import aiohttp
import asyncio

async def fetch_request_info():
    proxy = "http://MTAbvU:k5AU8L@77.73.133.79:8000"
    h = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://www.instagram.com/",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "129477",
            "X-Requested-With": "XMLHttpRequest",
            "X-IG-WWW-Claim": "0",
        }
    async with aiohttp.ClientSession() as session:
        async with session.get("https://httpbin.org/anything", proxy=proxy, headers=h) as response:
            data = await response.json()
            print("IP адрес и информация о запросе, которую видит сервер:")
            print(data)

asyncio.run(fetch_request_info())
