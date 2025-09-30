from fastapi import APIRouter, Body, Depends, Security, HTTPException, status
from fastapi.security import SecurityScopes
from ...database import db
from sqlalchemy import select, insert, update
from sqlalchemy.orm import Session
from typing import Annotated, Optional, Union, List
from ... import model
from ... import schemas
from . import auth

admin = APIRouter(prefix="/admin", tags=["admin"])

@admin.get("/")
async def getAdmin(db: db):
    return db.execute(select(model.AdminUser)).scalars().all()

@admin.post("/user")
async def createAdminUser(db: db, newUser: schemas.AdminUserCreate):
  new = model.AdminUser(**newUser.model_dump())
  db.add(new)
  db.commit()
  db.refresh(new)
  return {
    "message": "User created successfully",
    "user": new
  }
# async def createAdminUser(db: db, newUser: schemas.AdminUserCreate, createdBy: Annotated[model.AdminUser, Security(auth.verifyAdminAccessToken, scopes=[schemas.AccessLimit.CREATE_ACCOUNT.value])]):
#   new = model.AdminUser(email=newUser.email, password=auth.hashpass(newUser.password), first_name=newUser.first_name, last_name=newUser.last_name, phone_number=newUser.phone_number, group=newUser.group, role=newUser.role, createdBy=createdBy.id)
#   db.add(new)
#   db.commit()
#   db.refresh(new)
#   return {
#     "message": "User created successfully",
#     "user": new
#   }

@admin.post("/password")
async def updateAdminPassword(
  db: db, 
  payload: Annotated[model.AdminUser, Security(auth.verifyAdminAccessToken, scopes=[schemas.AccessLimit.PASSWORD.value])],
  password: str = Body(..., embed=True)):

  user = db.execute(select(model.AdminUser).where(model.AdminUser.email == payload.get('username'))).scalar_one_or_none()
  if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

  # if user.password:
  #   raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has a password")

  user.password = auth.hashpass(password)
  user.is_active = True

  db.add(user)
  db.commit()
  db.refresh(user)

  return {
    "message": "Password updated successfully"
  }