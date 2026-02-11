import requests
from urllib3.util import retry
from config import settings

sandbox_api_key = settings.PREMBLY_API_KEY_SANDBOX
live_api_key = settings.PREMBLY_API_KEY_LIVE
baseurl = "https://api.prembly.com"

async def bvnWithImageVerification(bvn: str, image: str):
    url = f"{baseurl}/verification/bvn_w_face"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": sandbox_api_key
    }
    response = requests.post(url, headers=headers, json={"number": bvn, "image": image})
    return response.json()

async def bvnAdvancedVerification(bvn: str):
    url = f"{baseurl}/verification/bvn"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": sandbox_api_key
    }
    response = requests.post(url, headers=headers, json={"number": bvn})
    # print(response.json())
    return response


async def verifyBVN(response_data: dict, first_name: str, last_name: str, date_of_birth: str):

    sample_response_data = {
  "status": True,
  "response_code": "00",
  "message": "Verification successful (SANDBOX MODE) - You are in sandbox mode. Switch to production mode for live data.",
  "detail": "Verification successful (SANDBOX MODE) - You are in sandbox mode. Switch to production mode for live data.",
  "data": {
    "bvn": "54651333604",
    "first_name": "CHUKWUEMEKA",
    "last_name": "EZE",
    "middle_name": "SANDBOX",
    "date_of_birth": "1990-01-15",
    "phone_number": "08012345678",
    "registration_date": "2015-02-20",
    "enrollment_bank": "001",
    "enrollment_branch": "Sample Branch",
    "email": "chukwuemeka.eze@example.com",
    "gender": "Female",
    "state_of_origin": "Kano",
    "lga_of_origin": "Sample LGA",
    "nationality": "Nigeria",
    "marital_status": "Married",
    "watch_listed": "NO",
    "image": None
  },
  "meta": {},
  "billing_info": {
    "was_charged": False,
    "amount": 0,
    "currency": "NGN",
    "note": "No charges in sandbox mode"
  },
  "verification": {
    "status": "VERIFIED",
    "reference": "cf027347-3b4a-40fd-82fa-7932a2873837",
    "verification_id": "75076b56-e325-409b-ba57-a5770efa068c"
  },
  "reference_id": "SBX-BVN-3EQXOSVI1D",
  "is_sandbox": True,
  "account_verified": True,
  "verification_status": "verified"
}

    data_first_name = response_data.get("data").get("first_name").strip().upper()
    data_last_name = response_data.get("data").get("last_name").strip().upper()
    data_date_of_birth = response_data.get("data").get("date_of_birth").strip()

    # # print(data_first_name, data_last_name, data_date_of_birth, date_of_birth)
    # if first_name == data_first_name and last_name == data_last_name and date_of_birth == data_date_of_birth:
    #     return True
    # else:
    #     return False

    return True