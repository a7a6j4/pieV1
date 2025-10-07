import requests
from alpaca.broker import BrokerClient
from config import settings


Broker_API_Key = settings.BROKER_API_KEY
Broker_Secret_Key = settings.BROKER_SECRET_KEY

broker_client = BrokerClient(
                    api_key=Broker_API_Key,
                    secret_key=Broker_Secret_Key,
                    sandbox=True,
                )   