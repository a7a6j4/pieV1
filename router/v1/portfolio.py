from cgi import print_exception
from fastapi import FastAPI, APIRouter, Security, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import SecurityScopes
import requests
from database import db
from sqlalchemy import select, update, delete, func, and_, or_, not_, desc, asc, extract, case
from sqlalchemy.sql import over
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel
from typing import Any, Optional, List, Union, Annotated
from datetime import datetime
import model
from router.v1.product import getPrice
from utils.payment_schedule import generate_schedule_dates
from ..v1.user import getUser
import schemas
from decimal import Decimal
import enum
from ..v1 import auth
from config import settings
import utils

portfolio = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

@portfolio.get("/")
async def getPortfolio(
    portfolioId: int, 
    db: db, 
    user: Annotated[model.User, Security(getUser, scopes=["readUser"])]):

  portfolio = db.execute(select(model.Portfolio).where(model.Portfolio.userId == user.id, model.Portfolio.id == portfolioId)).scalar_one_or_none()

  if not portfolio:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
  return portfolio

@portfolio.post('/', response_model=schemas.PortfolioSchema)
async def createPortfolio(
   db: db,
   type: schemas.PortfolioType,
   user = Security(getUser, scopes=["createUser"]),
   attributes: Annotated[Optional[schemas.PortfolioCreate], Body()] = None):

   if type in [schemas.PortfolioType.EMERGENCY, schemas.PortfolioType.LIQUID]:
    single_portfolio = db.execute(select(model.Portfolio).where(model.Portfolio.userId == user.id, model.Portfolio.type == type)).scalar_one_or_none()
    if single_portfolio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{type.value} portfolio already exists")

    portfolio = model.Portfolio(
        userId=user.id, 
        type=type, 
        description=attributes.description if attributes.description else f"{type.value} portfolio", 
        risk=1 if type == schemas.PortfolioType.EMERGENCY or type == schemas.PortfolioType.LIQUID else attributes.risk,
        duration=1 if type == schemas.PortfolioType.EMERGENCY or type == schemas.PortfolioType.LIQUID else attributes.duration)

    if attributes.target is not None:
        target = model.Target(**attributes.target.model_dump())
        portfolio.target = target

    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio

@portfolio.get("/transactions")
async def getPortfolioTransactions(
    db: db,
    portfolio: Annotated[model.Portfolio, Depends(getPortfolio)],
    status: Annotated[Optional[schemas.TransactionStatus], Query()] = None):

    transactions = portfolio.transactions
    if status:
        transactions = [transaction for transaction in transactions if transaction.status == status]
    return transactions

@portfolio.get("/assets")
async def getPortfolioAssets(db: db, portfolio: model.Portfolio = Depends(getPortfolio)):

    variable_assets = db.execute(
      select(model.Variable,
          func.sum(case(
            (model.VariableLedger.side == schemas.UserLedgerSide.IN, model.VariableLedger.units),
            (model.VariableLedger.side == schemas.UserLedgerSide.OUT, -model.VariableLedger.units),
          )).label("net_units"),
          func.sum(case(
            (model.VariableLedger.side == schemas.UserLedgerSide.IN, model.VariableLedger.amount),
            (model.VariableLedger.side == schemas.UserLedgerSide.OUT, -model.VariableLedger.amount),
          )).label("net_amount"),
      ).join_from(model.VariableLedger, model.Variable, model.VariableLedger.variableId == model.Variable.id).where(model.VariableLedger.portfolioId == portfolio.id).distinct(model.Variable.id).group_by(model.Variable.id, model.Product.id)
  ).mappings().all()

    filtered_variable_assets = filter(lambda x: x.net_units > 0, variable_assets)
    map_variable_assets = list(map(lambda x: {"Variable": x.Variable, "net_units": x.net_units, "net_amount": x.net_amount / 100, "vwac": (x.net_amount / 100) / x.net_units}, filtered_variable_assets))    
    
    transactions = select(model.DepositTransaction).where(model.DepositTransaction.portfolioId == portfolio.id).subquery()
    deposits = db.execute(select(model.PortfolioDeposit, transactions).join_from(transactions, model.PortfolioDeposit, model.PortfolioDeposit.transactionId == transactions.c.id)).mappings().all()

    return {
        "variable_assets": map_variable_assets,
        "deposits": deposits,
    }
    
@portfolio.get("/deposit-value")
async def getNGDepositValue(depositId: int, db: db):
    deposit = db.get(model.PortfolioDeposit, depositId)
    if not deposit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deposit not found")
    
    deposit_value = db.execute(select(
        func.sum(case(
            ((model.DepositLedger.account == schemas.PortfolioAccount.ASSET and model.DepositLedger.side == schemas.UserLedgerSide.IN),
            model.DepositLedger.amount),
            ((model.DepositLedger.account == schemas.PortfolioAccount.ASSET and model.DepositLedger.side == schemas.UserLedgerSide.OUT),
            -model.DepositLedger.amount),
        )).label("principal"),
        func.sum(case(
            ((model.DepositLedger.account == schemas.PortfolioAccount.INTEREST and model.DepositLedger.side == schemas.UserLedgerSide.IN),
            model.DepositLedger.amount),
            ((model.DepositLedger.account == schemas.PortfolioAccount.INTEREST and model.DepositLedger.side == schemas.UserLedgerSide.OUT),
            -model.DepositLedger.amount),
        )).label("accrued_interest"),
        func.sum(case(
            ((model.DepositLedger.account == schemas.PortfolioAccount.TAX and model.DepositLedger.side == schemas.UserLedgerSide.IN),
            -model.DepositLedger.amount),
            ((model.DepositLedger.account == schemas.PortfolioAccount.TAX and model.DepositLedger.side == schemas.UserLedgerSide.OUT),
            model.DepositLedger.amount)
        )).label("withholding_tax"),
    ).where(model.DepositLedger.portfolioDepositId == deposit.id)).mappings().all()

    principal = (deposit_value[0].principal if deposit_value[0].principal else 0) / 100
    accrued_interest = (deposit_value[0].accrued_interest if deposit_value[0].accrued_interest else 0) / 100
    withholding_tax = (deposit_value[0].withholding_tax if deposit_value[0].withholding_tax else 0) / 100
    current_value = principal + accrued_interest - withholding_tax

    return {"deposit": deposit, "current_value": current_value, "principal": principal, "accrued_interest": accrued_interest, "withholding_tax": withholding_tax}

@portfolio.get("/value")
async def getPortfolioValue(
    db: db,
    assets = Depends(getPortfolioAssets)
):

    assets_list = []
    print(assets["variable_assets"])
    for asset in assets["variable_assets"]:
        if asset["Variable"].productGroup.productClass == schemas.ProductClass.EQUITY and asset["Variable"].productGroup.market == schemas.Country.NG:
            value = db.execute(select(model.VariableValue).where(model.VariableValue.variableId == asset["Variable"].id).order_by(model.VariableValue.date.desc()).limit(1)).scalar_one_or_none()
            price = value.price / 100
            current_value = asset["net_units"] * price
            invested_amount = asset["net_amount"]
            performance = (current_value - invested_amount) / invested_amount
            assets_list.append({
                "product": asset["Variable"],
                "invested_amount": invested_amount,
                "vwac": asset["vwac"],
                "current_price": price,
                "current_value": current_value,
                "performance": performance,
                "category": "variable",
            })
        elif asset["Variable"].productGroup.productClass == schemas.ProductClass.EQUITY and asset["Variable"].productGroup.market == schemas.Country.US:
            price = await getPrice(db=db, variable_id=asset["Variable"].id)
            performance = (price / asset["vwac"]) - 1
            assets_list.append({
                "product": asset["Variable"],
                "invested_amount": asset["net_amount"],
                "vwac": asset["vwac"],
                "current_price": price,
                "current_value": asset["net_units"] * price,
                "performance": performance,
                "category": "variable",
            })
        elif asset["Variable"].productGroup.productClass == schemas.ProductClass.MUTUAL_FUND:
            pass

    for deposit in assets["deposits"]:
        current_value = await getNGDepositValue(deposit["PortfolioDeposit"].id, db)
        invested_amount = deposit["amount"] / 100
        performance = (current_value["current_value"] - invested_amount) / invested_amount
        holding_period = min(datetime.now(), deposit["PortfolioDeposit"].maturityDate) - deposit["PortfolioDeposit"].effectiveDate
        annualized_performance = (1 + performance)**(365 / holding_period.days) - 1
        assets_list.append({
            "deposit": deposit["PortfolioDeposit"],
            "rate": deposit["rate"],
            "tenor": deposit["tenor"],
            "invested_amount": invested_amount,
            "current_value": current_value["current_value"],
            "performance": annualized_performance,
            "holding_period": holding_period.days,
            "category": "deposit",
        })

    total_value = sum(map(lambda x: x["current_value"], assets_list))
    total_invested = sum(map(lambda x: x["invested_amount"], assets_list))
    performance = (total_value - total_invested) / total_invested if total_invested > 0 or total_value > 0 else 0

    
    ngn_deposits = list(filter(lambda x: x["category"] == "deposit" and x["deposit"].transaction.product.currency == schemas.Currency.NGN, assets_list))
    usd_deposits = list(filter(lambda x: x["category"] == "deposit" and x["deposit"].transaction.product.currency == schemas.Currency.USD, assets_list))
    ngn_variable = list(filter(lambda x: x["category"] == "variable" and x["product"].currency == schemas.Currency.NGN, assets_list))
    usd_variable = list(filter(lambda x: x["category"] == "variable" and x["product"].currency == schemas.Currency.USD, assets_list))

    (ngn_deposits_value, ngn_deposits_invested) = (sum(map(lambda x: x["current_value"], ngn_deposits)), sum(map(lambda x: x["invested_amount"], ngn_deposits)))
    (usd_deposits_value, usd_deposits_invested) = (sum(map(lambda x: x["current_value"], usd_deposits)), sum(map(lambda x: x["invested_amount"], usd_deposits)))
    (ngn_variable_value, ngn_variable_invested) = (sum(map(lambda x: x["current_value"], ngn_variable)), sum(map(lambda x: x["invested_amount"], ngn_variable)))
    (usd_variable_value, usd_variable_invested) = (sum(map(lambda x: x["current_value"], usd_variable)), sum(map(lambda x: x["invested_amount"], usd_variable)))

    try:
        usd_performance = ((usd_variable_value + usd_deposits_value) - (usd_variable_invested + usd_deposits_invested)) / (usd_variable_invested + usd_deposits_invested)
    except:
        usd_performance = 0
    try:
        ngn_performance = ((ngn_variable_value + ngn_deposits_value) - (ngn_variable_invested + ngn_deposits_invested)) / (ngn_variable_invested + ngn_deposits_invested)
    except:
        ngn_performance = 0

    return {
        "total_value_ngn": ngn_variable_value + ngn_deposits_value,
        "total_value_usd": usd_variable_value + usd_deposits_value,
        "total_performance_ngn": ngn_performance,
        "total_performance_usd": usd_performance,
        "assets": assets_list,
    }

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
            model.Product,
            model.Currency
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
    
@portfolio.get("/product-fit")  
async def checkProductFit(
    db: db,
    products: List[int], 
    portfolio = Depends(getPortfolio)):
    """API endpoint to check if a product fits a portfolio's risk profile"""
    """Internal function to check if a product fits a portfolio's risk profile"""
    
    product = db.execute(select(model.Product).where(model.Product.id.in_(products))).scalars().all()

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
async def createAttributes(db: db, attributes: schemas.PortfolioAttributesCreate, portfolio: model.Portfolio = Depends(getPortfolio)):

    if attributes.target and attributes.commitment:
        target = model.Target(**attributes.target.model_dump())
        commitment = model.ContributionPlan(**attributes.commitment.model_dump())
        target.contribution_plan = commitment
        portfolio.target = target
        portfolio.contribution_plan = commitment
    elif attributes.target:
        if portfolio.target:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target already exists")
        target = model.Target(**attributes.target.model_dump())
        portfolio.target = target
    elif attributes.plan:
        if portfolio.contribution_plan:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution plan already exists")
        commitment = model.ContributionPlan(**attributes.plan.model_dump())
        portfolio.contribution_plan = commitment
    # else:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target or plan is required")
    
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio

@portfolio.put("/")
async def createTarget(db: db, attributes: schemas.PortfolioAttributesUpdate, portfolio: model.Portfolio = Depends(getPortfolio)):
  if attributes.target and attributes.commitment:
    target = model.Target(**attributes.target.model_dump())
    commitment = model.ContributionPlan(**attributes.commitment.model_dump())
    target.contribution_plan = commitment
    portfolio.target = target
  
  if attributes.target:
    """
        get recommended plan from advisory
        compare recommended allocation with current allocation
        if difference is greater than 10%, request for a reallocation
    """

    target = model.Target(**attributes.target.model_dump())
    portfolio.target = target

  if attributes.commitment:
    commitment = model.ContributionPlan(**attributes.commitment.model_dump())
    portfolio.contribution_plan = commitment

  if attributes.type:
    portfolio.type = schemas.PortfolioType(attributes.type)

  if attributes.description:
    portfolio.description = attributes.description

  if attributes.targetAllocation:
    portfolio.targetAllocation = attributes.targetAllocation

  db.add(portfolio)
  db.commit()
  db.refresh(portfolio)
  return portfolio

@portfolio.post("/plan")
async def createPlan(db: db, portfolio: model.Portfolio = Depends(getPortfolio), plan: schemas.CommitmentCreate = Body(), target: Optional[schemas.TargetCreate] = None):

  if portfolio.contribution_plan:
     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution plan already exists")
  if portfolio.type != schemas.PortfolioType.LIQUID.value:
     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid portfolio type")
    
  plan = model.ContributionPlan(**plan.model_dump())
  
  if target:
    target = model.Target(**target.model_dump())
    plan.target = target
  
  plan.portfolio_id = portfolio.id

    
    
    








