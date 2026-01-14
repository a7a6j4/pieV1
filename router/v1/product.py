from click import utils
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Query, Path, Body
from database import db
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session, joinedload
from typing import Optional, Annotated, Union, List
import model
import yfinance as yf
import requests
from decimal import Decimal
import schemas
from pydantic import BaseModel
from datetime import datetime, timedelta, date
import statistics
import dotenv
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np  
from ..v1.auth import readUser
from utils import tiingo
from config import settings

load_dotenv()

VANTAGE_API_KEY = os.getenv("VANTAGE_KEY")

product = APIRouter(
    prefix="/product",
    tags=["product"]
)

@product.get('/', dependencies=[Depends(readUser)])
async def getProduct(
  db: db,
  productId: Optional[int] = Query(default=None, description="Product ID"),
  productClass: Optional[schemas.ProductClass] = Query(default=None),
  page: Optional[int] = Query(default=1),
  type: Optional[str] = Query(enum=["variable", "deposit"], default=None),
  limit: Optional[int] = Query(default=10)):


  if productId:
    product = db.query(model.Product).filter(model.Product.id == productId).first()
    if not product:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.category == "variable":
      return db.query(model.Variable).filter(model.Variable.id == productId).first()
    elif product.category == "deposit":
      return db.query(model.Deposit).filter(model.Deposit.id == productId).first()
  else:
    base_query = db.query(model.Product)
     
    if productClass:
      base_query = base_query.filter(model.Product.product_class == productClass)
    if type:
      base_query = base_query.filter(model.Product.category == type)
    if page and limit:
      base_query = base_query.offset((page - 1) * limit).limit(limit)
    return base_query.options(joinedload(model.Variable.attributes)).all()

@product.post('/issuer', response_model=schemas.IssuerSchema)
async def createIssuer(issuer_data: schemas.IssuerCreate, db: db):
  new_issuer = model.Issuer(**issuer_data.model_dump())
  db.add(new_issuer)
  db.commit()
  db.refresh(new_issuer)
  return new_issuer

@product.get('/issuer', response_model=List[schemas.IssuerSchema])
async def getIssuers(db: db):
  issuers = db.execute(select(model.Issuer)).scalars().all()
  return issuers

@product.get('/issuer/{issuer_id}', response_model=schemas.IssuerSchema)
async def getIssuer(issuer_id: int, db: db):
  issuer = db.get(model.Issuer, issuer_id)
  if not issuer:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issuer not found")
  return issuer

@product.get('/group')
async def getProductGroups(db: db, groupId: Optional[int] = Query(default=None)):
  if groupId:
    product_group = db.get(model.ProductGroup, groupId)
    if not product_group:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product group not found")
    return product_group
  else:
    product_groups = db.execute(select(model.ProductGroup)).scalars().all()
  return product_groups

@product.post('/fees', response_model=schemas.TransactionFeeSchema)
async def createTransactionFee(
  db: db,
  feeData: schemas.TransactionFeeCreate,
  ):

  new_transaction_fee = model.TransactionFee(**feeData.model_dump())

  db.add(new_transaction_fee)
  db.commit()
  db.refresh(new_transaction_fee)
  return new_transaction_fee  

@product.post("/group", response_model=schemas.ProductGroupSchema)
async def createProductGroup(
  db: db,
  groupData: schemas.ProductGroupCreate
):

  new_product_group = model.ProductGroup(**groupData.model_dump(exclude={'feeIds'}))
  if groupData.feeIds:
    for fee in groupData.feeIds:
      association = model.ProductGroupFees(TransactionFeeId=fee)
      new_product_group.transactionFees.append(association)
  db.add(new_product_group)
  db.commit()
  db.refresh(new_product_group)
  return new_product_group

@product.patch("/group")
async def updateProductGroup(
  db: db,
  productGroupId: int,
  groupData: schemas.ProductGroupUpdate,
):

  new_product_group = db.get(model.ProductGroup, productGroupId)
  if not new_product_group:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product group not found")

  new_product_group.name = groupData.name if groupData.name is not None else new_product_group.name
  new_product_group.description = groupData.description if groupData.description is not None else new_product_group.description
  new_product_group.market = groupData.market if groupData.market is not None else new_product_group.market

  if groupData.feeIds:
    new_product_group.transactionFees = []
    for fee in groupData.feeIds:
      dbFee = db.get(model.TransactionFee, fee)
      if not dbFee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction fee not found")
      association = model.ProductGroupFees()
      association.transactionFee = dbFee
      new_product_group.transactionFees.append(association)

  db.add(new_product_group)
  db.commit()
  db.refresh(new_product_group)  
  return new_product_group

@product.post('/variable', response_model=schemas.ProductSchema)
async def createProduct(
  db: db,
  product_data: schemas.VariableCreate,
  issuer = Depends(getIssuer),
):

  new_product = model.Variable(**product_data.model_dump())
  new_product.issuer = issuer  
  db.add(new_product)
  db.commit()
  db.refresh(new_product)

  return new_product

@product.post('/deposit', response_model=schemas.ProductGroupSchema)
async def createDeposit(
  db: db,
  product_data: schemas.DepositCreate,
  issuer = Depends(getIssuer),
):

  product_dict = product_data.model_dump()
  new_product = model.Deposit(**product_dict)

  new_product.issuer = issuer
  new_product.productGroupId = product_data.productGroupId
  db.add(new_product)
  db.commit()
  db.refresh(new_product)

  return new_product

@product.post('/bulk')
async def createProducts(db:db, data = Body()):
  
  for product_data in data:
    issuer = model.Issuer(name=product_data.get('name'))
    product = model.Variable(symbol=product_data.get('symbol'), title=issuer.name, risk_level=5, horizon=5, currency=schemas.Currency.NGN, product_class=schemas.ProductClass.EQUITY)
    product.issuer = issuer
    db.add(product)
  
  db.commit()
  return {"message": "Products created successfully"}


class BulkIn(BaseModel):
  name: str
  riskLevel: int
  duration: int
  issuerName: str
  currency: str
  symbol: str
  type: str

# @product.post('/bulk-ticket')
async def addBulkPolygon(db: db, tickers: List[BulkIn]):

  for ticker in tickers:
    issuerCheck = db.execute(select(model.Issuer).where(model.Issuer.name == ticker.issuerName)).scalar_one_or_none()

    if issuerCheck is None:
      issuer = model.Issuer(name=ticker.issuerName)
    else:
      issuer = issuerCheck

    product = model.Variable(symbol=ticker.symbol, title=ticker.name, risk_level=ticker.riskLevel, horizon=ticker.duration, currency=ticker.currency, product_class=ticker.type)
    product.issuer = issuer
    db.add(product)
  
  db.commit()

@product.get('/variable')
async def getVariable(db: db, variable_id: int):
  variable = db.get(model.Variable, variable_id)
  if not variable:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variable not found")
  
  return variable

@product.get('/analysis')
async def getProductAnalysis(db: db, 
                             product = Depends(getVariable)
                             ):

  benchmark = product.benchmark

  if benchmark is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark not found")

  if product.values is None or benchmark.history is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product values or benchmark history not found")
  
  if (product.product_class == schemas.ProductClass.EQUITY or product.product_class == schemas.ProductClass.ETF) and product.currency == schemas. Currency.USD:
    response = requests.get(f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={product.symbol}&outputsize=full&apikey={VANTAGE_API_KEY}").json()
    # Extract date and close price
    ts = response.get('Time Series (Daily)', {})
    price_records = [
      {"date": date, "price": float(values["4. close"])}
      for date, values in ts.items()
    ]
    price_df = pd.DataFrame(price_records)
    price_df['date'] = pd.to_datetime(price_df['date'])
    price_df = price_df.sort_values('date')
    price_df['return'] = price_df['price'].pct_change()
    # Convert to list of dicts with string dates and daily_return as float or None
    price_with_returns = [
      {
        "date": row['date'].strftime('%Y-%m-%d'),
        "price": row['price'],
        "daily_return": row['return'] if pd.notnull(row['return']) else None
      }
      for _, row in price_df.iterrows()
    ]
    historical_data = price_df['price']
  elif (product.product_class in [schemas.ProductClass.EQUITY, schemas.ProductClass.ETF, schemas.ProductClass.FUND, schemas.ProductClass.FUND]) and product.currency == schemas.Currency.NGN:
    # Extract date and value from product.values
    value_records = [
      {"date": v.date, "price": float(v.value)}
      for v in product.values 
    ]
    value_df = pd.DataFrame(value_records)
    value_df['date'] = pd.to_datetime(value_df['date'])
    value_df = value_df.sort_values('date')
    value_df['return'] = value_df['price'].pct_change()
    price_with_returns = [
      {
        "date": row['date'].strftime('%Y-%m-%d'),
        "price": row['price'],
        "daily_return": row['return'] if pd.notnull(row['return']) else None
      }
      for _, row in value_df.iterrows()
    ]
    historical_data = value_df['price']
    
  # product stats
  product_returns = [row['daily_return'] for row in price_with_returns if row['daily_return'] is not None]
  product_return_std = float(np.std(product_returns, ddof=1)) if product_returns else None
  product_return_variance = float(np.var(product_returns, ddof=1)) if product_returns else None
    
  # benchmark stats
  if benchmark.source == schemas.DataSource.API :
    pass
  elif benchmark.source == model.DataSource.LOCAL:
    # Extract date and value from benchmark.history
    bh_records = [
      {"date": h.date, "price": float(h.value)}
      for h in benchmark.history
    ]
    bh_df = pd.DataFrame(bh_records)
    bh_df['date'] = pd.to_datetime(bh_df['date'])
    bh_df = bh_df.sort_values('date')
    bh_df['daily_return'] = bh_df['price'].pct_change()
    benchmark_price_with_returns = [
      {
        "date": row['date'].strftime('%Y-%m-%d'),
        "price": row['price'],
        "daily_return": row['daily_return'] if pd.notnull(row['daily_return']) else None
      }
      for _, row in bh_df.iterrows()
    ]
  
  # Calculate variance and std of daily benchmark returns
  if 'benchmark_price_with_returns' in locals() and benchmark_price_with_returns:
    benchmark_returns = [row['daily_return'] for row in benchmark_price_with_returns if row['daily_return'] is not None]
    benchmark_return_std = float(np.std(benchmark_returns, ddof=1)) if benchmark_returns else None
    benchmark_return_variance = float(np.var(benchmark_returns, ddof=1)) if benchmark_returns else None
  else:
    benchmark_return_std = None
    benchmark_return_variance = None

  # correlation and beta (limit to last 2530 records or product row count)
  product_df = pd.DataFrame(price_with_returns)
  benchmark_df = pd.DataFrame(benchmark_price_with_returns) if 'benchmark_price_with_returns' in locals() and benchmark_price_with_returns else pd.DataFrame()

  if not product_df.empty and not benchmark_df.empty:
      merged = pd.merge(
          product_df[['date', 'daily_return']],
          benchmark_df[['date', 'daily_return']],
          on='date',
          suffixes=('_product', '_benchmark')
      )
      merged = merged.dropna(subset=['daily_return_product', 'daily_return_benchmark'])
      # N is the minimum of 2530 or the number of product return rows
      N = min(2530, len(merged))
      merged = merged.sort_values('date').tail(N)
      if not merged.empty:
          product_returns = merged['daily_return_product'].values
          benchmark_returns = merged['daily_return_benchmark'].values
          correlation = float(np.corrcoef(product_returns, benchmark_returns)[0, 1])
          beta = float(np.cov(product_returns, benchmark_returns, ddof=1)[0, 1] / np.var(benchmark_returns, ddof=1))
      else:
          correlation = None
          beta = None
  else:
      correlation = None
      beta = None

  if product.character is None:
    character = model.VariableCharacter(
      std_dev=product_return_std,
      variance=product_return_variance,
      beta=beta,
      variable=product
    )
  else:
    character = product.character
    character.std_dev = product_return_std
    character.variance = product_return_variance
    character.beta = beta

  db.add(character)
  db.commit()
  db.refresh(character)

  return {"message": "Product character added successfully", "character": character}


@product.patch('/')
async def updateProduct(db: db):

  for product in db.execute(select(model.Variable)).scalars().all():
    if product.product_class == schemas.ProductClass.EQUITY and product.currency == schemas.Currency.USD:
      product.benchmark_id = 3
      db.add(product)
  
  db.commit()
  return {"message": "Products updated successfully"}

# @product.post('/value')
# async def addProductValue(db: db, 
#                           data: list[schemas.VariableValueCreate], 
#                           id: int,
#                           type: str = Query(enum=['INDEX', 'PRODUCT']),
# ):
  
#   if type == 'INDEX':
#     benchmark = await getBenchmark(db, id)
#     for value in data:
#       new_value = model.BenchmarkMeta(**value.model_dump())
#       benchmark.history.append(new_value)
#       db.add(benchmark)
#   elif type == 'PRODUCT':
#     product = await getVariable(db, id)
#     for value in data:
#       new_value = model.VariableValue(**value.model_dump())
#       product.values.append(new_value)
#       db.add(product)

  db.commit()
  return {"message": "Product values added successfully"}

class BulkValueIn(BaseModel):
  date: datetime
  value: float
  ticker: str


@product.post('/bulk-value')
async def addBulkValue(db: db, 
                       data: list[schemas.VariableValueCreate],
                       ):

  seen = set()
  unique_items = []
  for item in data:
    key = (item.date, item.var_id)
    if key not in seen:
        unique_items.append(item)
        seen.add(key)

  max_id = db.execute(select(func.max(model.VariableValue.id))).scalar_one_or_none()
  if max_id is None:
    max_id = 0

  for value in unique_items:
    
    stock = db.get(model.Variable, value.var_id)

    if stock is not None:
      new_value = model.VariableValue(**value.model_dump(exclude={'var_id'}), id=max_id + 1)
      stock.values.append(new_value)
      db.add(stock)
      max_id += 1 
    
  db.commit()
  return {"message": "Product values added successfully"}


class TestIn(BaseModel):
  id: str

@product.post('/test')
async def test(db: db):

  products = db.execute(select(model.Variable).where(model.Variable.product_class == schemas.ProductClass.FUND, model.Variable.currency == schemas.Currency.NGN, model.Variable.risk_level == 5)).scalars().all()

  for product in products:
    product.benchmark_id = 2
    db.add(product)

  db.commit()
  return {"message": "Products updated successfully"}
  # df = pd.DataFrame()

  # for item in data:
  #   response = requests.get(f"https://dashboard.cowrywise.com/api/v2/funds/{item.id}/price-history/?days=2533").json()

  #   data = response.get('data')
  #   for item in data:
  #     df = pd.concat([df, pd.DataFrame([item])])

  # df.to_excel('output.xlsx', index=False)
  # return {"message": "Product values added successfully"}

@product.get('/ngx/price')
async def getNGXPrice(ticker: str):
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={settings.VANTAGE_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        price = float(data["Global Quote"]["05. price"])
        return price
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get price for {ticker}: {response.text}")

@product.get('/us/price')
async def getUSPrice(ticker: str):
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={settings.VANTAGE_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        price = float(data["Global Quote"]["05. price"])
        return price
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get price for {ticker}: {response.text}")

@product.get('/mutual-fund/price')
async def getNGMutualFundPrice():
    mutual_fund_value = db.execute(select(model.VariableValue).where(model.VariableValue.variableId == variable.variableId).order_by(model.VariableValue.date.desc()).limit(1)).scalar_one_or_none()
    return mutual_fund_value.price

@product.get('/price')
async def getPrice(db: db, variable_id: int):

  variable = db.get(model.Variable, variable_id)
  if variable is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Variable {variable_id} not found")
  if variable.productGroup.productClass == (schemas.ProductClass.EQUITY or schemas.ProductClass.ETF) and variable.productGroup.market == schemas.Country.NG:
    return 100.00
  elif variable.productGroup.productClass in [schemas.ProductClass.EQUITY, schemas.ProductClass.ETF] and variable.productGroup.market == schemas.Country.US:
    return 5.00
    # return await tiingo.tiingo.getStockPrice(variable.symbol)
    # return await utils.vantage.getUSPrice(variable.symbol)
  elif variable.productGroup.productClass == schemas.ProductClass.MUTUAL_FUND and variable.productGroup.market == schemas.Country.NG:
    return await getNGMutualFundPrice()
  else:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Variable {variable_id} is not an equity product")





