
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
from ..v1 import auth
from utils.minio_to_base64 import convert_minio_image_to_base64
from utils.assesment import runAssesment
from datetime import datetime, timedelta
from sqlalchemy import select, update, insert
from celery_app import linkAnchorAccountTask, uploadAnchorKycDocumentTask, createAnchorDepositAccountTask, validateAnchorTier2KycTask, validateAnchorTier3KycTask
from utils.minio import upload_file, get_file, download_s3_object_for_requests, validate_image_file
from utils.anchor import uploadAnchorCustomerDocument, createAnchorCustomer, anchor_api_server_error_codes, anchor_api_client_error_codes
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

@user.post("/password", response_model=schemas.UserSchema, status_code=status.HTTP_201_CREATED)
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

    # create wallet background task

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@user.post("/change-password")
async def changePassword(db: db, user: Annotated[model.User, Depends(auth.getActiveUser)]):
    # create a new password token
    create_password_token = auth.createToken(
        data={'username': user.email, "scope": schemas.AccessLimit.PASSWORD.value}, expires_delta=timedelta(seconds=schemas.opr[schemas.AccessLimit.PASSWORD.value]["seconds"])
    )
    return schemas.TokenResponse(token=create_password_token, token_type="bearer", expires_in=schemas.opr[schemas.AccessLimit.PASSWORD.value]["seconds"], limit=schemas.AccessLimit.PASSWORD)

@user.patch("/password", status_code=status.HTTP_201_CREATED)
async def updatePassword(db: db, new_password = Body(..., embed=True), token = Security(auth.verifyAccessToken, scopes=[schemas.AccessLimit.PASSWORD.value])):
    print(token)
    user = db.execute(update(model.User).where(model.User.email == token.get('username')).values(password=auth.hashpass(new_password)).returning(model.User)).scalar_one()
    db.commit()
    db.refresh(user)
    return {
        "message": "Password updated successfully"
    }

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

@user.post("/kyc")
async def createUserKyc(db: db, 
data: schemas.KycCreate, user: Annotated[model.User, Security(getUser, scopes=["createUser"])]):

    if user.kyc is not None and user.kyc.verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KYC already verified")
    
    base64_selfie_image = convert_minio_image_to_base64(bucket_name="user", object_name=f"{user.id}/kyc/{schemas.UserDocumentType.SELFIE.value}")
    address_data = schemas.Address(**data.address.model_dump())
    kyc_data = dict(**data.model_dump(exclude={"address"}))
        
    # create anchor user   
    anchor_user = schemas.AnchorAccountCreate(
            **data.model_dump(exclude={"addressProofType", "idExpirationDate", "address"}), 
            firstName=user.first_name, 
            lastName=user.last_name, 
            email=user.email,
            phoneNumber=user.phone_number,
            addressLineOne=data.address.addressLineOne,
            addressLineTwo=data.address.addressLineTwo,
            city=data.address.city,
            state=data.address.state,
            postalCode=data.address.postalCode,
            expiryDate=data.idExpirationDate,
    )

    args = {**anchor_user.model_dump(
        exclude={"addressLineTwo", "addressLineOne"}),
        "addressLine_1":data.address.addressLineOne, 
        "addressLine_2":data.address.addressLineTwo,
        "selfieImage":base64_selfie_image,
        "mode":schemas.AnchorMode.SANDBOX}
    
    create_customer_response = 200
    # create_customer_response = await createAnchorCustomer(args=args)
    if create_customer_response in anchor_api_server_error_codes:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=create_customer_response.get('error'))
    elif create_customer_response in anchor_api_client_error_codes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=create_customer_response.get('error'))
    else:

        # anchor_customer_id = create_customer_response.get('data').get('id')
        anchor_customer_id = "176091139716212-anc_ind_cst"

        # insert kyc to db
        address = model.UserAddress(**address_data.model_dump())
        kyc = model.Kyc(**data.model_dump(exclude={"address"}), verified=False, address=address, userId=user.id)
        # db.add(kyc)
        # db.commit()
        # db.refresh(kyc)
        validateAnchorTier2KycTask.delay(anchor_customer_id=anchor_customer_id, mode=schemas.AnchorMode.SANDBOX.value)
    
    return {"message": "KYC created successfully"}


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

# anchor account creation webhook
@user.post("/anchor/tier2")
async def anchorTier2Webhook(data: dict):
    anchor_customer_id = data.get('data').get('relationships').get('customer').get('data').get('id')
    validateAnchorTier3KycTask.delay(anchor_customer_id=anchor_customer_id, mode=schemas.AnchorMode.SANDBOX.value)
    return {"message": "Tier 2 KYC webhook received"}

@user.post("/anchor/tier3")
async def anchorTier3Webhook(data: dict):
    anchor_customer_id = data.get('data').get('relationships').get('customer').get('data').get('id')
    document_id = data.get('data').get('relationships').get('documents').get('data')[0].get('id')
    email = data.get('included')[1].get('attributes').get('email')
    
    uploadAnchorKycDocumentTask.delay(anchor_customer_id=anchor_customer_id, document_id=document_id, email=email, mode=schemas.AnchorMode.SANDBOX.value)
    return {"message": "Tier 3 KYC webhook received"}

@user.post("/anchor/document-verification")
async def anchorDocumentVerificationWebhook(data: dict):
    anchor_customer_id = data.get('data').get('relationships').get('customer').get('data').get('id')
    createAnchorDepositAccountTask.delay(anchor_customer_id=anchor_customer_id, mode=schemas.AnchorMode.SANDBOX.value)
    return {"message": "Document verification webhook received"}

@user.post("/anchor/deposit-account")
async def anchorDepositAccountWebhook(data: dict):
    customer_id = data.get('relationships').get('customer').get('data').get('id')
    deposit_account_id = data.get('relationships').get('account').get('data').get('id')
    email = data.get('included')[0].get('attributes').get('email')

    linkAnchorAccountTask.delay(anchor_customer_id=customer_id, anchor_deposit_account_id=deposit_account_id, email=email)
    return {"message": "Anchor deposit account created event received"}

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