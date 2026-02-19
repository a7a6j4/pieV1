from __future__ import print_function
import time
from pprint import pprint
import requests
from schemas import OtpType, opr
from config import settings


api_key = settings.BREVO_API_KEY

async def sendOtpEmail(otp: str, email: str, name: str, otpType: OtpType):

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
                "name": name
            }
        ],
        "subject": f"{opr[otpType.value].get('subject')}",
        "templateId":11,
        "params": {
            "otp": otp,
            "minutes": int(opr[otpType.value].get('seconds') / 60)
        }
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
        "htmlContent": data.get('htmlContent', '')
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code