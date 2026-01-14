from fastapi import APIRouter, Depends, HTTPException, Query, status, Security
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import db
import model
import schemas
from ..v1 import auth
from typing import Annotated, Optional
from sqlalchemy import select, func, case
from datetime import datetime
from ..v1.journal import prepareJournal
from ..v1.user import getUser

wallet = APIRouter(
    prefix="/wallet",
    tags=["wallet"]
)

@wallet.post('/')
async def createWallet(
  db: db,
  walletGroupId: int,
  user: Annotated[model.User, Security(getUser, scopes=["createUser"])]):

  wallet = db.execute(select(model.Wallet).where(model.Wallet.userId == user.id, model.Wallet.walletGroupId == walletGroupId)).scalar_one_or_none()

  if wallet is not None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet already exists")
  else: 
    new_wallet = model.Wallet(userId=user.id, walletGroupId=walletGroupId)
    db.add(new_wallet)
    db.commit()
    db.refresh(new_wallet)
    return new_wallet

@wallet.get('/')
async def getUserWallet(
  db: db,
  user: Annotated[model.User, Security(getUser, scopes=["readUser"])],
  walletId: int,
  ):

  wallet = db.execute(select(model.Wallet).where(model.Wallet.userId == user.id, model.Wallet.id == walletId)).scalar_one_or_none()
  
  if wallet is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
  return wallet

class WalletBalanceStore(BaseModel):
  balance: float
  last_request: datetime

@wallet.get('/balance')
async def getWalletBalance(
  db: db,
  wallet: Annotated[model.Wallet, Depends(getUserWallet)],
  last_request: Optional[datetime] = None
):

  net_inflow_query = (
    select(
        func.sum(
            case(
                (model.WalletTransaction.type == schemas.TransactionType.INVESTMENT.name, -model.WalletTransaction.amount),
                (model.WalletTransaction.type == schemas.TransactionType.LIQUIDATION.name, model.WalletTransaction.amount),
                (model.WalletTransaction.type == schemas.TransactionType.FEE.name, -model.WalletTransaction.amount),
                (model.WalletTransaction.type == schemas.TransactionType.TAX.name, -model.WalletTransaction.amount),
                (model.WalletTransaction.type == schemas.TransactionType.DEPOSIT.name, model.WalletTransaction.amount),
                (model.WalletTransaction.type == schemas.TransactionType.WITHDRAWAL.name, -model.WalletTransaction.amount),
                else_=0
            )
        ).label("net_inflow")
    )
    .where(model.WalletTransaction.walletId == wallet.id, model.WalletTransaction.status == schemas.TransactionStatus.COMPLETED)
)

  net_inflow = db.execute(net_inflow_query).scalar()
  net_inflow = 0 if net_inflow is None else net_inflow
  return {
    "balance": float(net_inflow / 100),
    "last_request": datetime.now(),
    "wallet": wallet,
  }

@wallet.get('/transactions')
async def getWalletTransactions(
  db: db,
  wallet: Annotated[model.Wallet, Depends(getUserWallet)],
  status: Annotated[Optional[schemas.TransactionStatus], Query()] = None,
):
  base_query = select(model.WalletTransaction).where(model.WalletTransaction.walletId == wallet.id).order_by(model.WalletTransaction.date.desc())  
  transactions = db.execute(base_query).scalars().all()
  if status:
    base_query = base_query.where(model.WalletTransaction.status == status)
  transactions = db.execute(base_query).scalars().all()
  return transactions

async def generateWalletTransaction(
    amount: float,
    type: schemas.TransactionType,
    db: db,
    wallet: model.Wallet,
    date: datetime
):

    amount = int(amount * 100)
    if wallet.active == False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet is not active")
    
    if type in [schemas.TransactionType.INVESTMENT, schemas.TransactionType.WITHDRAWAL]:
      # get current balance
      balance = await getWalletBalance(db=db, wallet=wallet)
      # check if balance is sufficient
      if balance.get("balance") < amount:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")
    # create transaction journal
    transaction_journal = model.Journal(date=date)

    funding_account_id = wallet.walletGroup.receivableAccountId if type == schemas.TransactionType.DEPOSIT or type == schemas.TransactionType.LIQUIDATION else 15
    wallet_account_id = wallet.walletGroup.holdingAccountId

    funding_entry_type = schemas.EntrySide.DEBIT if type == schemas.TransactionType.DEPOSIT or type == schemas.TransactionType.LIQUIDATION else schemas.EntrySide.CREDIT
    wallet_entry_type = schemas.EntrySide.CREDIT if type == schemas.TransactionType.DEPOSIT or type == schemas.TransactionType.LIQUIDATION else schemas.EntrySide.DEBIT
    
    # funding account entry
    funding_account_entry = model.JournalEntry(
        accountId=funding_account_id,
        amount=amount,
        side=funding_entry_type,
        description=f"Wallet: {wallet.id} - {type.value} transaction"
    )

    # wallet account entry
    wallet_account_entry = model.JournalEntry(
        accountId=wallet_account_id,
        amount=amount,
        side=wallet_entry_type,
        description=f"Wallet: {wallet.id} - {type.value} transaction"
    )

    if wallet_account_entry.amount != funding_account_entry.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount mismatch")

    transaction_journal.entries.append(wallet_account_entry)
    transaction_journal.entries.append(funding_account_entry)
    db.add(transaction_journal)

    wallet_trx = model.WalletTransaction(amount=amount, type=type, status=schemas.TransactionStatus.COMPLETED, walletId=wallet.id, date=date)
    wallet_trx.settled = True if type not in [schemas.TransactionType.DEPOSIT, schemas.TransactionType.LIQUIDATION] else False
    wallet_trx.journal = transaction_journal
    db.add(wallet_trx)
    db.commit()
    db.refresh(wallet_trx)

    return {"transaction": wallet_trx, "message": "Transaction initialized"}

@wallet.post('/transaction')
async def postWalletTransaction(
  db: db,
  amount: float,
  type: schemas.TransactionType,
  wallet: Annotated[model.Wallet, Security(getUserWallet, scopes=["createUser"])],
  date: Annotated[datetime, Query(le=datetime.now(), description="Transaction date")] = datetime.now(),
):

  return await generateWalletTransaction(
    amount=amount, 
    type=type, 
    db=db, 
    wallet=wallet, 
    date=date)

@wallet.post('/group')
async def createWalletGroup(
  db: db,
  walletGroupData: schemas.WalletGroupCreate
):
  
  new_wallet_group = model.WalletGroup(**walletGroupData.model_dump())
  db.add(new_wallet_group)
  db.commit()
  db.refresh(new_wallet_group)
  return new_wallet_group