import requests
import schemas
from config import settings

ANCHOR_API_KEY_SANDBOX = settings.ANCHOR_API_KEY_SANDBOX

url = "https://api.sandbox.getanchor.co/api/v1"

async def createAnchorCustomer(
  data: dict
  ):

  payload = { "data": { "attributes": {
            "fullName": {
                "firstName": data.get("firstName"),
                "lastName": data.get("lastName"),
                "maidenName": data.get("maidenName"),
                "middleName": data.get("middleName")
            },
            "address": {
                "country": "NG",
                "state": data.get("state"),
                "addressLine_1": data.get("addressLine_1"),
                "addressLine_2": data.get("addressLine_2"),
                "city": data.get("city"),
                "postalCode": "105101"
            },
            "identificationLevel2": {
                "dateOfBirth": data.get("dateOfBirth").isoformat(),
                "gender": data.get("gender"),
                "bvn": data.get("bvn"),
                "selfieImage": data.get("selfieImage")
            },
            "identificationLevel3": {
                "idType": data.get("idType"),
                "idNumber": data.get("idNumber"),
                "expiryDate": data.get("idExpirationDate").isoformat()
            },
            "email": data.get("email"),
            "phoneNumber": data.get("phoneNumber")  ,
            "isSoleProprietor": False
        },
        "type": "IndividualCustomer" } }
  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": ANCHOR_API_KEY_SANDBOX
}

  response = requests.post(f"{url}/customers", json=payload, headers=headers)
  return response

async def getAnchorCustomer(anchor_customer_id: str):

  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": ANCHOR_API_KEY_SANDBOX
  }

  response = requests.get(f"{url}/customers/{anchor_customer_id}", headers=headers)
  if response.status_code not in [200, 201]:
    raise Exception(response.text)
  return response.json()