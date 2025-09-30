from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from ...database import db
from ...model import UserDeposit, Deposit, DepositRate, Journal, Entries, EntrySide
from typing import Annotated, Union, Optional, List
from datetime import datetime
from ... import schemas



journal = APIRouter(
    prefix="/deposit",
    tags=["Deposit"]
)

@journal.get("/{journal_id}")
async def getJournal(
        journal_id: int,
        db: db
):  
  
  journal = db.get(UserDeposit, journal_id)
  if not journal:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Journal not found")
   
  return journal


async def prepareJournal(
  credit: list[schemas.JournalEntries],
  debit: list[schemas.JournalEntries]):

  journal = Journal()
  
  # Extract Pydantic model data and sum amounts
  credit_amount = sum(entry.amount for entry in credit)
  debit_amount = sum(entry.amount for entry in debit)

  if credit_amount != debit_amount:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credit and debit amounts do not match")
  
  credit_entries = [Entries(amount=entry.amount, side=EntrySide.CREDIT, account_id=entry.account_id) for entry in credit]
  debit_entries = [Entries(amount=entry.amount, side=EntrySide.DEBIT, account_id=entry.account_id) for entry in debit]

  journal.entries = credit_entries + debit_entries

  return journal

@journal.post("/")
async def postJournal(
  journal = Depends(prepareJournal),
  db: Session = Depends(db)
):
  
  db.add(journal)
  db.commit()
  db.refresh(journal)
  return journal



