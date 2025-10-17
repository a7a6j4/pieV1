import requests
import schemas
from config import settings

anchor_api_key_sandbox = settings.ANCHOR_API_KEY_SANDBOX
anchor_api_key_live = settings.ANCHOR_API_KEY_LIVE

url_sandbox = "https://api.sandbox.getanchor.co/api/v1"
url_live = "https://api.anchor.co/api/v1"

async def createAnchorCustomer(
  data: dict, mode: schemas.AnchorMode
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
    "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX else anchor_api_key_live
}

  response = requests.post(f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX else url_live}/customers", json=payload, headers=headers)
  return response.json()

async def getAnchorCustomer(anchor_customer_id: str, mode: schemas.AnchorMode):

  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX else anchor_api_key_live 
  }

  response = requests.get(f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX else url_live}/customers/{anchor_customer_id}", headers=headers)
  return response

async def validateAnchoTier2Kyc(anchor_customer_id: str, mode: schemas.AnchorMode):
  request_url = f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX else url_live}/customers/{anchor_customer_id}/verification/individual"
  payload = { "data": {
  "attributes": { "level": "TIER_2" },
  "type": "Verification"
  } }
  headers = {
      "accept": "application/json",
      "content-type": "application/json",
      "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX else anchor_api_key_live
  }
  
  response = requests.post(request_url, json=payload, headers=headers)
  return response.json()

async def validateAnchorTier3Kyc(anchor_customer_id: str, mode: schemas.AnchorMode):
  request_url = f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX else url_live}/customers/{anchor_customer_id}/verification/individual"
  payload = { "data": {
  "attributes": { "level": "TIER_3" },
  "type": "Verification"
  } }
  headers = {
      "accept": "application/json",
      "content-type": "application/json",
      "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX else anchor_api_key_live
  }
  response = requests.post(request_url, json=payload, headers=headers)
  return response.json()

async def uploadAnchorCustomerDocument(anchor_customer_id: str, document_id: str, file_data, mode: schemas.AnchorMode):
  request_url = f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX else url_live}/documents/upload-document/{anchor_customer_id}/{document_id}"
  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX else anchor_api_key_live
  }

  response = requests.post(request_url, files=file_data, headers=headers)
  return response.json()

async def createAnchorDepositAccount(anchor_customer_id: str, mode: schemas.AnchorMode = schemas.AnchorMode.SANDBOX):

  request_url = f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX else url_live}/accounts" 

  payload = { "data": {
        "attributes": { "productName": "SAVINGS" },
        "relationships": { "customer": { "data": {
                    "id": anchor_customer_id,
                    "type": "IndividualCustomer"
                } } },
        "type": "DepositAccount"
    } }
  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX else anchor_api_key_live
}

  response = requests.post(request_url, json=payload, headers=headers)
  return response.json()


#   url = "https://api.sandbox.getanchor.co/api/v1/accounts"

# payload = { "data": {
#         "attributes": {
#             "customer": {
#                 "id": "17597958382113-anc_ind_cst",
#                 "type": "IndividualCustomer"
#             },
#             "currency": "NGN",
#             "productName": "sfdfsd"
#         },
#         "type": "ElectronicAccount"
#     } }
# headers = {
#     "accept": "application/json",
#     "content-type": "application/json",
#     "x-anchor-key": "hfVz5.1f836e3cf846c4fb0695e31cf2a4f2eff8869c878f950a65385658c5aca2e0834f064e545e355d852b734b0b6918e88dd0d2"
# }

# response = requests.post(url, json=payload, headers=headers)