
from click import File
from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, status, Security
from fastapi.security import SecurityScopes
from sqlalchemy.orm import Session
from database import db
import model
from typing import Annotated, Optional, Union
from pydantic import BaseModel
import model
import schemas
from utils.kyc import prembly
from ..v1 import auth
from utils.minio_to_base64 import convert_minio_image_to_base64
from utils.assesment import runAssesment
from datetime import datetime, timedelta
from sqlalchemy import select, update, insert
from celery_app import linkAnchorAccountTask, uploadAnchorKycDocumentTask, createAnchorDepositAccountTask, validateAnchorTier2KycTask, validateAnchorTier3KycTask
from utils.minio import upload_file, get_file, download_s3_object_for_requests, validate_image_file
from utils.anchor import uploadAnchorCustomerDocument, createAnchorCustomer, anchor_api_server_error_codes, anchor_api_client_error_codes
from utils.kyc.anchor import createAnchorCustomer
import os

user = APIRouter(
    prefix="/user",
    tags=["user"],
)

@user.post("/signup", response_model=schemas.UserSchema, status_code=status.HTTP_201_CREATED)
async def signup(db: db, data = Security(auth.verifyOtp, scopes=[schemas.OtpType.SIGNUP.value])):

    user = db.execute(select(model.User).where(model.User.email == data.get('email'), model.User.is_active == True)).scalar_one_or_none()
    if user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    user = model.User(first_name=data.get('firstName'), last_name=data.get('lastName'), other_names=data.get('otherNames'), phone_number=data.get('phoneNumber'), email=data.get('email'), is_active=False)

    db.add(user)
    db.commit()
    db.refresh(user)

    # send welcome email - in a queue or send email for Brevo to send in the background
    # await utils.send_email(email=user.email, subject="Welcome to Your Pie", message="Welcome to Your Pie")

    return user

@user.post("/password", status_code=status.HTTP_201_CREATED)
async def set_password(db: db, password = Body(..., embed=True), payload = Security(auth.verifyAccessToken, scopes=[schemas.AccessLimit.PASSWORD.value])):

    user = db.execute(select(model.User).where(model.User.email == payload.get('username'))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has a password")

    user.password = auth.hashpass(password)
    user.is_active = True

    liquid = model.Portfolio(type=schemas.PortfolioType.LIQUID, duration=1, risk=1, userId=user.id)
    user.portfolios.append(liquid)

    db.add(user)
    db.commit()
    return {"message": "Password reset successfully"}

@user.post("/change-password", status_code=status.HTTP_201_CREATED, response_model=schemas.TokenResponse)
async def changePassword(db: db, user: Annotated[model.User, Depends(auth.getActiveUser)]):

    # send otp to user
    otp = await auth.sendOtp(data={'email': user.email}, type=schemas.OtpType.RESET_PASSWORD)
    return otp

@user.patch("/password", status_code=status.HTTP_201_CREATED)
async def updatePassword(db: db, new_password = Body(..., embed=True), token = Security(auth.verifyAccessToken, scopes=[schemas.OtpType.RESET_PASSWORD.value])):
    
    user = db.execute(update(model.User).where(model.User.email == token.get('email')).values(password=auth.hashpass(new_password)).returning(model.User)).scalar_one()
    db.commit()
    db.refresh(user)
    return user

# @user.get("/", response_model=schemas.UserOut)
@user.get("/")
async def getUser(
    db: db, 
    user_id: Annotated[Optional[int], Query(description="User_ID is required for admin to get user data")] = None,
    payload = Security(auth.readUser, scopes=["readUser"])):

    if payload.get("token") == "user":
        user = db.execute(select(model.User).where(model.User.email == payload.get("username"))).scalar_one_or_none()
    
    if payload.get("token") == "admin":
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User_id query param is required")
        user = db.get(model.User, user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@user.get("/all")
async def getAllUsers(db: db):
    return db.execute(select(model.User)).scalars().all()

@user.put("/", status_code=status.HTTP_200_OK)
async def update_user_password(password: str, db: db):
   user = db.get(model.User, user.id)
   if not user:
       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
   user.password = auth.hashpass(password.password)
   db.add(user)
   db.commit()
   return {"message": "user password updated successfully"}

@user.post("/risk", status_code=status.HTTP_201_CREATED)
async def completeRiskQuestionnaire(db: db, data: schemas.RiskProfileCreate, user: Annotated[model.User, Depends(auth.getActiveUser)]):
    
    if user.riskProfile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk profile already exists")

    capacity = await runAssesment(data)

    portfolio_types = map(lambda x: x.type, user.portfolios)
    emergency_portfolio_exists = schemas.PortfolioType.EMERGENCY not in list(portfolio_types)

    risk_profile = model.RiskProfile(**data.model_dump(exclude={"objective"}), objective=data.objective.name, user_id=user.id, capacity=capacity)
    
    if emergency_portfolio_exists:

        portfolio = model.Portfolio(userId=user.id, type=schemas.PortfolioType.EMERGENCY.name, risk=1, duration=1)
        portfolio.target = model.PortfolioTarget(amount=data.monthly_income * (3 if capacity.value == schemas.RiskLevel.HIGH.value else 6), currency=data.primary_income_currency)
        user.tier = 2
        user.riskProfile = risk_profile
        user.portfolios = user.portfolios
        db.add(portfolio)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emergency portfolio already exists")

    try:
        db.add(risk_profile)
        db.add(user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return user.riskProfile

from .portfolio import getPortfolioValue

@user.patch("/risk", response_model=schemas.RiskProfileSchema)
async def updateRiskProfile(db: db, data: schemas.RiskProfileUpdate, user: Annotated[model.User, Depends(getUser)]):
    risk_profile = user.riskProfile
    if risk_profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk profile does not exist, create one first")

    db.execute(update(model.RiskProfile).where(model.RiskProfile.user_id == user.id).values(**data.model_dump()))
    db.commit()
    return risk_profile

@user.patch("/password")
async def updatePassword(db: db, new_password = Body(..., embed=True), token = Depends(auth.otpScheme)):

    payload = await auth.decodeToken(token)
    email = payload.get('email')
    print(email)
    user = db.execute(select(model.User).where(model.User.email == email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password = auth.hashpass(new_password)
    db.commit()
    return {
        "message": "Password updated successfully"
    }

@user.get("/kyc/documents")
async def getKycDocument(db: db, user: Annotated[model.User, Depends(auth.getActiveUser)]):

    selfie_image = await get_file(bucket_name="user", object_name=f"{user.id}/kyc/{schemas.UserDocumentType.SELFIE.value}")
    front_id = await get_file(bucket_name="user", object_name=f"{user.id}/kyc/{schemas.UserDocumentType.FRONT_ID.value}")
    back_id = await get_file(bucket_name="user", object_name=f"{user.id}/kyc/{schemas.UserDocumentType.BACK_ID.value}")
    address_proof = await get_file(bucket_name="user", object_name=f"{user.id}/kyc/{schemas.UserDocumentType.PROOF_OF_ADDRESS.value}")

    return {
        "selfie_image": selfie_image,
        "front_id": front_id,
        "back_id": back_id,
        "address_proof": address_proof
    }

@user.post("/kyc/bvn", status_code=status.HTTP_201_CREATED)
async def verifyBvn(db: db, user: Annotated[model.User, Security(getUser, scopes=["createUser"])], data: schemas.KycBvnCreate):

    if user.bvn is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BVN already verified")

    bvn_exists = db.execute(select(model.User).where(model.User.bvn == data.bvn)).scalar_one_or_none()
    if bvn_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BVN already in use")

    try:
        selfie_image = await download_s3_object_for_requests(bucket_name="user", file_name=f"{user.id}/kyc/{schemas.UserDocumentType.SELFIE.value}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get selfie image: " + str(e))

    kyc_response = await prembly.bvnAdvancedVerification(data.bvn)
    if kyc_response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to verify BVN")

    verify_bvn = await prembly.verifyBVN(kyc_response.json(), user.first_name, user.last_name, data.dateOfBirth.isoformat())
    if not verify_bvn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BVN not verified")

    db.execute(update(model.User).where(model.User.id == user.id).values(bvn=data.bvn, dateOfBirth=data.dateOfBirth))
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    # db.refresh(user)
    return {"message": "BVN verified successfully"}

async def getUserBvn(db: db, user: Annotated[model.User, Security(getUser, scopes=["createUser"])]):
    if user.bvn is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BVN not verified")
    return user

async def validateKycDocumentFile(file: UploadFile):
    ALLOWED_FILE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"]
    ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    return await validate_image_file(file, allowed_file_types=ALLOWED_FILE_TYPES, allowed_extensions=ALLOWED_EXTENSIONS, max_file_size=MAX_FILE_SIZE)

@user.post("/kyc/document/{type}")
async def uploadKycDocuments(db: db, type: schemas.UserDocumentType, user: Annotated[model.User, Security(getUserBvn, scopes=["createUser"])], file = Depends(validateKycDocumentFile)):
    if user.kyc.status.identity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identity document already uploaded")

    file_name = f"{user.id}/kyc/{type.value}"
    file_path = await upload_file(bucket_name="user", file_object=file.file, file_name=file_name, content_type=file.content_type)
    user.kyc.status.identity = True
    db.commit()
    return {"message": "File uploaded successfully", "file_path": file_path}

async def getKycDocuments(db: db, user: Annotated[model.User, Security(getUserBvn, scopes=["createUser"])]):
    pass

async def checkKycStatus(db: db, user: Annotated[model.User, Security(getUserBvn, scopes=["createUser"])]):
    if user.kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KYC already exists")

    return user

@user.post("/kyc", status_code=status.HTTP_201_CREATED)
async def createUserKyc(db: db, user: Annotated[model.User, Security(checkKycStatus, scopes=["createUser"])], data: schemas.KycCreate):

    # check identity document file
    try:
        identity_document = await download_s3_object_for_requests(bucket_name="user", file_name=f"{user.id}/kyc/{schemas.UserDocumentType.FRONT_ID.value}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get identity document: " + str(e))
    
    if data.identity.idType == schemas.IDType.DRIVERS_LICENSE or data.identity.idType == schemas.IDType.VOTERS_CARD:
        try:
            back_document = await download_s3_object_for_requests(bucket_name="user", file_name=f"{user.id}/kyc/{schemas.UserDocumentType.BACK_ID.value}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get back identity document: " + str(e))

    kyc = model.Kyc(**data.model_dump(exclude={"address", "dateOfBirth", "identity", "nextOfKin", "middleName"}), userId=user.id)
    kyc.gender = data.gender
    kyc.idType = data.identity.idType
    kyc.idNumber = data.identity.idNumber
    kyc.idExpirationDate = data.identity.idExpirationDate
    kyc.nextOfKin = model.NextOfKin(**data.nextOfKin.model_dump(), kycId=kyc.id)

    db.add(kyc)
    # db.add(user_update)
    db.commit()
    return {"message": "KYC updated successfully"}

@user.post("/kyc/address", status_code=status.HTTP_200_OK)
async def createUserKycAddress(db: db, user: Annotated[model.User, Security(getUserBvn, scopes=["createUser"])], data: schemas.Address):

    # check proof of address file
    try:
        proof_of_address = await download_s3_object_for_requests(bucket_name="user", file_name=f"{user.id}/kyc/{schemas.UserDocumentType.PROOF_OF_ADDRESS.value}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get proof of address file: " + str(e))

    try:
        selfie_image_base64 = convert_minio_image_to_base64(bucket_name="user", object_name=f"{user.id}/kyc/{schemas.UserDocumentType.SELFIE.value}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get selfie image: " + str(e))

    submitted = db.execute(update(model.Kyc).where(model.Kyc.user_id == user.id).values(submitted=True).returning(model.Kyc)).scalar_one_or_none()

    # create anchor customer
    result = await createAnchorCustomer(
        firstName=user.first_name,
        lastName=user.last_name,
        maidenName=user.kyc.maidenName,
        dateOfBirth=user.dateOfBirth.isoformat(),
        gender=user.kyc.gender.value,
        bvn=user.bvn,
        selfieImage=selfie_image_base64,
        idType=user.kyc.idType.value,
        idNumber=user.kyc.idNumber,
        email=user.email,
        phoneNumber=user.phone_number,
        middleName=user.other_names,
        expiryDate=user.kyc.idExpirationDate.isoformat() if user.kyc.idExpirationDate else None,
        addressLine_1=data.addressLineOne,
        addressLine_2=data.addressLineTwo,
        city=data.city,
        state=data.state.value,
        postalCode=data.postalCode,
    )
    # print(result.json())
    if result.status_code not in [200, 201]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.text)

    db.execute(update(model.UserAddress).where(model.UserAddress.kycId == user.kyc.id).values(
        houseNumber=data.houseNumber,
        addressLineOne=data.addressLineOne,
        addressLineTwo=data.addressLineTwo,
        city=data.city,
        state=data.state.value,
        postalCode=data.postalCode,
    ))

    anchor_user = model.AnchorUser(customerId=result.json().get("data").get("id"), userId=user.id)
    db.add(anchor_user)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return {"message": "KYC address created successfully (Anchor user created)"}

async def getKycData(db: db, user: Annotated[model.User, Security(getUserBvn, scopes=["createUser"])]):

    kyc_data = schemas.AnchorKycCreate(**user.kyc, firstName=user.first_name, lastName=user.last_name, middleName=user.other_names, email=user.email, phoneNumber=user.phone_number)
    return {"kyc_data": kyc_data, "user_id": user.id}

@user.post("/kyc/validate")
async def validateKyc(db: db, kyc_data: Annotated[dict, Depends(getKycData)]):
    
    result = await createAnchorCustomer(**kyc_data.get("kyc_data").model_dump())
    if result.status_code not in [200, 201]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.text)
    return {"message": "KYC validated successfully (Anchor customer created)"}

@user.patch("/kyc")
async def updateUserKyc(db: db, data: schemas.KycUpdate, user: Annotated[model.User, Security(getUser, scopes=["createUser"])]):
    if user.kyc:
        db.execute(update(model.Kyc).where(model.Kyc.user_id == user.id).values(**data.model_dump()))
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        return {"message": "KYC updated successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start KYC first")

@user.get("/anchor/account")

@user.get("/value")
async def get_user_value(db: db, user = Depends(auth.getActiveUser)):
    
    total_usd = 0       
    total_ngn = 0

    for portfolio in user.portfolios:
        portfolio_value = await getPortfolioValue(db, portfolio)
        total_usd += portfolio_value["total_value_usd"]
        total_ngn += portfolio_value["total_value_ngn"]

    # get value of all products in portfolio with product risk <= 1
    

    return {
        "totalUsd": total_usd,
        "totalNgn": total_ngn,
        "inUsd": total_usd + (total_ngn/1600),
        "inNgn": total_ngn + (total_usd*1600),
        "holdings_count": len(user.portfolios),
        "active_deposits_count": len(user.portfolios),
        "calculation_date": datetime.now().isoformat()
    }

@user.post("/kyc/upload")
async def uploadKycFile(
    type: schemas.UserDocumentType, 
    user: Annotated[model.User, Security(getUser, scopes=["createUser"])],
    file: UploadFile = File()):

    # Validate the uploaded file
    await validate_image_file(file)
    
    file_name = f"{user.id}/kyc/{type.value}"
    file_path = await upload_file(bucket_name="user", file_object=file.file, file_name=file_name, content_type=file.content_type)
    return {"message": "File uploaded successfully", "file_path": file_path}

@user.get("/kyc")
async def getUserKyc(db: db, user: Annotated[model.User, Security(getUser, scopes=["createUser"])]):
    kyc = db.execute(select(model.Kyc).where(model.Kyc.userId == user.id)).scalar_one_or_none()
    if kyc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC not found")
    return kyc

async def checkKycVerification(kyc: Annotated[model.Kyc, Depends(getUserKyc)]):
    if kyc.identityVerified is False and kyc.verified is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KYC not verified")
    return kyc

@user.get("/file")
async def getFile(user_id: str, type: schemas.UserDocumentType):
    file_name = f"{user_id}/kyc/{type.value}"
    file = await get_file(bucket_name="user", file_name=file_name)
    return file

@user.get("/file/base64")
async def getFileAsBase64(user_id: str, type: schemas.UserDocumentType):
    """
    Get a stored file as base64 encoded string with data URL prefix
    """
    from utils.minio_to_base64 import convert_minio_image_to_base64
    
    file_name = f"{user_id}/kyc/{type.value}"
    try:
        base64_data = convert_minio_image_to_base64(bucket_name="user", object_name=file_name)
        return {
            "success": True,
            "data": base64_data,
            "file_name": file_name,
            "type": type.value
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "file_name": file_name,
            "type": type.value
        }