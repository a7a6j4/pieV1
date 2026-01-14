from config import settings
from datetime import datetime
import requests
from fastapi import HTTPException, status

base_url = f"https://www.alphavantage.co"

async def getAssetPrice(ticker: str):
    url = f"{base_url}/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={settings.VANTAGE_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return float(data["Global Quote"]["05. price"])
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get price for {ticker}: {response.text}")