from __future__ import print_function
import time
import brevo_python
from brevo_python.rest import ApiException
from pprint import pprint
import os
from dotenv import load_dotenv
from pathlib import Path
import requests


dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)
api_key = os.getenv('BREVO_API_KEY')

# Configure API key authorization: api-key
configuration = brevo_python.Configuration()
configuration.api_key['api-key'] = api_key
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
configuration.api_key_prefix['api-key'] = 'Bearer'
# Configure API key authorization: partner-key
configuration = brevo_python.Configuration()
configuration.api_key['partner-key'] = api_key
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
configuration.api_key_prefix['partner-key'] = 'Bearer'

# create an instance of the API class

async def send_email(email: str, subject: str, otp: str):

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    data = {
        "sender": {
            "name": "Pie Wealth",
            "email": "hello@usepie.ng"
        },
        "to": [
            {
                "email": email,
                "name": "John Doe"
            }
        ],
        "subject": subject,
        "htmlContent": f"<html><head></head><body><p>Hello,</p> Your signup OTP is {otp}.</p></body></html>"
    }

    response = requests.post(url, headers=headers, json=data)
    return response
    # Check the response

async def sendEmail(email: str, subject: str, data: dict):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    data = {
        "sender": {
            "name": "Pie Wealth",
            "email": "hello@usepie.ng"
        },
        "to": [
            {
                "email": email,
                "name": data.get('name','John Doe')
            }
        ],
        "subject": subject,
        "htmlContent": data.get('htmlContent', 'empty')
    }
    response = requests.post(url, headers=headers, json=data)
    return response