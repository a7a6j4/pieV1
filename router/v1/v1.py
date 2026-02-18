from fastapi import APIRouter
from . import user, auth, account, transaction, portfolio, product, journal, wallet, deposit, advisory, admin, webhooks

v1 = APIRouter(prefix="/v1", tags=["v1"])

@v1.get("/")
async def api_root():
    return {"message": "API is running"}

v1.include_router(router=user.user)
v1.include_router(router=auth.auth)
v1.include_router(router=account.account)
v1.include_router(router=transaction.transaction)
v1.include_router(router=portfolio.portfolio)
v1.include_router(router=product.product)
v1.include_router(router=journal.journal)
v1.include_router(router=wallet.wallet)
v1.include_router(router=deposit.deposit)
v1.include_router(router=advisory.advisory)
v1.include_router(router=admin.admin)
v1.include_router(router=webhooks.webhooks)

@v1.get("/health")
async def health():
    return {"message": "OK"}