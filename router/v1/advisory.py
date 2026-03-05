import math
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import SecurityScopes
from sqlalchemy import select, update, delete, func, and_, or_, not_, desc, asc, extract, case
from sqlalchemy.orm import Session, joinedload, selectinload, with_polymorphic
from datetime import datetime, timedelta
from database import db
import model
import schemas
from ..v1 import auth
from ..v1.portfolio import getPortfolioValue, getPortfolio, getPortfolioAssets
from typing import Annotated, Optional, Union
from utils.assesment import runAssesment
from ..v1.transaction import getWalletBalance
from ..v1.user import getUser, getUserRiskProfile, getUserValue
import enum
from fastapi import Query
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import numpy_financial as npf
from ..v1.user import getUser, getUserKyc, checkKycVerification


advisory = APIRouter(
    prefix="/advisory",
    tags=["advisory"],
)


@advisory.get("/independence")
async def getFinancialIndependence(db: db, user: Annotated[model.User, Depends(getUserRiskProfile)]):
  """
    Check total assets as a proportion of annual income
    investment income is estimated return on assets, subtracted from the total income to get the required investment value to hold.
    required investment value is estimated fom non investment income via an average expecte return on capital or inflation.
  """

  total_usd = 0
  total_ngn = 0

  user_value = await getUserValue(db, user)
  in_ngn = user_value.get("totalValueNgn")
  in_usd = user_value.get("totalValueUsd")

  if user.riskProfile.primary_income_currency == schemas.Currency.NGN:
    net_worth = in_ngn
  elif user.riskProfile.primary_income_currency == schemas.Currency.USD:
    net_worth = in_usd
  else:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid income currency")
  

  annual_income = in_ngn if user.riskProfile.primary_income_currency == schemas.Currency.NGN else in_usd * 1500
  required_investment = annual_income / 0.07 if user.riskProfile.primary_income_currency == schemas.Currency.USD else annual_income / 0.20 # required asset value to meet income
  
  gap = (required_investment - net_worth) if required_investment <= net_worth else 0
  independence = (net_worth / required_investment)
  return {
    "annualIncome": annual_income,
    "requiredInvestment": required_investment,
    "netWorth": net_worth,
    "gap": gap,
    "independence": independence,
  }
async def recommendIndependence(db: db, user = Depends(getUser)):
  pass

@advisory.get("/emergency-risk")
async def getEmergencyRisk(
    db: db, 
    user: Annotated[model.User, Depends(getUserRiskProfile)]):
  """
    Check total low risk liquid assets as a proportion of 6 months income target amount
    ratio has to be greater then 1. can track state by how close to one

  """

  if not user.riskProfile:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk profile not found")

  emergency_portfolio = list(filter(lambda x: x.type == schemas.PortfolioType.EMERGENCY, user.portfolios))

  emergency_fund_value = await getPortfolioValue(db, await getPortfolioAssets(db, portfolio=emergency_portfolio[0]))
  target_currency = emergency_portfolio[0].get("target").get("currency")

  target_emergency_fund = emergency_portfolio[0].get("target").get("amount")
  ratio = emergency_fund_value.get("totalValueNgn") if target_currency == schemas.Currency.NGN else emergency_fund_value.get("totalValueUsd") / target_emergency_fund
  
  return {
    "emergencyFundValue": emergency_fund_value.get("totalValueNgn") if target_currency == schemas.Currency.NGN else emergency_fund_value.get("totalValueUsd"),
    "targetEmergencyFund": target_emergency_fund,
    "targetCurrency": target_currency,
    "ratio": ratio,
  }

async def recommendEmergencyRisk(user = Depends(getUser)):
  pass

@advisory.get("/liquidity-risk")
async def getLiquidRisk(db: db, user: Annotated[model.User, Depends(getUserRiskProfile)]):

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



async def getHighestReturnIncomeProduct( db: db,
  portfolio: model.Portfolio = Depends(getPortfolio)):
  """
  Accepts a SQLAlchemy selectable (subquery) for deposit (product) IDs, and returns each product and its latest value and date.
  Example usage: getHigestReturnDeposit(db, select(Deposit.id).where(...))
  """ 

  # Subquery: get the latest date for each product (var_id)
# get highest return variable or deposit product

  base_model = with_polymorphic(model.Product, [model.Variable, model.Deposit])
  base_query = select(base_model).where(base_model.isActive == True)
  result = []
  
  base_query = base_query.where(base_model.currency == portfolio.income.currency, base_model.horizon <= 1)
  
  frequency = portfolio.income.frequency
  tenor = schemas.tenor_map[frequency]
  if frequency == schemas.Frequency.MONTHLY:
    base_query = base_query.where(or_(model.Deposit.maxTenor.in_([30, 31]), model.Variable.horizon == 1, model.Variable.attributes.has(model.VariableAttributes.distribution == schemas.Frequency.MONTHLY)))
  elif frequency == schemas.Frequency.QUARTERLY:
    base_query = base_query.where(or_(model.Deposit.maxTenor.in_([90, 91, 92]), model.Variable.horizon == 1, model.Variable.attributes.has(model.VariableAttributes.distribution == schemas.Frequency.QUARTERLY)))
  elif frequency == schemas.Frequency.SEMIANNUALLY:
    base_query = base_query.where(or_(model.Deposit.maxTenor.in_([180, 181, 182]), model.Variable.horizon == 1, model.Variable.attributes.has(model.VariableAttributes.distribution == schemas.Frequency.SEMIANNUALLY)))
  elif frequency == schemas.Frequency.ANNUALLY:
    base_query = base_query.where(or_(model.Deposit.maxTenor.in_([364, 365, 366]), model.Variable.horizon == 1, model.Variable.attributes.has(model.VariableAttributes.distribution == schemas.Frequency.ANNUALLY)))
  
  products = db.execute(base_query.limit(3)).scalars().all()
  for product in products:
    recomendation = {
      "product": product,
      "estAnnualReturn": product.rate if product.category == schemas.ProductClass.DEPOSIT else 8 if product.currency == schemas.Currency.USD else 20,
    }

    result.append(recomendation)
  
  new_result = sorted(result, key=lambda x: x["estAnnualReturn"])
  return new_result

class FrequencyDays(enum.IntEnum):
  monthly = 30
  quarterly = 91
  annual = 365
  semiannual = 182

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


@advisory.get("/portfolio/allocation")
async def getPortfolioAllocation(db: db, portfolio: model.Portfolio = Depends(getPortfolio)):
  pass


@advisory.get("/new-portfolio")
async def getNewPortfolioAllocation(
  db: db,
  portfolio: model.Portfolio = Depends(getPortfolio), 
  ):

  base_model = with_polymorphic(model.Product, [model.Variable, model.Deposit])
  base_query = select(base_model).where(base_model.isActive == True)
  result = []

  if portfolio.income is not None:
    products = await getHighestReturnIncomeProduct(db, portfolio)
    for product in products:
      numerator = portfolio.income.amount * 12 if portfolio.income.frequency == schemas.Frequency.MONTHLY else portfolio.income.amount * 4 if portfolio.income.frequency == schemas.Frequency.QUARTERLY else portfolio.income.amount * 2 if portfolio.income.frequency == schemas.Frequency.SEMIANNUALLY else portfolio.income.amount
      denominator = ((product.rate if product.category == schemas.ProductClass.DEPOSIT else 8 if product.currency == schemas.Currency.USD else 20) / 100)
      product.amount = numerator / denominator
      result.append(product)
    return {"recomendation": result}
  
  if portfolio.type in [schemas.PortfolioType.TARGET, schemas.PortfolioType.GROWTH, schemas.PortfolioType.INVEST]:

    # get highest expected return variable product
      if portfolio.target:

        base_query = base_query.where(base_model.currency == portfolio.target.currency)
        if portfolio.target.targetDate:

          target_date = portfolio.target.targetDate
          days_diff = relativedelta(target_date, datetime.now()).days

          # get time difference in x year(s), x month(s) and x day(s)
          years = math.floor(days_diff / 365)
          months = math.floor((days_diff % 365) / 30)
          days = days_diff % 30

          growth_duration = {
            "years": years,
            "months": months,
            "days": days
          }


          if days_diff <= 365:
            # get highest return deposit or mutual fund return
            products = db.execute(base_query.where(base_model.horizon <= 1).limit(3)).scalars().all()

          elif days_diff > 365 and days_diff <= 1095:
            # get highest return variable product
            products = db.execute(base_query.where(base_model.horizon > 1, base_model.horizon <= 3).limit(3)).scalars().all()

          elif days_diff > 1095 and days_diff <= 2190:

            products = db.execute(base_query.where(base_model.horizon > 3, base_model.horizon <= 5).limit(3)).scalars().all()

          else:
            products = db.execute(base_query.where(base_model.horizon > 5).limit(3)).scalars().all()

        # pv of target amount
        pv = npf.pv(0.08 if portfolio.target.currency == schemas.Currency.USD else 0.2, days_diff / 365, 0, -portfolio.target.amount)
        for product in products:
            result.append({
              "product": product,
              "amount": pv,
              "estAnnualReturn": 8 if portfolio.target.currency == schemas.Currency.USD else 20
            })
        return {"recomendation": result, "growthDuration": growth_duration}

      else: 
        products = db.execute(base_query.where(base_model.horizon == portfolio.duration).limit(3)).scalars().all()
        for product in products:
          result.append({
            "product": product,
            "estAnnualReturn": 8 if portfolio.target.currency == schemas.Currency.USD else 20
          })
        return {"recomendation": result}
        

@advisory.post("/wealth-objective")
async def createWealthObjective(db: db, objective: schemas.WealthObjectiveCreate):
  wealthObjective = model.WealthObjective(**objective.model_dump())
  db.add(wealthObjective)
  db.commit()
  db.refresh(wealthObjective)
  return wealthObjective


async def getIndependenceRequiredInvestment(db: db, user: model.User):

  age = relativedelta(datetime.now(), user.dateOfBirth).years
  years_to_retirement = 60 - age

  # get total assets value 
  total_assets = await getUserValue(db, user)
  total_value_usd = total_assets.get("totalValueUsd")
  total_value_ngn = total_assets.get("totalValueNgn")
  # get annual income
  annual_income = user.riskProfile.monthly_income * 12 if user.riskProfile.monthly_income is not None else 0

  if user.riskProfile.primary_income_currency == schemas.Currency.USD:
    required_investment = float(annual_income) / 0.02
    difference = required_investment - total_value_usd
    usd_long_term_inflation = 0.02
    fv = npf.fv(usd_long_term_inflation, years_to_retirement, 0, -difference)
  elif user.riskProfile.primary_income_currency == schemas.Currency.NGN:
    required_investment = float(annual_income) / 0.18
    difference = required_investment - total_value_ngn
    ngn_long_term_inflation = 0.10
    fv = npf.fv(ngn_long_term_inflation, years_to_retirement, 0, -difference)

  else:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid risk profile")

  return {
    "requiredFutureValue": fv,
    "currency": user.riskProfile.primary_income_currency,
    "yearsToRetirement": years_to_retirement,
    "requiredInvestment": required_investment,
  }

@advisory.get("/portfolio-recommendation", )
async def getPortfolioRecommendation(db: db, user: Annotated[model.User, Depends(getUserRiskProfile)]):

  user_portfolios = user.portfolios
  portfolio_ids = [portfolio.wealthObjectiveId for portfolio in user_portfolios if portfolio.wealthObjectiveId is not None]

  recommended = select(model.WealthObjective).where(model.WealthObjective.id.not_in(portfolio_ids))
  recommended = db.execute(recommended).scalars().all()

  result = []
  required_investment = await getIndependenceRequiredInvestment(db, user)

  for objective in recommended:
    if objective.category == schemas.WealthObjectiveCategory.RETIREMENT:
      # calulate independence required investment
      result.append({
        "objective": objective,
        "amount": required_investment.get("requiredFutureValue"),
        "timeToTarget": required_investment.get("yearsToRetirement"),
        "currency": required_investment.get("currency"),
        "targetDate": datetime.now() + relativedelta(years=required_investment.get("yearsToRetirement"))
      })

    if objective.category == schemas.WealthObjectiveCategory.INDEPENDENCE:
      result.append({
        "objective": objective,
        "amount": required_investment.get("requiredInvestment"),
        "currency": required_investment.get("currency"),
      })

    if objective.category == schemas.WealthObjectiveCategory.NRENT:

      annual_rent = user.riskProfile.annual_rent

      result.append({
        "objective": objective,
        "amount": annual_rent,
        "currency": user.riskProfile.primary_income_currency,
        "targetDate": datetime.now() + relativedelta(years=1)
      })

    if objective.category == schemas.WealthObjectiveCategory.ARENT:
      # get annual rent // estimated annual rent
      annual_rent = user.riskProfile.annual_rent
      result.append({
        "objective": objective,
        "amount": annual_rent,
        "currency": user.riskProfile.primary_income_currency,
      })

    if objective.category == schemas.WealthObjectiveCategory.MEXPENSE:

      # 40% of monthly income as estimated basic living expenses
      pass


  return {  
    "result": result,
    "recommended": recommended

  }



