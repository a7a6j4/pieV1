from fastapi import FastAPI, APIRouter, Depends, status, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from sqlalchemy import func, case, select, and_, or_, text
from database import db
import model
import schemas
from typing import Annotated, Optional, Union, List
from datetime import datetime, date
from ..v1 import auth

account = APIRouter(prefix="/account", tags=["account"])

# Dependency function to get account
async def get_account_by_id(id: int, db: db) -> model.Account:
    account = db.get(model.Account, id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account

@account.post('/', response_model=schemas.AccountSchema)
async def create_account(account_data: schemas.AccountCreate, db: db, header_id: Optional[int] = None):

  if not header_id:
    account_data.parent_id = None
    account_data.is_header = True
  else:
    header_account = db.get(model.Account, header_id)
    if not header_account:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Header account not found")
    if not header_account.is_header:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid header account")
    
    account_data.parent_id = header_id
  
  new_account = model.Account(**account_data.model_dump())
  db.add(new_account)
  db.commit()
  db.refresh(new_account)
  return new_account

@account.get('/')
async def get_account(db: db, id: Optional[int] = None):
  if id:
    account = await get_account_by_id(id, db)
    return account
  else:
    accounts = db.query(model.Account).all()
    return accounts

@account.get('/entries')
async def get_account_entries(
    account: Annotated[model.Account, Depends(get_account_by_id)], 
    db: db,
    start_date: Annotated[Optional[datetime], Field(le=date.today())] = None,
    end_date: Annotated[Optional[datetime], Field(le=date.today())] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0
):
  """
  Get ledger entries for a specific account.
  
  Args:
    account: The account object (injected via dependency)
    start_date: Optional start date filter (inclusive)
    end_date: Optional end date filter (inclusive)
    limit: Maximum number of entries to return (default: 100)
    offset: Number of entries to skip for pagination (default: 0)
  
  Returns:
    List of ledger entries for the account
  """
  # Get all entries for this account with journal join
  query = select(model.Entries).join(model.Journal, model.Entries.journal_id == model.Journal.id).where(model.Entries.account_id == account.id)
  
  # Apply date filters if provided
  if start_date:
    query = query.where(model.Journal.date >= start_date)
  if end_date:
    query = query.where(model.Journal.date <= end_date)
  
  # Apply pagination and ordering by journal date (newest first)
  entries = db.execute(query.order_by(model.Journal.date.desc()).offset(offset).limit(limit)).scalars().all()
  
  return entries

@account.put('/{account_id}', response_model=schemas.AccountSchema)
async def update_account(account_id: int, account_data: schemas.AccountCreate, db: db):
  account = db.get(model.Account, account_id)
  if not account:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
  
  # Update account fields
  for field, value in account_data.model_dump(exclude_unset=True).items():
    setattr(account, field, value)
  
  db.commit()
  db.refresh(account)
  return account

@account.delete('/{account_id}')
async def delete_account(account_id: int, db: db):
  account = db.get(model.Account, account_id)
  if not account:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
  
  db.delete(account)
  db.commit()
  return {"message": "Account deleted successfully"}

@account.get('/summary')
async def get_account_summary(account: Annotated[model.Account, Depends(get_account_by_id)],
    db: db,
    end_date: Annotated[datetime, Field(le=datetime.now())] = datetime.now()
):
  
  """
  Get account summary including balance and entry statistics.
  
  Args:
    account: The account object (injected via dependency)
    end_date: Date to calculate balance up to (default: today)
  
  Returns:
    Account summary with statistics including total entries, debits, credits, and balance
  """
  # Get entry statistics with date filtering
  total_debit = db.execute(select(func.sum(case((model.Entries.side == schemas.EntrySide.DEBIT, model.Entries.amount), else_=0)).label('total_debits')
  ).select_from(model.Entries).join(model.Journal, model.Entries.journal_id == model.Journal.id).where(and_(
    model.Entries.account_id == account.id, 
    model.Journal.date <= end_date
  ))).scalar_one_or_none()

  total_credit = db.execute(select(
    func.sum(case((model.Entries.side == schemas.EntrySide.CREDIT, model.Entries.amount), else_=0)).label('total_credits')
  ).select_from(model.Entries).join(model.Journal, model.Entries.journal_id == model.Journal.id).where(    and_(
        model.Entries.account_id == account.id,
        model.Journal.date <= end_date
    ))).scalar_one_or_none()

  return {
    "credit": total_credit,
    "debit": total_debit,
    "balance": float(total_debit or 0) - float(total_credit or 0) if account.account_type in [schemas.AccountType.ASSET, schemas.AccountType.EXPENSE] else float(total_credit or 0) - float(total_debit or 0),
  }