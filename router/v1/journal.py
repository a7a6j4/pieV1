from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, func, case
from database import db
import model
import schemas
from ..v1 import auth


journal = APIRouter(
    prefix="/deposit",
    tags=["Deposit"]
)

@journal.get("/{journal_id}")
async def getJournal(
        journal_id: int,
        db: db
):  
  
  journal = db.get(model.UserDeposit, journal_id)
  if not journal:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Journal not found")
   
  return journal


async def prepareJournal(
  credit: list[schemas.JournalEntries],
  debit: list[schemas.JournalEntries]):

  journal = model.Journal()
  
  # Extract Pydantic model data and sum amounts
  credit_amount = sum(entry.amount for entry in credit)
  debit_amount = sum(entry.amount for entry in debit)

  if credit_amount != debit_amount:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credit and debit amounts do not match")
  
  credit_entries = [model.Entries(amount=entry.amount, side=schemas.EntrySide.CREDIT, account_id=entry.account_id) for entry in credit]
  debit_entries = [model.Entries(amount=entry.amount, side=schemas.EntrySide.DEBIT, account_id=entry.account_id) for entry in debit]

  journal.entries = credit_entries + debit_entries

  return journal

@journal.post("/")
async def postJournal(
  db: db,
  journal = Depends(prepareJournal)
):
  
  db.add(journal)
  db.commit()
  db.refresh(journal)
  return journal



