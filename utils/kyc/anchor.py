from typing import Optional
from config import settings
import requests
'''
BVN
dob
passport
identity type
identity expiry
id number
front image
back image
proof of address
proof image

create customer with tier 1 and tier 2 kyc
verify request in customer creation webhook
request tier 2 kyc 
verify tier 2 kyc
request tier 3 kyc
verify tier 3 kyc
send kyc documents to anchor
verify kyc documents in anchor
send kyc verification email to user
create deposit account with anchor
verify depposit account creation webhook
link anchor account to user

all kyc documents are stored until kyc is verified
identify missing or faulty kyc item

create kyc item table in db
kyc item status

'''

anchor_api_key_sandbox = settings.ANCHOR_API_KEY_SANDBOX
anchor_api_key_live = settings.ANCHOR_API_KEY_LIVE
anchor_url_sandbox = "https://api.sandbox.getanchor.co/api/v1"
anchor_url_live = "https://api.anchor.co/api/v1"

async def createAnchorCustomer(
    firstName: str, 
    lastName: str, 
    maidenName: str, 
    dateOfBirth: str, 
    gender: str, 
    bvn: str, 
    selfieImage: str, 
    idType: str, 
    idNumber: str, 
    email: str, 
    phoneNumber: str, 
    city: str, 
    addressLine_1: str, 
    state: str, 
    postalCode: str, 
    middleName: Optional[str] = None, 
    expiryDate: Optional[str] = None, 
    addressLine_2: Optional[str] = None):

    create_customer_payload = { 
        "data": 
            { "attributes": 
                { "fullName": 
                    { "firstName": firstName, "lastName": lastName, "maidenName": maidenName }, 
                    "address": { "country": "NG", "state": state, "addressLine_1": addressLine_1, "city": city, "postalCode": postalCode }, 
                    "identificationLevel2": { "dateOfBirth": dateOfBirth, "gender": gender, "bvn": bvn, "selfieImage": selfieImage }, 
                    "identificationLevel3": { "idType": idType, "idNumber": idNumber }, 
                    "email": email, "phoneNumber": phoneNumber }, 
                    "type": "IndividualCustomer" 
                } 
            } 
    
    if addressLine_2:
        create_customer_payload["data"]["attributes"]["address"]["addressLine_2"] = addressLine_2
    if middleName:
        create_customer_payload["data"]["attributes"]["fullName"]["middleName"] = middleName
    if expiryDate:
        create_customer_payload["data"]["attributes"]["identificationLevel3"]["expiryDate"] = expiryDate

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-anchor-key": anchor_api_key_sandbox
    }
    response = requests.post(f"{anchor_url_sandbox}/customers", json=create_customer_payload, headers=headers)
    return response

async def sendTierTwoKycRequest(anchor_customer_id: str):
    url = f"{anchor_url_sandbox}/customers/{anchor_customer_id}/verification/individual"

    payload = { "data": {
        "attributes": { "level": "TIER_2" },
        "type": "Verification"
    } }
    headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox
}
    response = requests.post(url, json=payload, headers=headers)
    return response


async def sendTierThreeKycRequest(anchor_customer_id: str):
    request_url = f"{anchor_url_sandbox}/customers/{anchor_customer_id}/verification/individual"

    payload = { "data": {
        "attributes": { "level": "TIER_3" },
        "type": "Verification"
    } }
    headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-anchor-key": anchor_api_key_sandbox
}
    response = requests.post(request_url, json=payload, headers=headers)
    return response


async def sendKycDocumentsToAnchor(anchor_customer_id: str, document_id: str, file: dict):
    request_url = f"{anchor_url_sandbox}/documents/upload-document/{anchor_customer_id}/{document_id}"
    files = { "fileData": (file["filename"], file["file_obj"], file["content_type"]) }
    headers = {
        "accept": "application/json",
        "x-anchor-key": anchor_api_key_sandbox
    }
    response = requests.post(request_url, files=files, headers=headers)
    return response

async def verifyKycDocumentsInAnchor(anchor_customer_id: str, mode: str):
    pass


async def verifyDepositAccountCreationWebhook(anchor_customer_id: str, mode: str):
    pass

async def linkAnchorAccountToUser(anchor_customer_id: str, mode: str):
    pass