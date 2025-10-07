
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
from datetime import datetime
from sqlalchemy import select, update, insert
from celery_app import createAnchorAccountTask, linkAnchorAccountTask, validateKycTask
from utils.minio import upload_file, get_file

user = APIRouter(
    prefix="/user",
    tags=["user"],
)   

@user.post("/signup", response_model=schemas.UserSchema)
async def signup(db: db, data = Security(auth.verifyOtp, scopes=[schemas.OtpType.SIGNUP.value])):

    user = db.execute(select(model.User).where(model.User.email == data.get('email'), model.User.is_active == True)).scalar_one_or_none()
    if user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    user = model.User(first_name=data.get('first_name'), last_name=data.get('last_name'), other_names=data.get('other_names'), phone_number=data.get('phone_number'), email=data.get('email'), is_active=False)





    db.add(user)
    db.commit()
    db.refresh(user)

    # send welcome email - in a queue or send email for Brevo to send in the background
    # await utils.send_email(email=user.email, subject="Welcome to Your Pie", message="Welcome to Your Pie")

    return user

@user.post("/password", response_model=schemas.UserSchema)
async def set_password(db: db, password = Body(..., embed=True), payload = Security(auth.verifyAccessToken, scopes=[schemas.AccessLimit.PASSWORD.value])):

    user = db.execute(select(model.User).where(model.User.email == payload.get('username'))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has a password")

    user.password = auth.hashpass(password)
    user.is_active = True

    #  create use wallets
    usd_wallet = model.Wallet(currency="USD")
    ngn_wallet = model.Wallet(currency="NGN")
    user.wallets = [usd_wallet, ngn_wallet]

    liquid = model.Portfolio(type=model.PortfolioType.LIQUID.name, duration=1, risk=1, user_id=user.id)
    user.portfolios.append(liquid)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

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

@user.get("/all", dependencies=[Depends(auth.verifyAdminAccessToken)])
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

@user.post("/risk")
async def completeRiskQuestionnaire(db: db, data: schemas.RiskProfileCreate, user: Annotated[model.User, Depends(auth.getActiveUser)]):
    
    if user.riskProfile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk profile already exists")

    capacity = await runAssesment(data)

    portfolio_types = map(lambda x: x.type, user.portfolios)
    emergency_portfolio_exists = model.PortfolioType.EMERGENCY not in list(portfolio_types)
    print(emergency_portfolio_exists)

    risk_profile = model.RiskProfile(**data.model_dump(exclude={"objective"}), objective=data.objective.name, user_id=user.id, capacity=capacity)
    
    if emergency_portfolio_exists:

        portfolio = model.Portfolio(user_id=user.id, type=model.PortfolioType.EMERGENCY.name, risk=1, duration=1)
        portfolio.target = model.Target(amount=data.monthly_income * (3 if capacity.value == model.RiskLevel.HIGH.value else 6), currency=data.primary_income_currency)
        user.tier = 2
        user.riskProfile = risk_profile
        user.portfolios = user.portfolios
        db.add(portfolio)
    
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

@user.post("/kyc")
async def createKyc(db: db, 
data: schemas.KycCreate, user: Annotated[model.User, Security(getUser, scopes=["createUser"])]):

    if user.kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KYC already exists")
    kyc = model.Kyc(user_id=user.id, **data.model_dump(exclude={"maidenName", "address", "dateOfBirth", "gender", "phoneNumber"}), addresslineOne=data.address.addressLine_1, addresslineTwo=data.address.addressLine_2, city=data.address.city, state=data.address.state, postalCode=data.address.postalCode,is_complete=False)
    try:
        base64_selfie_image = convert_minio_image_to_base64(bucket_name="user", object_name=f"{user.id}/kyc/{schemas.UserDocumentType.SELFIE.value}")
        anchor_user = schemas.AnchorKycCreate(**data.model_dump(exclude={"addressProofType"}), firstName=user.first_name, middleName=user.other_names, lastName=user.last_name, email=user.email,addressProofType=data.addressProofType, selfieImage=base64_selfie_image)
        db.add(kyc)
        db.commit()
        createAnchorAccountTask.delay(**anchor_user.model_dump(exclude={"address","addressProofType", "country", "gender", "idType", "state"}), addressLine_1=data.address.addressLine_1, addressLine_2=data.address.addressLine_2, city=data.address.city, postalCode=data.address.postalCode, selfieImage=base64_selfie_image, gender=schemas.Gender(data.gender).value, idType=data.idType.value, state=data.address.state.value)
    except Exception as e:
        db.add(kyc)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
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
@user.post("/anchor/webhook")
async def anchorAccountCreated(data: dict = Body(embed=True)):

    linkAnchorAccountTask.delay(data)
    validateKycTask.delay(data)
    return {"message": "Anchor webhook received"}

@user.post("/kyc/webhook")
async def kycWebhook(data: dict = Body(embed=True)):
    validateKycTask.delay(data)
    return {"message": "KYC webhook received"}

@user.post("/kyc/upload")
async def uploadKycFile(
    type: schemas.UserDocumentType, 
    user: Annotated[model.User, Security(getUser, scopes=["createUser"])],
    file: UploadFile = File()):
    
    file_name = f"{user.id}/kyc/{type.value}"
    file_path = await upload_file(bucket_name="user", file_name=file_name, file_object=file.file, content_type=file.content_type)
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