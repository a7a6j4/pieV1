from fastapi import FastAPI, APIRouter, Security, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import SecurityScopes
from ...database import db
from sqlalchemy import select, update, delete, func, and_, or_, not_, desc, asc, extract, case
from sqlalchemy.sql import over
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel
from typing import Optional, List, Union, Annotated
from datetime import datetime
from ...model import PortfolioTransaction, Portfolio, User, RiskProfile, Journal, TransactionType, Entries, Target, PortfolioType, Product, ContributionPlan, ContributionSchedule, VariableHolding, UserDeposit, VariableValue, DepositRate, Variable, Deposit, Currency
from ...utils.payment_schedule import generate_schedule_dates
from .user import getUser
from ... import schemas
from decimal import Decimal
import enum
from ... import model
from . import auth

portfolio = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

class TargetCreate(BaseModel):
    amount: float
    date: Union[datetime, None] = None

class CommitmentCreate(BaseModel):
    amount: float
    frequency: str
    duration: Optional[int] = None

class TargetCommit(BaseModel):
  target: Optional[TargetCreate]
  commitment: Optional[CommitmentCreate]


@portfolio.get("/")
async def getPortfolio(
    portfolio_id: int, 
    db: db, 
    payload = Security(auth.readUser, scopes=["readUser"])):

  if payload.get("token") == "user":
    user = select(model.User).where(model.User.email == payload.get("username")).subquery()
    portfolio = db.execute(select(model.Portfolio).where(model.Portfolio.user_id == user.c.id, model.Portfolio.id == portfolio_id)).scalar_one_or_none()
  if payload.get("token") == "admin":
    portfolio = db.get(model.Portfolio, portfolio_id)

  if not portfolio:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
  return portfolio

@portfolio.post('/', response_model=schemas.PortfolioSchema)
async def createPortfolio(
   db: db,
   user = Security(auth.getActiveUser, scopes=["createUser"]),
   attributes: Annotated[Optional[schemas.PortfolioCreate], Body()] = None
):

    description = {
     PortfolioType.EMERGENCY.value: "Six months monthly income savings, held in short term, low risk & high yield investments",
     PortfolioType.LIQUID.value: "Holds cash to be needed in less than 90 days in highly liquid, low risk investments",
     PortfolioType.INVEST.value: "Investment Portfolio"}

    portfolio = model.Portfolio(
        user_id=user.id, 
        type=PortfolioType.INVEST.name)
    
    if attributes.description is not None:
        portfolio.description = attributes.description
    
    if attributes.risk is not None:
        portfolio.risk = attributes.risk

    if attributes.target is not None:
        target = model.Target(**attributes.target.model_dump())
        portfolio.target = target
    else:
        portfolio.description = description[PortfolioType.INVEST.value]

    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio

@portfolio.get("/transactions")
async def getPortfolioTransactions(
    db: db, 
    portfolio = Depends(getPortfolio)):
   
  portfolioTransactions = db.execute(select(model.PortfolioTransaction).where(model.PortfolioTransaction.portfolio_id == portfolio.id)).scalars().all()

  return portfolioTransactions

async def getPortfolioJournal(db: db, portfolio = Depends(getPortfolio)):
     
  # portfolio_transactions = select(PortfolioTransaction).where(PortfolioTransaction.portfolio_id == portfolio.id)

  # transaction_holdings = select(VariableHolding).where(portfolio_transactions.c.id == VariableHolding.transaction_id)

  assets = db.execute(
      select(
          model.Product.title,
          model.Product.currency,
          model.VariableHolding.units,
          model.VariableHolding.price,
          (model.VariableHolding.units * model.VariableHolding.price).label("total_value"),
          model.PortfolioTransaction.type,
          model.PortfolioTransaction.transaction_date
      )
      .join(model.PortfolioTransaction, model.VariableHolding.transaction_id == model.PortfolioTransaction.id)
      .join(model.Product, model.PortfolioTransaction.product_id == model.Product.id)
      .where(model.PortfolioTransaction.portfolio_id == portfolio.id, model.Product.category == "variable")
  ).all()

  deposits = db.execute(
      select(
          model.Product.title,
          model.Product.currency,
          model.UserDeposit.amount,
          model.UserDeposit.tenor,
          model.UserDeposit.start_date,
          model.UserDeposit.rate,
          model.PortfolioTransaction.type,
          model.PortfolioTransaction.transaction_date
      )
      .join(model.PortfolioTransaction, model.UserDeposit.transaction_id == model.PortfolioTransaction.id)
      .join(model.Product, model.PortfolioTransaction.product_id == model.Product.id)
      .where(model.PortfolioTransaction.portfolio_id == portfolio.id, model.Product.category == "deposit")
  ).all()

  # Combine and format the results
  all_assets = []
  for asset in assets:
      all_assets.append({
          "product_title": asset.title,
          "currency": asset.currency.value,
          "units": float(asset.units),
          "price": float(asset.price),
          "total_value": float(asset.total_value),
          "type": asset.transaction_type.value,
          "transaction_date": asset.transaction_date.isoformat(),
          "asset_type": "variable"
      })
  
  for deposit in deposits:
      all_assets.append({
          "product_title": deposit.title,
          "currency": deposit.currency.value,
          "amount": float(deposit.amount),
          "tenor": deposit.tenor,
          "start_date": deposit.start_date.isoformat(),
          "rate": float(deposit.rate),
          "transaction_type": deposit.transaction_type.value,
          "transaction_date": deposit.transaction_date.isoformat(),
          "asset_type": "deposit"
      })

  return all_assets

async def getPortfolioVariableAssets(
    db: db, 
    portfolio = Depends(getPortfolio)):

    testing = db.execute(select(
        model.Product,
        model.VariableValue.value.label("price"),
        (func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.INVESTMENT,
                    TransactionType.INTEREST,
                    TransactionType.BUY
                ]), model.VariableHolding.units),
                else_=0
            )
        ) -
        func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.LIQUIDATION, 
                    TransactionType.SELL, 
                    TransactionType.WITHDRAWAL]), 
                    model.VariableHolding.units),
                else_=0
            )
        )).label("units"),
        (model.VariableValue.value * 
        (func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.INVESTMENT,
                    TransactionType.INTEREST,
                    TransactionType.BUY
                ]), model.VariableHolding.units),
                else_=0
            )
        ) -
        func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.LIQUIDATION, 
                    TransactionType.SELL, 
                    TransactionType.WITHDRAWAL]), 
                    model.VariableHolding.units),
                else_=0
            )
        ))).label("value"),
        ((func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.INVESTMENT,
                    TransactionType.INTEREST,
                    TransactionType.BUY
                ]), model.PortfolioTransaction.amount),
                else_=0
            )
        ) - func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.LIQUIDATION, 
                    TransactionType.SELL, 
                    TransactionType.WITHDRAWAL]), 
                    model.PortfolioTransaction.amount),
                else_=0
            )
        )) / (func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.INVESTMENT,
                    TransactionType.INTEREST,
                    TransactionType.BUY
                ]), model.VariableHolding.units),
                else_=0
            )
        ) - func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.LIQUIDATION, 
                    TransactionType.SELL, 
                    TransactionType.WITHDRAWAL]), 
                    model.VariableHolding.units),
                else_=0
            )
        ))).label("vwac"),
        (model.VariableValue.value / 
        (
            (func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.INVESTMENT,
                    TransactionType.INTEREST,
                    TransactionType.BUY
                ]), model.PortfolioTransaction.amount),
                else_=0
            )
        ) - func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.LIQUIDATION, 
                    TransactionType.SELL, 
                    TransactionType.WITHDRAWAL]), 
                    model.PortfolioTransaction.amount),
                else_=0
            )
        )) / (func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.INVESTMENT,
                    TransactionType.INTEREST,
                    TransactionType.BUY
                ]), model.VariableHolding.units),
                else_=0
            )
        ) - func.sum(
            case(
                (model.PortfolioTransaction.type.in_([
                    TransactionType.LIQUIDATION, 
                    TransactionType.SELL, 
                    TransactionType.WITHDRAWAL]), 
                    model.VariableHolding.units),
                else_=0
            )
        ))
        ) - 1
        ).label("return"),

    )
    .join(model.VariableHolding, model.PortfolioTransaction.id == model.VariableHolding.transaction_id)
    .join(model.Product, model.PortfolioTransaction.product_id == model.Product.id)
    .join(model.VariableValue, model.Product.id == model.VariableValue.var_id)
    .where(model.PortfolioTransaction.portfolio_id == portfolio.id, model.Product.category == "variable")
    .distinct(model.VariableValue.value)
    .group_by(model.Product.id, model.VariableValue.value)
    .order_by(model.VariableValue.value.desc())
    .limit(1)
    ).mappings().all()

    return testing


async def getPortfolioDeposits(
    db: db, 
    portfolio = Depends(getPortfolio)):

    # Active deposits
    user_deposits = db.execute(
        select(
            model.UserDeposit.amount,
            model.UserDeposit.start_date,
            model.UserDeposit.rate,
            model.UserDeposit.maturity_date,
            model.Product
        )
        .join(model.PortfolioTransaction, model.UserDeposit.transaction_id == model.PortfolioTransaction.id)
        .join(model.Product, model.PortfolioTransaction.product_id == model.Product.id)
        .join(model.DepositRate, model.Product.id == model.DepositRate.deposit_id)
        .where(
            model.PortfolioTransaction.portfolio_id == portfolio.id,
            model.UserDeposit.is_active == True,
            model.UserDeposit.closed == False,
            model.UserDeposit.maturity_date >= datetime.now()
        )
    ).mappings().all()

    deposit_list = map(lambda x: {
        "Product": x.Product,
        "amount": x.amount,
        "value": float(x.amount) * float(1 + x.rate)**((datetime.now() - x.start_date).days/365),
        "rate": x.rate,
        "maturity_date": x.maturity_date,
    }, user_deposits)

    return list(deposit_list)


@portfolio.get("/assets")
async def getPortfolioAssets(
    db: db, 
    portfolio = Depends(getPortfolio)):

    return await getPortfolioVariableAssets(db, portfolio) + await getPortfolioDeposits(db, portfolio)

@portfolio.get("/value")
async def getPortfolioValue(
    products = Depends(getPortfolioAssets),
    currency: model.Currency = Query(default=None)):

    # print(products)

    usd_value = sum(x["value"] for x in filter(lambda x: x["Product"].currency == model.Currency.USD, products))
    ngn_value = sum(x["value"] for x in filter(lambda x: x["Product"].currency == model.Currency.NGN, products))

    total_usd = float(usd_value) + (float(ngn_value) / 1600)
    total_ngn = float(ngn_value) + (float(total_usd) * 1600)

    all_value = {
        "usdAssets": usd_value,
        "ngnAssets": ngn_value,
        "totalInUsd": total_usd,
        "totalInNgn": total_ngn,
        "last_calculated": datetime.now().isoformat()
    }

    if currency == model.Currency.USD:
        return all_value["totalInUsd"]
    elif currency == model.Currency.NGN:
        return all_value["totalInNgn"]
    else:
        return all_value
    
@portfolio.get("/product-fit")  
async def checkProductFit(
    db: db,
    products: List[int], 
    portfolio = Depends(getPortfolio)):
    """API endpoint to check if a product fits a portfolio's risk profile"""
    """Internal function to check if a product fits a portfolio's risk profile"""
    
    product = db.execute(select(Product).where(Product.id.in_(products))).scalars().all()

    found_product_ids = {product.id for product in product}

    missing_product_ids = set(products) - found_product_ids
    if missing_product_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Products not found: {list(missing_product_ids)}",
        )

    product_lookup = [{f"{product.id}": product} for product in product]

    unfit_products = []
    for id in products:
        if product_lookup[f"{id}"].risk_level > portfolio.risk:
            unfit_products.append(product_lookup[f"{id}"])
    
    if unfit_products:
        return {"fit": False, "unfit_products": unfit_products}
    else:
        return {"fit": True}

@portfolio.post("/attributes")
async def createAttributes(db: db, attributes: schemas.PortfolioAttributesCreate, portfolio: Portfolio = Depends(getPortfolio)):

    if attributes.target and attributes.commitment:
        target = Target(**attributes.target.model_dump())
        commitment = ContributionPlan(**attributes.commitment.model_dump())
        target.contribution_plan = commitment
        portfolio.target = target
        portfolio.contribution_plan = commitment
    elif attributes.target:
        if portfolio.target:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target already exists")
        target = Target(**attributes.target.model_dump())
        portfolio.target = target
    elif attributes.plan:
        if portfolio.contribution_plan:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution plan already exists")
        commitment = ContributionPlan(**attributes.plan.model_dump())
        portfolio.contribution_plan = commitment
    # else:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target or plan is required")
    
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio

@portfolio.put("/")
async def createTarget(db: db, attributes: schemas.PortfolioAttributesUpdate, portfolio: Portfolio = Depends(getPortfolio)):
  if attributes.target and attributes.commitment:
    target = Target(**attributes.target.model_dump())
    commitment = ContributionPlan(**attributes.commitment.model_dump())
    target.contribution_plan = commitment
    portfolio.target = target
  
  if attributes.target:
    """
        get recommended plan from advisory
        compare recommended allocation with current allocation
        if difference is greater than 10%, request for a reallocation
    """

    target = Target(**attributes.target.model_dump())
    portfolio.target = target

  if attributes.commitment:
    commitment = ContributionPlan(**attributes.commitment.model_dump())
    portfolio.contribution_plan = commitment

  if attributes.type:
    portfolio.type = PortfolioType(attributes.type)

  if attributes.description:
    portfolio.description = attributes.description

  if attributes.targetAllocation:
    portfolio.targetAllocation = attributes.targetAllocation

  db.add(portfolio)
  db.commit()
  db.refresh(portfolio)
  return portfolio

@portfolio.post("/plan")
async def createPlan(db: db, portfolio: Portfolio = Depends(getPortfolio), plan: schemas.CommitmentCreate = Body(), target: Optional[schemas.TargetCreate] = None):

  if portfolio.contribution_plan:
     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution plan already exists")
  if portfolio.type != PortfolioType.LIQUID.value:
     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid portfolio type")
    
  plan = ContributionPlan(**plan.model_dump())
  
  if target:
    target = Target(**target.model_dump())
    plan.target = target
  
  plan.portfolio_id = portfolio.id

    
    
    








