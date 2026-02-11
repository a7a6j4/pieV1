import asyncio
from model import PortfolioTransaction
import uuid
from fastapi import APIRouter, Depends, status, HTTPException, Query, Security
from fastapi.security import SecurityScopes
from sqlalchemy.orm import Session, join
from sqlalchemy import select, func, case, and_, or_
from router.v1.portfolio import getPortfolioValue
import celery_app
from ..v1 import auth
from database import db
import model
import schemas
from typing import Annotated, Union, Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
from ..v1.portfolio import getPortfolio
from ..v1.deposit import getLiquidationValue
from ..v1.journal import prepareJournal
from ..v1.wallet import generateWalletTransaction, getWalletBalance
from ..v1.product import getPrice

transaction = APIRouter(prefix="/transaction", tags=["transaction"])

@transaction.get("/")
async def getTransaction(
    transaction_id: int,
    db: db,
):
    transaction = db.get(model.PortfolioTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if transaction.category == "deposittransaction":
        return db.get(model.DepositTransaction, transaction_id)
    elif transaction.category == "variabletransaction":
        return db.get(model.VariableTransaction, transaction_id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid transaction category")

@transaction.get("/status")
async def getTransactionStatus(
    transaction_id: int,
    db: db,
):
    transaction = db.get(model.PortfolioTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction.status

@transaction.get("/batch")
async def getTransactionBatch(
    batch_id: uuid.UUID,
    db: db,
):
    batch = db.get(model.TransactionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return batch

def getDbProduct(
    productId: int,
    db:  db
):
    product = db.get(model.Product, productId)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {productId} not found",
        )
    if product.category == "variable":
        return db.get(model.Variable, productId)
    if product.category == "deposit":
        return db.get(model.Deposit, productId)
    
def calculateConsideration(product: model.Variable | model.Deposit, amount: float, side: schemas.TransactionType, db: db):
    
    all_fees = []    
    if product.productGroup.transactionFees is not None:
        for fee in product.productGroup.transactionFees:
            _fee = fee.transactionFee
            fee_amount = int((_fee.fee / 100) if _fee.feeType == schemas.FeeType.FLAT else (_fee.fee / 10000) * amount)
            all_fees.append({
                "fee": _fee.title,
                "amount": int(fee_amount)
            })

            if _fee.vat:
                all_fees.append({
                    "fee": f"VAT on {_fee.title}",
                    "amount": int(fee_amount * 0.0075)
                })
    total_fees = sum(map(lambda x: x["amount"], all_fees))
    total = amount + total_fees if side == schemas.TransactionType.INVESTMENT else amount - total_fees
    return {
        "fees": all_fees,
        "netConsideration": total
    }

@transaction.post("/consideration")
async def getTransactionConsideration(
    db: db,
    orders: list[schemas.PurchaseOrder],
    type: str = Query(enum=["purchase", "sale"]),
):

    products = map(lambda x: {"product": getDbProduct(x.productId, db=db), "amount": x.amount, "tenor": None if x.tenor is None else x.tenor}, orders)
    consideration = list(map(lambda x: {"product": x["product"], "amount": x["amount"], "tenor": x["tenor"], "consideration": calculateConsideration(product=x["product"], amount=x["amount"], side=schemas.TransactionType.INVESTMENT if type == "purchase" else schemas.TransactionType.LIQUIDATION, db=db)}, products))
    total_consideration = sum(x["consideration"]["netConsideration"] for x in consideration)
    return {
        "orderBook": consideration,
        "totalConsideration": total_consideration
    }

@transaction.post("/coverage")
async def getTransactionCoverage(
    db: db,
    wallet = Depends(getWalletBalance),
    consideration: dict = Depends(getTransactionConsideration),
):
    # balance = wallet["balance"]
    balance = wallet.data.availableBalance
    # check if user has sufficient funds
    if balance < consideration["totalConsideration"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds",
        )
    return {
        **consideration
    }

@transaction.post("/execute")
async def executeTransaction(
    batch: Annotated[model.TransactionBatch, Depends(getTransactionBatch)]):
    if batch.executed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transactions already executed")

    # separate transactions by product group
    ng_mutual_funds = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.MUTUAL_FUND and x.product.productGroup.market == schemas.Country.NG, batch.portfolio_transactions))
    ng_deposits = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.DEPOSIT and x.product.productGroup.market == schemas.Country.NG, batch.portfolio_transactions))
    us_stocks = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.EQUITY and x.product.productGroup.market == schemas.Country.US, batch.portfolio_transactions))
    ng_stocks = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.EQUITY and x.product.productGroup.market == schemas.Country.NG, batch.portfolio_transactions))

    if ng_mutual_funds:
        for mutual_fund_transaction in ng_mutual_funds:
            celery_app.executeMutualFundTransactionTask.delay(portfolio_transaction_id=mutual_fund_transaction.id)

    if ng_deposits:
        for deposit_transaction in ng_deposits:
            celery_app.bookPortfolioDepositTask.delay(deposit_transaction_id=deposit_transaction.id)
    if us_stocks:
        for stock_transaction in us_stocks:  
            celery_app.executeAlpacaTransactionTask.delay(portfolio_transaction_id=stock_transaction.id)

    if ng_stocks:
        for stock_transaction in ng_stocks:
            celery_app.executeNGXTransactionTask.delay(portfolio_transaction_id=stock_transaction.id)

    return {
        "message": "Transactions execution initiated",
    }

async def settleTransaction(
    db: db,
    batch: model.TransactionBatch,
):
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch

@transaction.post("/purchase")
async def postTransaction(
    db: db,
    orderBook = Depends(getTransactionCoverage),
    portfolio = Security(getPortfolio, scopes=["createUser"]),
    date: datetime = datetime.now(),
):
    batch = model.TransactionBatch()

    for order in orderBook["orderBook"]:
        currency = order["product"].currency
        wallet_journal = model.Journal(
            date=datetime.now()
        )

        accounting_amount = (order["amount"] * 1470 if order["product"].currency == schemas.Currency.USD else order["amount"]) * 100
        transaction_amount = order["amount"]

        consideration_wallet_transaction = model.WalletTransaction(
            amount=accounting_amount,
            type=schemas.TransactionType.INVESTMENT,
            status=schemas.TransactionStatus.COMPLETED,
            walletId=orderBook["wallet"].id,
            date=datetime.now(),
        )

        # debit wallet for consideration
        wallet_entry = model.JournalEntry(
            accountId=13 if currency == schemas.Currency.USD else 14,
            amount=accounting_amount,
            side=schemas.EntrySide.DEBIT,
            description=f"{order["product"].title} investment purchase consideration"
        )
        # credit transaction payable for consideration
        payable_entry = model.JournalEntry(
            accountId=order["product"].productGroup.receivableAccountId,
            amount=accounting_amount,
            side=schemas.EntrySide.CREDIT,
            description=f"{order["product"].title} investment purchase consideration"
        )

        wallet_journal.entries.append(wallet_entry)
        wallet_journal.entries.append(payable_entry)
        consideration_wallet_transaction.journal = wallet_journal
        db.add(consideration_wallet_transaction)

        # book fee transctions
        if order.get("consideration", {}).get("fees") is not None:
            for fee in order.get("consideration", {}).get("fees"):

                fee_amount = int((fee["amount"] * 1470 if currency == schemas.Currency.USD else fee["amount"]) * 100)
            # book fee wallet transaction
                fee_transaction = model.WalletTransaction(
                    amount=fee_amount,
                    type=schemas.TransactionType.FEE,
                    status=schemas.TransactionStatus.COMPLETED,
                    walletId=orderBook["wallet"].id,
                    journal=wallet_journal,
                    date=datetime.now()
                )
            # debit wallet for fee
                fee_wallet_entry = model.JournalEntry(
                    accountId=13 if currency == schemas.Currency.USD else 14,
                    amount=fee_amount,
                    side=schemas.EntrySide.DEBIT,
                    description=f"{fee} fee",
                    journal=wallet_journal
                )
            # credit payable for fee
                fee_payable_entry = model.JournalEntry(
                    accountId=order["product"].productGroup.payableAccountId,
                    amount=fee_amount,
                    side=schemas.EntrySide.CREDIT,
                    description=f"{fee} fee",
                    journal=wallet_journal
                )
                wallet_journal.entries.append(fee_wallet_entry)
                wallet_journal.entries.append(fee_payable_entry)
                db.add(fee_transaction)
        db.add(wallet_journal)

        # create product transaction for variable and deposit products
        if order["product"].category == "variable":
            # get product price
            price = (await getPrice(db=db, variable_id=order["product"].id))
            units = int(transaction_amount / price)
            port_transaction = model.VariableTransaction(
                productId=order["product"].id,
                amount=accounting_amount,
                type=schemas.TransactionType.INVESTMENT,
                status=schemas.TransactionStatus.PENDING,
                portfolioId=portfolio.id,
                date=datetime.now(),
                units=units,
                price=int(price * 100),
                settlement=schemas.TransactionStatus.PENDING,
            )
            port_transaction.batch = batch
        
        if order["product"].category == "deposit":
            port_transaction = model.DepositTransaction(
                productId=order["product"].id,
                amount=accounting_amount,
                type=schemas.TransactionType.INVESTMENT,
                status=schemas.TransactionStatus.PENDING,
                portfolioId=portfolio.id,
                date=datetime.now(),
                tenor=order["tenor"],
                rate=order["product"].rate,
                settlement=schemas.TransactionStatus.PENDING,
            )
            port_transaction.batch = batch


        association = model.PortfolioWalletTransactionAssociation(wallet_transaction=consideration_wallet_transaction)
        port_transaction.wallet_transaction_associations.append(association)
        db.add(consideration_wallet_transaction)
        db.add(batch)

    db.commit()
    db.refresh(batch)
    # separate transactions by product group
    ng_mutual_funds = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.MUTUAL_FUND and x.product.productGroup.market == schemas.Country.NG, batch.portfolio_transactions))
    ng_deposits = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.DEPOSIT and x.product.productGroup.market == schemas.Country.NG, batch.portfolio_transactions))
    us_stocks = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.EQUITY and x.product.productGroup.market == schemas.Country.US, batch.portfolio_transactions))
    ng_stocks = list(filter(lambda x: x.product.productGroup.productClass == schemas.ProductClass.EQUITY and x.product.productGroup.market == schemas.Country.NG, batch.portfolio_transactions))

    if ng_mutual_funds:
        for mutual_fund_transaction in ng_mutual_funds:
            celery_app.executeMutualFundTransactionTask.delay(portfolio_transaction_id=mutual_fund_transaction.id)

    if ng_deposits:
        for deposit_transaction in ng_deposits:
            celery_app.bookPortfolioDepositTask.delay(deposit_transaction_id=deposit_transaction.id)

    if us_stocks:
        for stock_transaction in us_stocks:
            celery_app.executeAlpacaTransactionTask.delay(portfolio_transaction_id=stock_transaction.id)

    if ng_stocks:
        for stock_transaction in ng_stocks:
            celery_app.executeNGXTransactionTask.delay(portfolio_transaction_id=stock_transaction.id)

    return {"message": "Transaction initialized", "batch": batch.id}

async def checkAssetAvailability(
    db: db,
    orders: list[schemas.SaleOrder],
    assets = Depends(getPortfolioValue),
):
    variables = list(filter(lambda x: x["category"] == "variable", assets))
    variable_orders = list(filter(lambda x: x.type == schemas.ProductCategory.VARIABLE, orders))
    for order in variable_orders:
        variable = next((asset for asset in variables if asset["product"].id == order.id), None)
        if variable is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Variable {order.id} not found")
        if variable["current_value"] < order.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Variable {order.id} has insufficient funds")
    
    deposits = list(filter(lambda x: x["category"] == "deposit", assets))
    deposit_orders = list(filter(lambda x: x.type == schemas.ProductCategory.DEPOSIT, orders))
    for order in deposit_orders:
        deposit = next((asset for asset in deposits if asset["deposit"].id == order.id), None)
        if deposit is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Deposit {order.id} not found")
        if deposit["current_value"] < order.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Deposit {order.id} has insufficient funds")

    return {
        "variable_orders": variable_orders,
        "deposit_orders": deposit_orders,
    }

