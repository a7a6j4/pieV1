import requests
from alpaca.broker import BrokerClient

import os
from dotenv import load_dotenv

load_dotenv()

Broker_API_KEY = os.getenv("BROKER_API_KEY")
BROKER_SECRET_KEY = os.getenv("BROKER_SECRET_KEY")

BROKER_API_KEY = "api-key"
BROKER_SECRET_KEY = "secret-key"

broker_client = BrokerClient(
                    api_key=Broker_API_KEY,
                    secret_key=BROKER_SECRET_KEY,
                    sandbox=True,
                )