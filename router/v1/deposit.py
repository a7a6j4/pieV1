from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from ...database import db
from ...model import UserDeposit, Deposit, DepositRate, Product
from typing import Annotated, Union, Optional, List
from datetime import datetime



deposit = APIRouter(
    prefix="/deposit",
    tags=["Deposit"]
)

@deposit.get("/{deposit_id}")
async def getDeposit(
        deposit_id: int,
        db: db
):
    deposit = db.get(UserDeposit, deposit_id)
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deposit not found")
     
    return deposit

@deposit.get("/deposit_value")
async def getDepositValue(
    deposit = Depends(getDeposit),
):
    
    value = deposit.amount * (1 + (deposit.rate/ 365 * 0.9 * (datetime.now() - deposit.start_date)))

    return value

@deposit.get("/liquidation_value")
async def getLiquidationValue(
    db: db,
    deposit: UserDeposit = Depends(getDeposit)
):
    days_passed = (datetime.now() - deposit.start_date).days
    days_left = deposit.tenor - days_passed

    if days_left >= 0:
        product = db.get(Deposit, deposit.transaction.product_id)
        penalty = product.penalty if product.penalty else 0     
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Deposit has matured")
    
    penalty_charge = (1 - penalty)
    total_interest_earned = deposit.amount * (deposit.rate/ 365 * days_passed)
    tax = float(total_interest_earned) * 0.1
    net_interest = float(total_interest_earned) - tax
    penalty_amount = net_interest * penalty
    liquidation_value = float(deposit.amount) + float(total_interest_earned) - tax - penalty_charge

    obj = {
        "principal": deposit.amount,
        "current": deposit.amount + total_interest_earned,
        "net_value": liquidation_value
    }

    if total_interest_earned > 0:

        obj["tax"] = tax
        obj["total_interest"] = total_interest_earned
        obj["net_interest"] = net_interest

    if penalty_amount > 0:
        obj["penalty"] = penalty_amount

    return obj