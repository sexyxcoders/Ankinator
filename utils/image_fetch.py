import aiohttp
import asyncio

# Simple DuckDuckGo image search using unofficial API
DUCKDUCKGO_URL = "https://duckduckgo.com/i.js"

async def fetch_image_url(query: str) -> str:
    """
    Returns the first image URL from DuckDuckGo search results for the given query.
    """
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(DUCKDUCKGO_URL, params=params, headers=headers) as resp:
            if resp.status != 200:
                return None
            try:
                data = await resp.json()
                if "results" in data and len(data["results"]) > 0:
                    return data["results"][0]["image"]
            except Exception:
                return None
    return None

# ------------------------------
# Test function (optional)
# ------------------------------
if __name__ == "__main__":
    async def test():
        url = await fetch_image_url("Iron Man")
        print(url)

    asyncio.run(test())