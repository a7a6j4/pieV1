import requests
import schemas
from config import settings

anchor_api_key_sandbox = settings.ANCHOR_API_KEY_SANDBOX
anchor_api_key_live = settings.ANCHOR_API_KEY_LIVE

url_sandbox = "https://api.sandbox.getanchor.co/api/v1"
url_live = "https://api.anchor.co/api/v1"

anchor_api_server_error_codes = [500, 502, 503, 504]
anchor_api_client_error_codes = [400, 401, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 421, 422, 423, 424, 426, 428, 429, 431, 451]
anchor_api_success_codes = [200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255]

async def createAnchorCustomer(
  args: dict
  ):

  payload = { "data": { "attributes": {
            "fullName": {
                "firstName": args.get("firstName"),
                "lastName": args.get("lastName"),
                "maidenName": args.get("maidenName"),
                "middleName": args.get("middleName")
            },
            "address": {
                "country": "NG",
                "state": args.get("state").value,
                "addressLine_1": args.get("addressLine_1"),
                "addressLine_2": args.get("addressLine_1"),
                "city": args.get("city"),
                "postalCode": args.get("postalCode")
            },
            "identificationLevel2": {
                "dateOfBirth": args.get("dateOfBirth").isoformat(),
                "gender": args.get("gender").value,
                "bvn": args.get("bvn"),
                "selfieImage": args.get("selfieImage")
            },
            "identificationLevel3": {
                "idType": args.get("idType").value,
                "idNumber": args.get("idNumber"),
                "expiryDate": args.get("expiryDate").isoformat()
            },
            "email": args.get("email"),
            "phoneNumber": args.get("phoneNumber"),
            "isSoleProprietor": False
        },
        "type": "IndividualCustomer" } }
  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox if args.get("mode") == schemas.AnchorMode.SANDBOX else anchor_api_key_live
}

  response = requests.post(f"{url_sandbox if args.get("mode") == schemas.AnchorMode.SANDBOX else url_live}/customers", json=payload, headers=headers)
  return response.json()

async def getAnchorCustomer(anchor_customer_id: str, mode: schemas.AnchorMode):

  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX else anchor_api_key_live 
  }

  response = requests.get(f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX else url_live}/customers/{anchor_customer_id}", headers=headers)
  return response

async def validateAnchoTier2Kyc(anchor_customer_id: str, mode: str):
  request_url = f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX.value else url_live}/customers/{anchor_customer_id}/verification/individual"
  payload = { "data": {
  "attributes": { "level": "TIER_2" },
  "type": "Verification"
  } }
  headers = {
      "accept": "application/json",
      "content-type": "application/json",
      "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX.value else anchor_api_key_live
  }
  
  response = requests.post(request_url, json=payload, headers=headers)
  return response

async def validateAnchorTier3Kyc(anchor_customer_id: str, mode: str):
  request_url = f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX.value else url_live}/customers/{anchor_customer_id}/verification/individual"
  payload = { "data": {
  "attributes": { "level": "TIER_3" },
  "type": "Verification"
  } }
  headers = {
      "accept": "application/json",
      "content-type": "application/json",
      "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX.value else anchor_api_key_live
  }
  response = requests.post(request_url, json=payload, headers=headers)
  return response

async def uploadAnchorCustomerDocument(anchor_customer_id: str, document_id: str, file_data, mode: str):
  request_url = f"{url_sandbox if mode == schemas.AnchorMode.SANDBOX.value else url_live}/documents/upload-document/{anchor_customer_id}/{document_id}"

  headers = {
    "accept": "application/json",
    "content-type": "multipart/form-data",
    "x-anchor-key": anchor_api_key_sandbox if mode == schemas.AnchorMode.SANDBOX.value else anchor_api_key_live
  }

  response = requests.post(request_url, files=file_data, headers=headers)
  return response

async def createAnchorDepositAccount(anchor_customer_id: str):

  request_url = f"{url_sandbox}/accounts" 

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
    "x-anchor-key": anchor_api_key_sandbox
}

  response = requests.post(request_url, json=payload, headers=headers)
  return response

async def getAnchorDepositAccount(anchor_customer_id: str):
  request_url = f"{url_sandbox}/accounts"
  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox
  }
  response = requests.get(request_url, headers=headers)
  return response

async def getAnchorBalance(account_number: str):
  
  request_url = f"{url_sandbox}/accounts/balance/{account_number}"
  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox
  }
  response = requests.get(request_url, headers=headers)
  return response