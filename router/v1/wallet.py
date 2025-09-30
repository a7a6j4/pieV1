from fastapi import APIRouter, Depends, HTTPException, Query, status, Security
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...database import db
from ... import model
from ... import schemas
from . import auth
from typing import Annotated, Optional
from sqlalchemy import select, func, case
from datetime import datetime
from .journal import prepareJournal

wallet = APIRouter(
    prefix="/wallet",
    tags=["wallet"]
)

@wallet.get('/')
async def getWallet(
  db: db,
  wallet_id: Optional[int] = Query(default=None, description="Wallet_ID is required for admin to get wallet data"),
  currency: Optional[model.Currency] = Query(default=None, description="Currency is required for admin to get wallet data"),
  payload = Security(auth.readUser, scopes=["readUser"])):

  if payload.get("token") == "user":
    if currency is None:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Currency query param is required")
    user = select(model.User).where(model.User.email == payload.get("username")).subquery()
    wallet = db.execute(select(model.Wallet).where(model.Wallet.user_id == user.c.id, model.Wallet.currency == currency)).scalar_one_or_none()
  
  if payload.get("token") == "admin":
    if wallet_id is None:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet_id query param is required")
    wallet = db.get(model.Wallet, wallet_id)
  
  if wallet is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
  return wallet

class WalletBalanceStore(BaseModel):
  balance: float
  last_request: datetime

@wallet.get('/balance')
async def getWalletBalance(
  db: db,
  wallet: Annotated[model.Wallet, Depends(getWallet)],
  last_request: Optional[WalletBalanceStore] = None
):

  net_inflow_query = (
    select(
        func.sum(
            case(
                (model.WalletTransaction.type.in_(schemas.inflow_types), model.WalletTransaction.amount),
                (model.WalletTransaction.type.in_(schemas.outflow_types), -model.WalletTransaction.amount),
                else_=0
            )
        ).label("net_inflow")
    )
    .where(model.WalletTransaction.wallet_id == wallet.id)
)

  net_inflow = db.execute(net_inflow_query).scalar()
  net_inflow = 0 if net_inflow is None else net_inflow
  return WalletBalanceStore(balance=net_inflow, last_request=datetime.now())
  # return net_inflow

@wallet.get('/transactions')
async def getWalletTransactions(
  db: db,
  wallet: Annotated[model.Wallet, Depends(getWallet)],
  status: Annotated[Optional[model.TrasnsactionStatus], Query()] = None
):

  base_query = select(model.WalletTransaction).where(model.WalletTransaction.wallet_id == wallet.id).order_by(model.WalletTransaction.date.desc())  
  transactions = db.execute(base_query).scalars().all()
  if status:
    base_query = base_query.where(model.WalletTransaction.status == status)
  transactions = db.execute(base_query).scalars().all()
  return transactions

async def generateWalletTransaction(
    data: schemas.WalletTransactionCreate,
    db: db,
    wallet: model.Wallet
):
    if wallet.active == False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet is not active")
    
    if data.type in [model.TransactionType.BUY, model.TransactionType.INVESTMENT, model.  TransactionType.WITHDRAWAL]:
        # check if wallet has sufficient balance
        balance = await getWalletBalance(wallet=wallet, db=db)
        # balance = await checkWalletBalance(wallet_id=wallet.id, db=db)
        if balance.get("balance", 0) < data.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

    if wallet.currency == model.Currency.USD:
        receivable_id = 57
        payable_id = 21
        wallet_id = 13
        bank = 17
    elif wallet.currency == model.Currency.NGN:
        receivable_id = 56
        payable_id = 21
        wallet_id = 14
        bank = 15
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid currency"
        )

    account_currency = db.get(model.Account, bank)
    if not account_currency or account_currency.currency != wallet.currency or wallet.currency != wallet.currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Currency mismatch"
        )
    wallet_trx = model.WalletTransaction(**data.model_dump(exclude='type'), type=data.type.name, status=model.TrasnsactionStatus.COMPLETED if data.type in [model.TransactionType.WITHDRAWAL, model.TransactionType.DEPOSIT] else model.TrasnsactionStatus.PENDING, currency=wallet.currency)

    wallet_trx.wallet_id = wallet.id

    if data.type in [model.TransactionType.BUY, model.TransactionType.INVESTMENT]:
        debit_account = wallet_id
        credit_account = payable_id
    elif data.type in [model.TransactionType.SELL, model.TransactionType.LIQUIDATION, model.TransactionType.INTEREST]:
        debit_account = receivable_id
        credit_account = wallet_id
    elif data.type in [model.TransactionType.FEE, model.TransactionType.TAX]:
        debit_account = wallet_id
        credit_account = receivable_id
    elif data.type == model.TransactionType.WITHDRAWAL:
        debit_account = wallet_id
        credit_account = bank
    elif data.type ==  model.TransactionType.DEPOSIT:
        debit_account = bank
        credit_account = wallet_id

    debit_entry = model.JournalEntries(amount=data.amount, account_id=debit_account, description=f"{data.type} transaction")
    credit_entry = model.JournalEntries(amount=data.amount, account_id=credit_account, description=f"{data.type} transaction")


    transaction_journal = await prepareJournal(
        credit=[credit_entry],
        debit=[debit_entry]
    )

    wallet_trx.journal = transaction_journal
    return wallet_trx

@wallet.post('/transaction')
async def postWalletTransaction(
  db: db,
  wallet: Annotated[model.Wallet, Depends(getWallet)],
  transaction: schemas.WalletTransactionCreate
):
  transaction = await generateWalletTransaction(transaction, db, wallet)
  db.add(transaction)
  try:
    db.commit()
    db.refresh(transaction)
  except Exception as e:
    db.rollback()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
  return transaction