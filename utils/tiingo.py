import requests
import config
from fastapi import HTTPException, status

class Tiingo:
    def __init__(self):
        self.base_url = "https://api.tiingo.com/tiingo"
        self.api_key = config.settings.TIINGO_API_KEY

    async def getStockPrice(self, symbol: str):
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        url = f"{self.base_url}/daily/{symbol}/prices"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data[-1]["close"]
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get stock price for {symbol}: {response.status_code} {response.text}")

tiingo = Tiingo()