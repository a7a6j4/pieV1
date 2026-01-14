from config import settings
from datetime import datetime
import requests
from fastapi import HTTPException, status


base_url = "https://api.polygon.io"

async def getAssetPrice(ticker: str):
    url = f"{base_url}/v1/open-close/{ticker}/{datetime.now().strftime('%Y-%m-%d')}?adjusted=true&apiKey={settings.POLYGON_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data["close"]
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get price for {ticker}: {response.text}")