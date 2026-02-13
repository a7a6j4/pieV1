
from fastapi import APIRouter, Body, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBasic, HTTPBasicCredentials, SecurityScopes
from sqlalchemy import select
from model import User
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone
from database import db
from jwt import InvalidTokenError
from random import randint
from random import randrange
import secrets
import schemas
from typing import Annotated
from datetime import datetime, timezone
import model
from celery_app import sendOtpTask
from config import settings
from utils.brevo import sendOtpEmail
# models    

auth = APIRouter(prefix="/auth", tags=["auth"])

otpScheme = OAuth2PasswordBearer(tokenUrl="otp", scopes={"signUp": "signUp","resetPassword": "resetPassword"})
userAccessScheme = OAuth2PasswordBearer(
    tokenUrl="", 
    scopes={
        "createPassword": "User only has access to create password", 
        "readUser": "User can read their own user data", 
        "createUser": "User can create and update their own user data"}, 
    auto_error=False)
adminAccessScheme = OAuth2PasswordBearer(
    tokenUrl="admin", 
    scopes={
        "readUser": "Admin can read user data",
        "createUser": "Admin can create and update user data",
        "createPassword": "Allows new admin user create password", 
        "createAccount": "Allows super admin user create admin user", 
        "login": "Allows admin user login abd view their dashboard",
        "readAdmin": "Allows admin user read admin data",
        "createAdmin": "Allows admin user create admin data",
        "approveAdmin": "Allows admin user approve admin data"}, 
    auto_error=False)

security = HTTPBasic()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

secret = settings.SECRET_KEY
algorithm = settings.ALGORITHM
login_minutes = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES)

def hashpass(password: str):
    return pwd_context.hash(password)

def verify_hash(plain, hashed):
    return pwd_context.verify(plain, hashed)

def createToken(data: dict, expires_delta: timedelta):

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": int(expire.timestamp()), **data}
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=algorithm)
    return encoded_jwt

async def decodeToken(encoded_jwt):

    try:
        payload = jwt.decode(encoded_jwt, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload

async def verifyAccessToken(security_scopes: SecurityScopes, encoded_jwt = Security(userAccessScheme)):
    payload = await decodeToken(encoded_jwt)
    token_scopes = payload.get('scope', '').split()
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
            )
    return payload

async def verifyUserAccess(payload = Security(verifyAccessToken, scopes=["createPassword", "fullAccess", "createAccount"])):

    user = db.execute(select(User).where(User.email == payload.get('username'))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not exist")
    return user

async def verifyOtp(scopes: SecurityScopes, otp = Body(..., embed=True), encoded_jwt = Depends(otpScheme)):

    if scopes.scopes:
        authenticate_value = f'Bearer scope="{scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    payload = await decodeToken(encoded_jwt)
    otp_check = verify_hash(otp, payload.get('otp'))
    if not otp_check:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP", headers={"WWW-Authenticate": authenticate_value})
    for scope in payload.get('scope', "").split(","):
        if scope not in scopes.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient Permission", headers={"WWW-Authenticate": authenticate_value})

    return payload

@auth.post("/otp", response_model=schemas.TokenResponse)
async def verifyOtpResponse(encoded_jwt =Security(verifyOtp, scopes=[schemas.OtpType.RESET_PASSWORD.value, schemas.OtpType.SIGNUP.value, schemas.OtpType.CREATE_PASSWORD.value])):
    
    access_token_expires = timedelta(seconds=schemas.opr[encoded_jwt.get('scope', "")]["seconds"])
    access_token = createToken(
        data={'email': encoded_jwt.get('email'), "scope": encoded_jwt.get('scope', "")}, expires_delta=access_token_expires 
    )
    return schemas.TokenResponse(token=access_token, token_type="bearer", expires_in=schemas.opr[encoded_jwt.get('scope', "")]["seconds"], limit=encoded_jwt.get('scope', ""))

@auth.post("", response_model=schemas.SigninTokenResponse)
async def accessToken(
    db: db, 
    credentials: Annotated[dict, Body(..., embed=False)],
):

    email = credentials.get('username').lower()
    
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not Authorized")

    if not user.is_active:
        create_password_token = createToken(
            data={'username': user.email, "scope": schemas.AccessLimit.PASSWORD.value}, expires_delta=timedelta(seconds=schemas.opr[schemas.AccessLimit.PASSWORD.value]["seconds"])
        )
        return schemas.SigninTokenResponse(token=create_password_token,token_type="bearer", expires_in=schemas.opr[schemas.AccessLimit.PASSWORD.value]["seconds"], limit=schemas.AccessLimit.PASSWORD)
    
    check_password = verify_hash(credentials.get('password'), user.password)

    if not check_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect username or password")
    
    access_token_expires = timedelta(seconds=schemas.opr[schemas.AccessLimit.LOGIN.value]["seconds"])
    access_token = createToken(
        data={'username': user.email, "scope": f"{schemas.AccessLimit.CREATE_USER.value} {schemas.AccessLimit.READ_USER.value}", "token": "user"}, expires_delta=access_token_expires
    )
    return schemas.SigninTokenResponse(token=access_token, token_type="bearer", expires_in=schemas.opr[schemas.AccessLimit.LOGIN.value]["seconds"], limit=schemas.AccessLimit.LOGIN)

async def sendOtp(data: dict, type: schemas.OtpType):

    single_digits = [str(randint(0, 9)) for _ in range(5)]  # Convert to strings
    otp = ''.join(single_digits)

    hashed_otp = hashpass(otp)
    email_response = await sendOtpEmail(otp=otp, email=data.get('email'), otpType=type)
    if email_response not in [200, 201]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to send OTP")
    seconds = schemas.opr.get(type.value).get("seconds")
    expires = timedelta(seconds=int(seconds))
    payload = {"otp": hashed_otp, **data, "scope": type.value}
    token = createToken(data=payload, expires_delta=expires)
    return schemas.TokenResponse(token=token, token_type="bearer", expires_in=seconds)

@auth.post("/signup", response_model=schemas.TokenResponse)
async def signupotp(userData: schemas.SignupCreate, db: db):
    user = db.execute(select(User).where(User.email == userData.email)).scalar_one_or_none()

    if user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    phone_number = db.execute(select(User).where(User.phone_number == userData.phoneNumber)).scalar_one_or_none()
    if phone_number is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered")
    
    data = userData.model_dump()
    data['email'] = data['email'].lower()
    
    return await sendOtp(data=data, type=schemas.OtpType.SIGNUP)

async def getActiveUser(db: db, payload = Security(verifyAccessToken)):

    user = db.execute(select(User).where(User.email == payload.get('username'))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not exist")
    return user

async def checkWithdrawPermission(db: db, user: Annotated[User, Depends(getActiveUser)]):
    if user.tier < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not have withdrawal permission")
    return user

async def checkAdvisoryPermission(db: db, user: Annotated[User, Depends(getActiveUser)]):
    if user.tier < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not have advisory permission")
    return user

@auth.post("/reset-password", response_model=schemas.TokenResponse)
async def resetPassword(db: db, email = Body(..., embed=True)):
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        return await sendOtp(data={'email': user.email}, type=schemas.OtpType.RESET_PASSWORD)
    else:
        raise None

@auth.post("/admin", response_model=schemas.SigninTokenResponse)
async def getAdminAccess(
    db: db, 
    HTTPBasicCredentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
    user = db.execute(select(model.AdminUser).where(model.AdminUser.email == HTTPBasicCredentials.username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not exist")
    if user.is_active == False:
        create_password_token = createToken(
            data={'username': user.email, "scope": schemas.AccessLimit.PASSWORD.value}, expires_delta=timedelta(seconds=schemas.opr[schemas.AccessLimit.PASSWORD.value]["seconds"])
        )
        return schemas.SigninTokenResponse(token=create_password_token, token_type="bearer", expires_in=schemas.opr[schemas.AccessLimit.PASSWORD.value]["seconds"], limit=schemas.AccessLimit.PASSWORD)

    check_user = secrets.compare_digest(HTTPBasicCredentials.username.encode('utf-8'), user.email.encode('utf-8'))
    check_password = verify_hash(HTTPBasicCredentials.password.encode('utf-8'), user.password.encode('utf-8'))

    if not check_user or not check_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    scope = f"{schemas.AccessLimit.LOGIN.value} {schemas.AccessLimit.READ_ADMIN.value} {schemas.AccessLimit.READ_USER.value}"
    
    if user.role == model.AdminRole.SUPER and user.group == model.AdminGroup.SUPER:
        scope = scope + f" {schemas.AccessLimit.CREATE_ACCOUNT.value} {schemas.AccessLimit.CREATE_USER.value} {schemas.AccessLimit.CREATE_ADMIN.value} {schemas.AccessLimit.APPROVE_ADMIN.value}"
    elif user.group in [model.AdminGroup.EXECUTIVE.value, model.AdminGroup.OPERATIONS.value, model.AdminGroup.SUPPORT.value, model.AdminGroup.ADMIN.value]:
        if user.role == model.AdminRole.WRITE:
            scope = scope
        elif user.role == model.AdminRole.APPROVE:
            scope = scope + f" {schemas.AccessLimit.APPROVE_ADMIN.value}"

    access_token_expires = timedelta(seconds=schemas.opr[schemas.AccessLimit.LOGIN.value]["seconds"])
    access_token = createToken(
        data={'username': user.email, "scope": scope, "token": "admin"}, expires_delta=access_token_expires
    )
    return schemas.SigninTokenResponse(token=access_token, token_type="Bearer", expires_in=schemas.opr[schemas.AccessLimit.LOGIN.value]["seconds"], limit=schemas.AccessLimit.LOGIN.value)


async def decodeTokenScopes(encoded_jwt, scopes: SecurityScopes):

    if scopes.scopes:
        authenticate_value = f'Bearer scope="{scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    payload = await decodeToken(encoded_jwt)
    token_scopes = payload.get('scope', '').split()
    for scope in scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return payload

async def verifyAdminAccessToken(
    scopes: SecurityScopes, 
    encoded_jwt = Depends(adminAccessScheme)):

    payload = await decodeTokenScopes(encoded_jwt, scopes)
    return payload

async def readUser(
    scopes: SecurityScopes,
    userToken: Annotated[User, Security(userAccessScheme)],
    adminToken: Annotated[model.AdminUser, Security(adminAccessScheme)],
):

    if not userToken and not adminToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if userToken:
        payload = await decodeTokenScopes(userToken, scopes) 
    if adminToken:
        payload = await decodeTokenScopes(adminToken, scopes)
        
    return payload

