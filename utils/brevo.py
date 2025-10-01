from __future__ import print_function
import time
from pprint import pprint
import os
from dotenv import load_dotenv
from pathlib import Path
import requests


dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)
api_key = os.getenv('BREVO_API_KEY')

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