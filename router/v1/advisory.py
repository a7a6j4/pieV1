import math
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import SecurityScopes
from sqlalchemy import select, update, delete, func, and_, or_, not_, desc, asc, extract, case
from sqlalchemy.orm import Session, joinedload, selectinload
from datetime import datetime, timedelta
from database import db
import model
import schemas
from ..v1 import auth
from ..v1.portfolio import getPortfolioValue, getPortfolio, getPortfolioAssets
from typing import Annotated, Optional, Union
from utils.assesment import runAssesment
from ..v1.transaction import getWalletBalance
from ..v1.user import getUser
import enum
from fastapi import Query
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import numpy_financial as npf
from ..v1.user import getUser

advisory = APIRouter(
    prefix="/advisory",
    tags=["advisory"],
)

@advisory.get("/independence")
async def getFinancialIndependence(db: db, user = Depends(auth.getActiveUser)):
  """
    Check total assets as a proportion of annual income
    investment income is estimated return on assets, subtracted from the total income to get the required investment value to hold.
    required investment value is estimated fom non investment income via an average expecte return on capital or inflation.
  """

  total_usd = 0
  total_ngn = 0

  for portfolio in user.portfolios:
    portfolio_value = await getPortfolioValue(products=await getPortfolioAssets(db, portfolio=portfolio))
    total_usd += portfolio_value.get("totalInUsd", 0.00)
    total_ngn += portfolio_value.get("totalInNgn", 0.00)

  net_worth = total_ngn

  annual_income = float(user.riskProfile.monthly_income) * 12
  required_investment = float(annual_income) / 0.20 # required asset value to meet income
  
  gap = (required_investment - net_worth) if required_investment <= net_worth else 0
  independence = (net_worth / required_investment)

  return {
        "annualIncome": float(annual_income),
        "ngnRequiredInvestment": required_investment,
        "ngnNetWorth": float(net_worth),
        "independenceGap": gap,
        "independenceScore": independence,
        "message": "You are on your way to financial independence!" if independence >= 1 else "You need to increase your investments to achieve financial independence."
  }

async def recommendIndependence(db: db, user = Depends(getUser)):
  pass

@advisory.get("/emergency-risk")
async def getEmergencyRisk(
    db: db, 
    user: model.User = Depends(auth.getActiveUser)):
  """
    Check total low risk liquid assets as a proportion of 6 months income target amount
    ratio has to be greater then 1. can track state by how close to one

  """

  if not user.riskProfile:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk profile not found")

  usdLowRiskAssetValue = 0
  ngnLowRiskAssetValue = 0

  for portfolio in user.portfolios:
    assetInPortfolio = await getPortfolioAssets(db, portfolio=portfolio)
    lowRiskAssets = list(filter(lambda x: x["Product"].risk_level <= 1, assetInPortfolio))
    usdLowRiskAssetValue += sum(map(lambda x: x.get("total_value", 0.00) if x.get("Product").currency == model.Currency.USD else 0.00, lowRiskAssets))
    ngnLowRiskAssetValue += sum(map(lambda x: x.get("total_value", 0.00) if x.get("Product").currency == model.Currency.NGN else 0.00, lowRiskAssets))

  target_amount = user.riskProfile.monthly_income * 6
  ratio = (ngnLowRiskAssetValue + (usdLowRiskAssetValue * 1500)) / float(target_amount)

  return {
      "emergencyFundValue": (ngnLowRiskAssetValue + (usdLowRiskAssetValue * 1500)),
      "targetEmergencyFund": float(target_amount),
      "ratio": ratio,
      "message": "You have sufficent investments to mitigate financial emergency risk!" if ratio >= 1 else "Your emergency fund needs to be increased."
  }

async def recommendEmergencyRisk(user = Depends(getUser)):
  pass

@advisory.get("/liquidity-risk")
async def getLiquidRisk(db: db, user = Depends(getUser)):

  """
    Check all assets with horizon less than 1 compared to total net worth
  """

  total_usd = 0
  total_ngn = 0

  liquidityUsd = 0
  liquidityNgn = 0

  for portfolio in user.portfolios:
    portfolio_value = await getPortfolioValue(products=await getPortfolioAssets(
      db, 
      portfolio=portfolio))
    
    total_ngn += portfolio_value.get("totalInNgn")

    liquidity = await getPortfolioAssets(
      db, 
      portfolio=portfolio)
    liquidityUsd += sum(map(lambda x: x.get("total_value", 0.00) if x.get("Product").currency == model.Currency.USD else 0.00, liquidity))
    liquidityNgn += sum(map(lambda x: x.get("total_value", 0.00) if x.get("Product").currency == model.Currency.NGN else 0.00, liquidity))

  investmentValue = total_ngn
  liquid_assets = liquidityNgn + (liquidityUsd * 1500)
  liquidityRatio = liquid_assets / investmentValue

  return {
    "investmentValue": investmentValue,
    "liquidAssets": liquid_assets,
    "ratio": liquidityRatio,
    "message": "You have sufficent investments to mitigate liquidity risk!" if liquidityRatio >= 0.20 else "Invest in more liquid assets to mitigate liquidity risk."
  }

async def recommendLiquidRisk(user = Depends(getUser)):
  pass

async def performance(db: db, user = Depends(getUser)):

  """
  check portfolio performance relative to other comparable investments
  """
  pass

async def recommendPerformance(user = Depends(getUser)):
  pass

class RecommendationType(enum.Enum):
  SAVING = "saving"
  INCOME = "income"
  GROWTH = "growth"

async def getHigestReturnVariable(db: db, variables_subquery):
    """
    Accepts a SQLAlchemy selectable (subquery) for variable (product) IDs, and returns each product and its latest value and date.
    Example usage: getHigestReturnVariable(db, select(Variable.id).where(...))
    """

    # Subquery: get the latest date for each product (var_id)
    latest_dates_subq = (
        select(
            model.VariableValue.var_id,
            func.max(model.VariableValue.date).label("latest_date")
        )
        .where(
            model.VariableValue.var_id.in_(variables_subquery),
        )
        .group_by(model.VariableValue.var_id)
        .subquery()
    )

    # Main query: join Product, VariableValue, and the subquery
    query = (
        select(model.Product, model.VariableValue.value.label("latestValue"), model.VariableValue.date)
        .join(model.VariableValue, model.Product.id == model.VariableValue.var_id)
        .join(
            latest_dates_subq,
            and_(
                model.VariableValue.var_id == latest_dates_subq.c.var_id,
                model.VariableValue.date == latest_dates_subq.c.latest_date
            )
        )
        .where(model.Product.id.in_(variables_subquery), model.VariableValue.date <= datetime.now())
        .limit(3)
        .order_by(model.VariableValue.date.desc())
    )

    result = db.execute(query).mappings().all()

    return result    

async def getHigestReturnDeposit(db: db, deposits_subquery):
  """
  Accepts a SQLAlchemy selectable (subquery) for deposit (product) IDs, and returns each product and its latest value and date.
  Example usage: getHigestReturnDeposit(db, select(Deposit.id).where(...))
  """ 

  # Subquery: get the latest date for each product (var_id)
  latest_dates_subq = (
      select(
          model.DepositRate.deposit_id,
          func.max(model.DepositRate.date).label("latest_date")
      )
      .where(model.DepositRate.deposit_id.in_(deposits_subquery))
      .group_by(model.DepositRate.deposit_id)
      .subquery()
  )
    
  query = (select(model.Product, model.DepositRate.rate.label("latestValue"), model.  DepositRate.date)
        .join(model.DepositRate, model.Product.id == model.DepositRate.deposit_id)
        .join(
            latest_dates_subq,
            and_(
                model.DepositRate.deposit_id == latest_dates_subq.c.deposit_id,
                model.DepositRate.date == latest_dates_subq.c.latest_date
            )
        )
        .where(model.DepositRate.deposit_id.in_(deposits_subquery), model.DepositRate.date <= datetime.now())
        .limit(3)
        .order_by(model.DepositRate.date.desc())
        )
    
  result = db.execute(query).mappings().all()

  return result

@advisory.get("/savings")
async def getSavingsRecommendation(db: db,
  attributes: Annotated[schemas.SavingsRecommendationCreate, Query()],
  ):
  """
    Get savings recommendation for the user
  """
  benchmark = db.execute(select(model.Benchmark).where(model.Benchmark.symbol == 'FGN90')).scalar_one_or_none()

  if not benchmark:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benchmark not found")

  benchmarkYield = db.execute(select(model.BenchmarkHistory).join_from(model.BenchmarkHistory, model.Benchmark).where(model.BenchmarkHistory.benchmark_id == benchmark.id).order_by(model.BenchmarkHistory.date.desc())).first()

  if not benchmarkYield:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benchmark yield not found")

  variableProducts = select(model.Variable.id).where(model.Variable.horizon <= 1)
  depositProducts = select(model.Deposit.id)

  if attributes.tenor and attributes.tenor < 90:
    depositProducts = depositProducts.where(model.Deposit.fixed == False)
  elif attributes.tenor and attributes.tenor >= 90:
    depositProducts = depositProducts.where(model.Deposit.max_tenor >= attributes.tenor, model.Deposit.min_tenor <= attributes.tenor)
  
  if attributes.currency:
    variableProducts = variableProducts.where(model.Variable.currency == attributes.currency)
    depositProducts = depositProducts.where(model.Deposit.currency == attributes.currency)
  
  variableProducts = await getHigestReturnVariable(db, variableProducts.subquery())
  depositProducts = await getHigestReturnDeposit(db, depositProducts.subquery())

  filteredProducts = variableProducts + depositProducts
  filteredProducts = sorted(filteredProducts, key=lambda x: x.latestValue, reverse=True)
  
  filteredProducts = filteredProducts[:4]
  preferredProduct = filteredProducts[0]
  
  def addEstimatedFutureValue(product):
    latest_value = float(product.latestValue) if product.latestValue else 1e-9
    frequency = attributes.tenor
    estimated_future_value = attributes.amount * (1 + (latest_value * frequency / 365))
    d = dict(product)
    d['estimatedFutureValue'] = estimated_future_value
    d['earnedInterest'] = estimated_future_value - attributes.amount
    return d
  
  if attributes.amount:
    if attributes.tenor and attributes.tenor < 90:
      preferredProduct = addEstimatedFutureValue(preferredProduct)
      filteredProducts = list(map(addEstimatedFutureValue, filteredProducts))
    elif attributes.tenor and attributes.tenor >= 90:
      preferredProduct = addEstimatedFutureValue(preferredProduct)
      filteredProducts = list(map(addEstimatedFutureValue, filteredProducts))
  
  return {
    "preferred": preferredProduct,
    "others": filteredProducts
  }

class FrequencyDays(enum.IntEnum):
  monthly = 30
  quarterly = 91
  annual = 365
  semiannual = 182

@advisory.get("/income")
async def getIncomeAdvisory(db: db,
 attributes: Annotated[schemas.IncomeAdvisoryCreate, Query()]):
  """
    Get income advisory for the user
  """

  variableProducts = select(model.Variable.id).where(or_(model.Variable.horizon <= 1)).subquery()
  depositProducts = select(model.Deposit.id).where(model.Deposit.max_tenor >= FrequencyDays[attributes.frequency.value].value, model.Deposit.min_tenor <= FrequencyDays[attributes.frequency.value].value).subquery()

  variableProducts = await getHigestReturnVariable(db, variableProducts)
  depositProducts = await getHigestReturnDeposit(db, depositProducts)

  recommendedProducts = variableProducts + depositProducts
  recommendedProducts = sorted(recommendedProducts, key=lambda x: x.latestValue, reverse=True)
  recommendedProducts = recommendedProducts[:4]

  # Add requiredInvestment attribute to each product using the formula
  def add_required_investment(product):
      # Defensive: avoid division by zero
      latest_value = float(product.latestValue) if product.latestValue else 1e-9
      frequency = FrequencyDays[attributes.frequency.value].value
      required_investment = float(attributes.income) / latest_value / (frequency / 365)
      d = dict(product)
      d['requiredInvestment'] = required_investment
      return d

  def addEstimatedIncome(product):
    latest_value = float(product.latestValue) if product.latestValue else 1e-9
    frequency = FrequencyDays[attributes.frequency.value].value
    estimated_income = attributes.investment * latest_value * frequency / 365 
    d = dict(product)
    d['estimatedIncome'] = estimated_income
    return d
  
  preferredProduct = recommendedProducts[0]

  if attributes.liquidation:
      preferredProduct = variableProducts[0] if variableProducts else depositProducts[0]

  if attributes.income:
      # If you want to update recommendedProducts based on amount, do it here
      preferredProduct = add_required_investment(preferredProduct)
      recommendedProducts = list(map(add_required_investment, recommendedProducts))


  if attributes.investment:
    recommendedProducts = list(map(addEstimatedIncome, recommendedProducts))
    preferredProduct = addEstimatedIncome(preferredProduct)


  return {
    "preferred": preferredProduct,
    "others": recommendedProducts
  }


class EquityAllocationLimit(enum.Enum):
  MINMHORIZON = 3
  MAXMHORIZON = 10
  MINALLOCATION = 0.30
  MAXALLOCATION = 0.50
  
class UserRiskFactor(enum.Enum):
  HIGH = 0.30
  MID = 0.10
  LOW = 0

AGELIMIT = 60

async def getBestProducts(db:db, durationDays: int, currency: schemas.Currency):
  # best performing index or fund product
  ngnEquityProduct = select(model.Variable).where(model.  Variable.symbol == "NGN20")
  usdEquityProduct = select(model.Variable).where(model.  Variable.symbol == "SPY")

# Highest return money market or deposit product
  usdBondProduct = select(model.Deposit).where(model.Deposit.currency == schemas.Currency.USD)
  ngnBondProduct = select(model.Deposit).where(model.Deposit.currency == schemas.Currency.NGN)

  lowRiskProducts = select(model.Variable.id).where(model.Variable.horizon <= 1)
  depositProducts = select(model.Deposit.id).where(model.Deposit.max_tenor >= durationDays, model.Deposit.min_tenor <= durationDays)

  lowRiskProducts = await getHigestReturnVariable(db, lowRiskProducts)
  depositProducts = await getHigestReturnDeposit(db, depositProducts)

  recommendedLowRiskProducts = sorted(lowRiskProducts + depositProducts, key=lambda x: x.latestValue, reverse=True)

  if currency == schemas.Currency.USD:
    return usdEquityProduct, usdBondProduct, recommendedLowRiskProducts[0]
  elif currency == schemas.Currency.NGN:
    return ngnEquityProduct, ngnBondProduct

def getAllocation(duration: int, riskFactor: UserRiskFactor, age: int):

    factor = (min(duration, EquityAllocationLimit.MAXMHORIZON.value) - EquityAllocationLimit.MINALLOCATION.value) / (EquityAllocationLimit.MAXMHORIZON.value - EquityAllocationLimit.MINALLOCATION.value)
    eq_alloc = EquityAllocationLimit.MINALLOCATION.value + factor * (EquityAllocationLimit.MAXALLOCATION.value - EquityAllocationLimit.MINALLOCATION.value)
    eq_alloc = eq_alloc + riskFactor.value
    bond_alloc = 1 - eq_alloc

    return {"equity": eq_alloc, "bond": bond_alloc} if duration >= EquityAllocationLimit.MINMHORIZON.value else {"equity": 0, "bond": 1}

def getWeightedReturn(allocation: dict, currency: str, bond_return: float) -> float:
    """
    allocation: dict like {'equity': 0.5, 'bond': 0.5}
    currency: 'USD' or 'NGN'
    """
    # Set equity return based on currency
    if currency == schemas.Currency.USD:
        equity_return = 0.08
    elif currency == schemas.Currency.NGN:
        equity_return = 0.25
    else:
        raise ValueError("Unsupported currency")

    weighted = (
        allocation.get('equity', 0) * equity_return +
        allocation.get('bond', 0) * bond_return +
        allocation.get('cash', 0) * 0
    )
    return weighted

@advisory.get("/growth")
async def getTargetRecommendation(db: db,
  attributes: Annotated[schemas.growthParams, Query()]):
  """
    Get target recommendation for the user
  """

  if attributes.targetDate is None and attributes.duration is None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target date or duration is required")

  if attributes.targetDate is not None and attributes.duration is not None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target date and duration cannot be provided together. Please provide only one.")

  future_date = datetime.now() + relativedelta(months=attributes.duration) if attributes.duration else attributes.targetDate

  time_diff = relativedelta(future_date, datetime.now())
  days_diff = (future_date - datetime.now()).days

  lowRiskProducts = select(model.Variable.id).where(model.Variable.horizon <= 1, model.Variable.currency == attributes.currency.value)
  depositProducts = select(model.Deposit.id).where(model.Deposit.max_tenor >= min(365,days_diff), model.Deposit.min_tenor <= min(365,days_diff), model.Deposit.currency == attributes.currency.value)

  lowRiskProducts = await getHigestReturnVariable(db, lowRiskProducts)
  depositProducts = await getHigestReturnDeposit(db, depositProducts)

  recommendedLowRiskProducts = sorted(lowRiskProducts + depositProducts, key=lambda x: x.latestValue, reverse=True)

  equityProductUSD = select(model.Variable).where(model.Variable.symbol == "SPY")
  equityProductNGN = select(model.Variable).where(model.Variable.id == 2779)

  equityProduct = db.execute(equityProductUSD if attributes.currency.value == schemas.Currency.USD.value else equityProductNGN).scalar_one_or_none()

  if not equityProduct:
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Equity product not found")
  
  yearDuration = (future_date - datetime.now()).days/365

  daysToTarget = time_diff.days

  monthNper = math.floor(time_diff.years * 12 + time_diff.months) if attributes.investment is not None else math.floor(time_diff.years * 12 + time_diff.months) - 1
  quarterNper = math.floor(time_diff.years * 4 + time_diff.months / 3) if attributes.investment is not None else math.floor(time_diff.years * 4 + time_diff.months / 3) - 1
  semiAnnualNper = math.floor(time_diff.years * 2 + time_diff.months / 6) if attributes.investment is not None else math.floor(time_diff.years * 2 + time_diff.months / 6) - 1
  yearNper = 1 if time_diff.years <= 0 else math.floor(time_diff.years) if attributes.investment is not None else math.floor(time_diff.years) - 1

  allocation = getAllocation(yearDuration, UserRiskFactor.HIGH, 35)
  weightedReturn = getWeightedReturn(allocation, attributes.currency.value, float(recommendedLowRiskProducts[0].latestValue))

  if not attributes.target:
    response = {
      "duration": {
        "years": time_diff.years,
        "months": time_diff.months,
        "days": time_diff.days,
      },
      "estPortfolioAnnualReturn": weightedReturn,
      "portfolio": {
        "bond" : {
          "allocation": allocation.get('bond', 0),
          "product": recommendedLowRiskProducts[0],
          "estAnnualReturn": recommendedLowRiskProducts[0].latestValue
        }
      }}

    if allocation.get('equity', 0) > 0:
        response["portfolio"]["equity"] = {
          "allocation": allocation.get('equity', 0),
          "product": equityProduct,
          "estAnnualReturn": 0.30
        }

    return response 

  when = 'begin'

  #future of today's investment
  invFv = npf.fv(weightedReturn, yearDuration, 0, -attributes.investment, when=when) if attributes.investment is not None else 0
  # Net discounted target amount 
  discountedTargetAmount = (attributes.targetAmount / (1 + weightedReturn) ** daysToTarget) - invFv
  
  monthlyContribution = npf.pmt(weightedReturn / 12, monthNper, 0,discountedTargetAmount, when=when)
  quarterlyContribution = npf.pmt(weightedReturn / 4, quarterNper, 0,discountedTargetAmount, when=when)
  semiAnnualContribution = npf.pmt(weightedReturn / 2, semiAnnualNper, 0,discountedTargetAmount, when=when)
  yearlyContribution = npf.pmt(weightedReturn, yearNper, 0,discountedTargetAmount, when=when)

  result = {
    "duration": {
      "years": time_diff.years,
      "months": time_diff.months,
      "days": time_diff.days,
    },
    "porfolio": {
      "bond" : {
        "allocation": allocation.get('bond', 0),
        "product": recommendedLowRiskProducts[0],
        "estAnnualReturn": recommendedLowRiskProducts[0].latestValue
      }
    },
    "peridicContribution": {
      "monthly": {
        "contribution": monthlyContribution,
        "nper": monthNper
      },
      },
    "estPortfolioAnnualReturn": weightedReturn
  }

  if semiAnnualNper > 4:
    result["peridicContribution"]["semiAnnual"] = {
      "contribution": semiAnnualContribution,
      "nper": semiAnnualNper
    }

  if quarterNper > 4:
    result["peridicContribution"]["quarterly"] = {
      "contribution": quarterlyContribution,
      "nper": quarterNper
    }

  if yearNper > 2:
    result["peridicContribution"]["yearly"] = {
      "contribution": yearlyContribution,
      "nper": yearNper
    }

  result["upfrontInvestment"] = attributes.investment if attributes.investment is not None else 0

  if allocation.get('equity', 0) > 0:
    result["porfolio"]["equity"] = {
      "allocation": allocation.get('equity', 0),
      "product": equityProduct,
      "estAnnualReturn": 0.30
    }

  if attributes.target:
    return result
  else:
    pass

@advisory.get("/portfolio/allocation")
async def getPortfolioAllocation(db: db, portfolio: model.Portfolio = Depends(getPortfolio)):
  pass

@advisory.get("/new-portfolio")
async def getNewPortfolioAllocation(
  db: db,
  portfolio: model.Portfolio = Depends(getPortfolio) 
  ):

  if portfolio.type == schemas.PortfolioType.INCOME:

    frequency = portfolio.income.frequency
    # tenor = schemas.tenor_map[frequency]
    tenor = 90

    # mutual funds and deposits, which has the 

    depositProducts = db.execute(
      select(model.Deposit).
      where(model.Deposit.maxTenor >= tenor, model.Deposit.minTenor <= tenor, model.Deposit.currency == 'NGN', model.Deposit.isActive == True).
      order_by(model.Deposit.rate.desc()).
      limit(3)).scalars().all()
    if portfolio.income.amount is not None:
      target_income = portfolio.income.amount
      print(target_income)
      requiredInvestments = list(map(lambda x: {
        "product": x,
        "requiredInvestment": target_income / x.rate * 100 / (tenor / 365)
      }, depositProducts))
      return requiredInvestments

    return depositProducts

  elif portfolio.type in [schemas.PortfolioType.TARGET, schemas.PortfolioType.GROWTH, schemas.PortfolioType.INVEST]:

    # get highest expected return variable product

      duration = portfolio.duration
      if portfolio.target is not None:
        if portfolio.target.targetDate is not None:

          target_date = portfolio.target.targetDate
          days_diff = relativedelta(target_date, datetime.now()).days

          if days_diff <= 365:
            # get highest return deposit or mutual fund return
            pass

          elif days_diff > 365 and days_diff <= 1095:
            # get highest return variable product
            pass

          else:

            pass



          pass
        else: 
          pass