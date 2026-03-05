from cgi import print_exception
from math import prod
# from click.utils import P
from celery import current_app
from fastapi import FastAPI, APIRouter, Security, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import SecurityScopes
import requests
from database import db
from sqlalchemy import select, update, delete, func, and_, or_, not_, desc, asc, extract, case
from sqlalchemy.sql import over
from sqlalchemy.orm import Session, aliased, joinedload, selectinload, with_polymorphic
from pydantic import BaseModel
from typing import Any, Optional, List, Union, Annotated
from datetime import datetime, timedelta
import model
from router.v1.advisory import getHighestReturnIncomeProduct
from router.v1.product import getPrice, getProduct
from utils.payment_schedule import generate_schedule_dates
from ..v1.user import getUser
import schemas
from decimal import Decimal
import enum
from ..v1 import auth
from config import settings
import utils, copy

portfolio = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

@portfolio.get("")
async def getPortfolio(
    portfolioId: int, 
    db: db, 
    user: Annotated[model.User, Security(getUser, scopes=["readUser"])]):

    portfolio = db.execute(select(model.Portfolio).where(model.Portfolio.userId == user.id, model.Portfolio.id == portfolioId)).scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    return portfolio

@portfolio.get("/all")
async def getAllPortfolios(db: db, user: Annotated[model.User, Security(getUser, scopes=["readUser"])]):

    return user.portfolios

@portfolio.post("", status_code=status.HTTP_201_CREATED)
async def createPortfolio(
   db: db,
   type: schemas.PortfolioType,
   user = Security(getUser, scopes=["createUser"]),
   attributes: schemas.PortfolioCreate = Body()
   ):

    if type in [schemas.PortfolioType.EMERGENCY, schemas.PortfolioType.LIQUID]:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=f"invalid portfolio type: cannot create liquid or emergency portfolios here")

    if type == schemas.PortfolioType.GROWTH or type == schemas.PortfolioType.TARGET or type == schemas.PortfolioType.INVEST:
        if attributes.duration is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"duration attribute is required in request body for {type.value} portfolios")

    description = attributes.description if attributes.description is not None and attributes.description != "" else schemas.default_description_map.get(type, None)
    
    portfolio = model.Portfolio(
        title=attributes.title,
        userId=user.id, 
        type=type, 
        description=description, 
        risk=attributes.risk,
        duration=attributes.duration)
    db.add(portfolio)

    if attributes.target is not None:
        target = model.PortfolioTarget(**attributes.target.model_dump())
        portfolio.target = target

    if attributes.income is not None:
        if type != schemas.PortfolioType.INCOME:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{type.value} cannot have an income a")
        income = model.PortfolioIncome(**attributes.income.model_dump())
        income.startDate = datetime.now()

        nextdate_map = {
            schemas.Frequency.MONTHLY: timedelta(days=30),
            schemas.Frequency.BIMONTHLY: timedelta(days=60),
            schemas.Frequency.QUARTERLY: timedelta(days=90),
            schemas.Frequency.SEMIANNUALLY: timedelta(days=180),
            schemas.Frequency.ANNUALLY: timedelta(days=365),
        }

        income.nextIncomeDate = income.startDate + nextdate_map[attributes.income.frequency]
        portfolio.income = income
    
    # Define portfolio strategic asset allocation

    db.commit()
    db.refresh(portfolio)
    return portfolio

@portfolio.get("/transactions")
async def getPortfolioTransactions(
    db: db,
    portfolio: Annotated[model.Portfolio, Depends(getPortfolio)],
    status: Annotated[Optional[schemas.TransactionStatus], Query()] = schemas.TransactionStatus.COMPLETED):

    transactions = portfolio.transactions
    if status:
        transactions = [transaction for transaction in transactions if transaction.status == status]
    return transactions

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

    principal = (deposit_value[0].principal if deposit_value[0].principal else 0)
    accrued_interest = (deposit_value[0].accrued_interest if deposit_value[0].accrued_interest else 0)
    withholding_tax = (deposit_value[0].withholding_tax if deposit_value[0].withholding_tax else 0)
    current_value = float(principal) + float(accrued_interest) - float(withholding_tax)

    return {"deposit": deposit, "current_value": current_value, "principal": principal, "accrued_interest": accrued_interest, "withholding_tax": withholding_tax}

@portfolio.get("/assets")
async def getPortfolioAssets(db: db, portfolio: model.Portfolio = Depends(getPortfolio)):

    
    transactions = select(model.PortfolioTransaction.id).where(model.PortfolioTransaction.portfolioId == portfolio.id, model.PortfolioTransaction.status == schemas.TransactionStatus.COMPLETED)
    ledgers = select(model.VariableLedger).where(model.VariableLedger.transactionId.in_(transactions)).subquery()

    # return db.execute(ledgers).scalars().all()

    net_units_expr = func.sum(
        case(
            (ledgers.c.side == schemas.UserLedgerSide.IN, (ledgers.c.amount/ledgers.c.price)),
            (ledgers.c.side == schemas.UserLedgerSide.OUT, (-ledgers.c.amount/ledgers.c.price)),
        )
    )
    net_amount_expr = func.sum(
        case(
            (ledgers.c.side == schemas.UserLedgerSide.IN, ledgers.c.amount),
            (ledgers.c.side == schemas.UserLedgerSide.OUT, -ledgers.c.amount),
        )
    )

    product = select(model.Product).options(joinedload(model.Variable.values)).subquery()

    variable_assets = db.execute(
        select(
            product,
            net_units_expr.label("netUnits"),
            net_amount_expr.label("netAmount"),
        )
        .select_from(product).join(ledgers, ledgers.c.variableId == product.c.id)
        .group_by(product.c.id, product.c.issuerId, product.c.title, product.c.description, product.c.currency, product.c.assetClass, product.c.productClass, product.c.category, product.c.benchmarkId, product.c.isActive, product.c.created, product.c.lastModified, product.c.productGroupId, product.c.riskLevel, product.c.horizon, product.c.img, ledgers.c.price)
        .having(net_amount_expr > 0)
    ).mappings().all()

    assets = []

    for asset in variable_assets:
        asset_data = dict(asset).copy()
        net_amount = float(asset["netAmount"]) / 100

        asset_data["vwac"] = net_amount / float(asset["netUnits"])
        asset_data["currentPrice"] = await getPrice(db=db, product=await getProduct(db=db, productId=asset["id"]))
        asset_data["performance"] = asset_data["currentPrice"] / (asset_data["vwac"]) - 1
        asset_data["currentValue"] = net_amount * (1 + asset_data["performance"])
        asset_data["netAmount"] = net_amount
        assets.append(asset_data)


    deposits = select(model.PortfolioDeposit, model.DepositTransaction).select_from(model.PortfolioDeposit).join(model.DepositTransaction, model.PortfolioDeposit.transactionId == model.DepositTransaction.id).where(model.DepositTransaction.portfolioId == portfolio.id, model.DepositTransaction.status == schemas.TransactionStatus.COMPLETED, model.PortfolioDeposit.closed == False, model.PortfolioDeposit.matured == False, model.PortfolioDeposit.maturityDate >= datetime.now()).subquery()
    deposit_products = db.execute(select(model.Product.id, model.Product.currency, model.Product.title, model.Product.category, deposits.c.id.label("depositId"), deposits.c.effectiveDate, deposits.c.maturityDate, deposits.c.amount).select_from(deposits).join(model.Product, deposits.c.productId == model.Product.id)).mappings().all()
    # return db.execute(deposit_products).mappings().all()

    for deposit in deposit_products:
        deposit_data = dict(deposit).copy()
        current_value  = await getNGDepositValue(deposit_data["depositId"], db)
        deposit_data["currentValue"] = float(current_value.get("current_value")) / 100
        deposit_data["netAmount"] = float(deposit_data["amount"]) / 100
        deposit_data["performance"] = (deposit_data["currentValue"] - float(deposit_data["netAmount"])) / float(deposit_data["netAmount"])
        deposit_data["accruedInterest"] = current_value.get("accrued_interest") / 100
        deposit_data["withholdingTax"] = current_value.get("withholding_tax") / 100
        deposit_data["holdingPeriod"] = (datetime.now() - deposit_data["effectiveDate"]).days
        assets.append(deposit_data)

    return assets

@portfolio.get("/value")
async def getPortfolioValue(db: db, assets = Depends(getPortfolioAssets)):

    usd_base_value = 0
    ngn_base_value = 0
    usd_current_value = 0
    ngn_current_value = 0
    portfolio_performance = 0

    for asset in assets:
        if asset["currency"] == schemas.Currency.USD:
            usd_base_value += float(asset["netAmount"])
            usd_current_value += asset["currentValue"]
        if asset["currency"] == schemas.Currency.NGN:
            ngn_base_value += float(asset["netAmount"])
            ngn_current_value += asset["currentValue"]
        asset_performance = (asset["currentValue"] - float(asset["netAmount"])) / float(asset["netAmount"])
        portfolio_performance += asset_performance * float(asset["netAmount"])
    
    return {
        "totalValueUsd": usd_current_value + (ngn_current_value / 1600),
        "totalValueNgn": ngn_current_value + (usd_current_value * 1600),
        "totalPerformance": portfolio_performance,
        "totalUsdAssetValue": usd_current_value,
        "totalNgnAssetValue": ngn_current_value,
        "totalUsdInvested": usd_base_value,
        "totalNgnInvested": ngn_base_value,
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

@portfolio.post("/objectives", status_code=status.HTTP_201_CREATED)
async def addPortfolioObjectives(db: db, objectives: schemas.PortfolioObjectiveCreate, portfolio: model.Portfolio = Depends(getPortfolio)):

    updated_attributes = {}

    if objectives.target:
        if portfolio.target is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target already exists")
        target = model.PortfolioTarget(**objectives.target.model_dump())
        portfolio.target = target
        updated_attributes["target"] = {"amount": target.amount, "currency": target.currency, "targetDate": target.targetDate}
    if objectives.income:
        if portfolio.income is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Income already exists")
        income = model.PortfolioIncome(**objectives.income.model_dump())
        income.startDate = datetime.now()

        income.nextIncomeDate = income.startDate + schemas.nextdate_map[objectives.income.frequency]
        portfolio.income = income
        updated_attributes["income"] = {"amount": income.amount, "currency": income.currency, "frequency": income.frequency, "startDate": income.startDate, "nextIncomeDate": income.nextIncomeDate}
    
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return {"message": "Objectives created successfully", "objectives": updated_attributes}

@portfolio.patch("/objectives", status_code=status.HTTP_200_OK)
async def updatePortfolioObjectives(db: db, objectives: schemas.PortfolioObjectiveCreate, portfolio: model.Portfolio = Depends(getPortfolio)):
    updated_attributes = {}
    
    if objectives.target:
        if portfolio.target is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target not found")
        target = db.execute(update(model.PortfolioTarget).values(**objectives.target.model_dump()).where(model.PortfolioTarget.id == portfolio.target.id).returning(model.PortfolioTarget)).scalar_one_or_none()
        updated_attributes["target"] = {"amount": target.amount, "currency": target.currency, "targetDate": target.targetDate}
    if objectives.income:
        if portfolio.income is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Income not found")
        income = db.execute(update(model.PortfolioIncome).values(**objectives.income.model_dump()).where(model.PortfolioIncome.id == portfolio.income.id).returning(model.PortfolioIncome)).scalar_one_or_none()
        updated_attributes["income"] = {"amount": income.amount, "currency": income.currency, "frequency": income.frequency, "startDate": income.startDate, "nextIncomeDate": income.nextIncomeDate}
    
    db.commit()
    db.refresh(portfolio)
    return {"message": "Objectives updated successfully", "updated": updated_attributes}

@portfolio.delete("/attributes")
async def deleteAttributes(db: db, target: bool = Query(False), commitment: bool = Query(False), portfolio: model.Portfolio = Depends(getPortfolio)):
  if portfolio.target is None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target not found")
  if portfolio.contributionPlan is None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution plan not found")

  if target:
    db.delete(portfolio.target)
  if commitment:
    db.delete(portfolio.contributionPlan)

  db.add(portfolio)
  db.commit()
  db.refresh(portfolio)
  return portfolio

@portfolio.get("/advice")
async def getPortfolioAdvice(db: db, portfolio: model.Portfolio = Depends(getPortfolio)):
    """
       - target to commitment: check that the value of periodic contributions can achieve the target
       - target to allocation: check that the allocation of the portfolio can achieve the target
       - portfolio expected return vs other allocations
    """
    portfolio_value = await getPortfolioValue(db, await getPortfolioAssets(db, portfolio))

    if portfolio.type == schemas.PortfolioType.EMERGENCY:
        # get portfolio value and compare to target

        deposit_product = db.execute(select(model.Deposit).where(model.Deposit.currency == portfolio.target.currency, model.Deposit.maxTenor <= 180, model.Deposit.minTenor >= 0).order_by(model.Deposit.rate.desc()).limit(1)).scalar_one_or_none()
        
        # mutual_fund_product = find the mutual fund with the highest expected return / yield
        # 

        value = portfolio_value.get("totalValueNgn") if portfolio.target.currency == schemas.Currency.NGN else portfolio_value.get("totalValueUsd")
        target = portfolio.target.amount
        progress = value / target

        deficiency = target - value

        advice = ""

        if progress < 0.5:
            advice = "You are at risk of not having enough emergency fund to cover your expenses in the event of an emergency."
        elif progress < 0.75:
            advice = "You are on track to have enough emergency fund to cover your expenses in the event of an emergency."
        elif progress < 1:
            advice = "You are on track to have enough emergency fund to cover your expenses in the event of an emergency."
        else:
            advice = "You are sufficienty protected for an financial emergency emergency risk"
            deficiency = value - target

        return {
            "progress": progress,
            "advice": advice,
            "deficiency": deficiency,
            "recomendedProduct": deposit_product,
        }

    if portfolio.type == schemas.PortfolioType.GROWTH:
        # get portfolio value and compare to growth
        portfolio_value = await getPortfolioValue(db, portfolio)
        if portfolio_value.get("totalValueNgn") < portfolio.growth.amount:
            pass

    if portfolio.type == schemas.PortfolioType.INCOME:
        # compare portfolio income yield to other products in similar income frequency
        # if portfolio income yield is higher or equal, return the portfolio income yield
        # if portfolio income yield is lower, return the other products in similar income frequency
        pass

# def generate_schedule_dates(start_date: datetime, frequency: schemas.Frequency, duration: int)

@portfolio.get("/transaction/all")
async def getAllPortfolioTransactions(db: db, user: model.User = Depends(auth.getActiveUser)):
    portfolios = user.portfolios
    all_transactions = []
    for portfolio in portfolios:
        transactions = filter(lambda x: x.status == schemas.TransactionStatus.COMPLETED, portfolio.transactions)
        all_transactions.extend(list(transactions)) 

    all_transactions = sorted(all_transactions, key=lambda x: x.date, reverse=True)
    return all_transactions