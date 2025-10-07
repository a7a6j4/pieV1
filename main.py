from fastapi import FastAPI, File, Request, Depends, Header, Cookie, HTTPException, UploadFile, status, Body    
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Annotated
from router.v1 import user, auth, account, transaction, portfolio, product, journal, wallet, deposit, advisory, admin
import os
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from database import create_db_and_tables, db
from sqlalchemy import select, func
from utils.minio import upload_file
import schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await create_db_and_tables()
    except Exception as e:
        logger.error(f"Error creating database and tables: {e}")
        raise
    yield

app = FastAPI(lifespan=lifespan)

async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": f"Internal Server Error: {str(exc.orig)}"},
    )

app.add_exception_handler(IntegrityError, integrity_error_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

v1 = "/api/v1"

app.include_router(prefix=v1, router=user.user)
app.include_router(prefix=v1, router=auth.auth)
app.include_router(prefix=v1,router=account.account)
app.include_router(prefix=v1,router=transaction.transaction)
app.include_router(prefix=v1,router=portfolio.portfolio)
app.include_router(prefix=v1,router=product.product)
app.include_router(prefix=v1,router=journal.journal)
app.include_router(prefix=v1,router=wallet.wallet)
app.include_router(prefix=v1,router=deposit.deposit)
app.include_router(prefix=v1,router=advisory.advisory)
app.include_router(prefix=v1,router=admin.admin)

templates = Jinja2Templates(directory="templates")  # 'templates' is your HTML folder

# @app.get("/products", response_class=HTMLResponse)
# async def read_root(request: Request, db: db):
#     products = await product.getProducts(db)

#     return templates.TemplateResponse("index.html", {"request": request, "products": products})

# @app.get("/product/{id}", response_class=HTMLResponse)
# async def readProductPage(id: int, request: Request, db: db):
#     prod = await product.getProduct(product_id=id, db=db)

#     return templates.TemplateResponse("product.html", {"request": request, "product": prod})

# @app.get("/user/{id}", response_class=HTMLResponse)
# async def readUserPage(id: int, request: Request, db: db):
#     # fetch ORM object with relationships available in template
#     user_obj = await user.get_user(user_id=id, db=db)
#     return templates.TemplateResponse("user.html", {"request": request, "user": user_obj})

