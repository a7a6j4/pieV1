from fastapi import APIRouter, Depends, status, HTTPException, Query, Security
from fastapi.security import SecurityScopes
from sqlalchemy.orm import Session, join
from sqlalchemy import select, func, case, and_, or_
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

transaction = APIRouter(prefix="/transaction", tags=["transaction"])

async def recordVariableTransaction(
    product: model.Product,
    amount: float,
    price: float,
    portfolio: model.Portfolio,
    side: str,
    units: Optional[float] = None
):  
    description = f"Investment in {product.title}"

    if side == "sell":

        debit_account = 12 # user portfolio
        credit_account = 18 if product.currency == model.Currency.USD.value else 19 # transaction payables
    
    if side == "buy":
        debit_account = 18 if product.currency == model.Currency.USD.value else 19 # transaction payables
        credit_account = 12 # u ser portfolio

    # investment entries
    debit_entry = model.JournalEntries(amount=amount, description=description, account_id=debit_account)
    credit_entry = model.JournalEntries(amount=amount, description=description, account_id=credit_account)

    journal = await prepareJournal(
        credit=[credit_entry],
        debit=[debit_entry]
    )

    port_transaction = model.PortfolioTransaction(product=product,
        currency=product.currency, status=model.TrasnsactionStatus.PENDING, type=model.TransactionType.INVESTMENT.name if side == "buy" else model.TransactionType.LIQUIDATION.name, amount=amount
    )
    port_transaction.journal = journal
    portfolio.transactions.append(port_transaction)

    holding = model.VariableHolding(units=amount/price, price=price) if product.product_class != model.ProductClass.MONEY_MARKET else model.VariableHolding(units=units, price=100)
    holding.transaction = port_transaction

    return holding

async def recordDepositTransaction(
    product: model.Product,
    amount: float,
    tenor: int,
    rate: float,
    start_date: datetime,
    side: str,
    portfolio: model.Portfolio,
):
    description = f"Investment in {product.title}"

    if side == "sell":

        debit_account = 12 # user portfolio
        credit_account = 18 if product.currency == model.Currency.USD.value else 19 # global portfolio
    
    if side == "buy":
        credit_account= 18 if product.currency == model.Currency.USD.value else 19 # global portfolio
        debit_account = 12 # user portfolio

        # investment entries
    debit_entry = model.JournalEntries(amount=amount, account_id=debit_account, description=description)
    credit_entry = model.JournalEntries(amount=amount, account_id=credit_account, description=description)

    journal = await prepareJournal(
        credit=[credit_entry],
        debit=[debit_entry]
    )

    port_transaction = model.PortfolioTransaction(product=product,
        currency=product.currency, status=model.TrasnsactionStatus.PENDING, type=model.TransactionType.INVESTMENT.name, amount=amount
    )
    port_transaction.journal = journal
    portfolio.transactions.append(port_transaction)

    matures_on = start_date + timedelta(days=tenor)

    user_deposit = model.UserDeposit(
        amount=amount, tenor=tenor, rate=rate, start_date=start_date, maturity_date=matures_on 
    )
    user_deposit.portfolio = portfolio
    user_deposit.transaction = port_transaction

    return {
        "user_deposit": user_deposit,
        "transaction": port_transaction,
    }


async def getProductValue(product_id: int, db: Session):
    product = db.get(model.Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    
    if product.category == "variable":
        value = db.execute(
            select(model.VariableValue)
            .where(model.VariableValue.var_id == product_id)
            .order_by(model.VariableValue.date.desc())
        ).first()
        
        if not value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No value found for product {product_id}"
            )
        
        return value.value
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not a variable type"
        )

async def getNetProductHolding(product: model.Product, portfolio: model.Portfolio, db: Session):
    product = db.execute(
        select(
            model.Product.title,
            model.Product.currency,
            func.sum(
                case(
                    (model.PortfolioTransaction.type.in_([
                        model.TransactionType.INVESTMENT,
                        model.TransactionType.INTEREST
                    ]), model.VariableHolding.units),
                    else_=0
                )
            ).label("in_units"),
            func.sum(
                case(
                    (model.PortfolioTransaction.type == model.TransactionType.LIQUIDATION, model.VariableHolding.units),
                    else_=0
                )
            ).label("out_units")
        )
        .join(model.PortfolioTransaction, model.VariableHolding.transaction_id == model.PortfolioTransaction.id)
        .join(model.Product, model.PortfolioTransaction.product_id == model.Product.id)
        .where(model.PortfolioTransaction.portfolio_id == portfolio.id, model.Product.id == product.id)
        .group_by(model.Product.title, model.Product.currency)
    ).first()
        
    if product:
        units = product.in_units if product.in_units else 0 - product.out_units if product.out_units else 0
        return units
    else:
        return 0
    

async def liquidateDeposit(
        deposit: model.UserDeposit,
        liquidation: dict,
        portfolio: model.Portfolio
):

    liquidation_credit = model.JournalEntries(amount=liquidation["net_value"], account_id=12, description=f"Deposit liquidation") # add liquidation to transaction payables
    liquidation_debit = model.JournalEntries(amount=liquidation["net_value"], account_id=12, description=f"Deposit liquidation") # remove principal from portfolio

    liquidation_journal = await prepareJournal(
        credit=[liquidation_credit],
        debit=[liquidation_debit]
    )

    transactions = []
    # post penalty
    if liquidation.get("penalty"):
        penalty_deduction = model.PortfolioTransaction(
            amount=liquidation["penalty"],
            type=model.TransactionType.FEE,
            status=model.TrasnsactionStatus.PENDING,
            currency=deposit.transaction.product.currency,
            journal=liquidation_journal,
            portfolio=portfolio,
            product=deposit.transaction.product
        )

        transactions.append(penalty_deduction)
        # post tax
    if liquidation.get("total_interest"):
        tax_deduction = model.PortfolioTransaction(
        amount=liquidation["tax"],
        type=model.TransactionType.TAX,
        status=model.TrasnsactionStatus.PENDING,
        journal=liquidation_journal,
        currency=deposit.transaction.product.currency,
        portfolio=portfolio,
        product=deposit.transaction.product
        )
        transactions.append(tax_deduction)

        # post interest accrued
        interest_posting = model.PortfolioTransaction(
        amount=liquidation["total_interest"],
        type=model.TransactionType.INTEREST,
        status=model.TrasnsactionStatus.PENDING,
        currency=deposit.transaction.product.currency,
        journal=liquidation_journal,
        portfolio=portfolio,
        product=deposit.transaction.product
        )
        transactions.append(interest_posting)

        #post liquidation
    liquidation_posting = model.PortfolioTransaction(
        amount=liquidation["principal"],
        type=model.TransactionType.LIQUIDATION,
        status=model.TrasnsactionStatus.PENDING,
        currency=deposit.transaction.product.currency,
        journal=liquidation_journal,
        portfolio=portfolio,
        product=deposit.transaction.product
    )
    transactions.append(liquidation_posting)

    deposit.closed = True
    deposit.closed_on = datetime.now()
    deposit.is_active = False

    

    trx = {
        "transactions": transactions,
        "deposit": deposit
    }

    return trx

async def getUserWallets(
        user_id: int,
        db: Session
):
    usd_wallet = db.execute(select(model.Wallet).where(model.Wallet.user_id == user_id, model.Wallet.currency == 'USD')).scalar_one_or_none()
    ngn_wallet = db.execute(select(model.Wallet).where(model.Wallet.user_id == user_id, model.Wallet.currency == 'NGN')).scalar_one_or_none()

    if not usd_wallet or not ngn_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallets not found for user",
        )
    
    return {
        "usd": usd_wallet,
        "ngn": ngn_wallet
    }

async def getLatestPrice(variable: int, db:db):  
    value  = db.execute(
        select(model.VariableValue)
        .where(model.VariableValue.var_id == variable)
        .order_by(model.VariableValue.date.desc())
    ).scalar()
    
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No value found for variable {variable}"
        )
    return value


async def getVariableSalesValue(variables: List[schemas.VariableIn], product_lookup: dict, db: db):
    async def transaction_generator():
        for variable in variables:
            latest_value = await getLatestPrice(variable=variable.product_id, db=db)
            price_per_share = latest_value.value
            units = variable.amount / price_per_share

            yield {
                "product": product_lookup[variable.product_id],
                "amount": variable.amount,
                "units": units,
                "price": price_per_share
            }
    
    # Convert generator to list
    transactions = [transaction async for transaction in transaction_generator()]
    
    return transactions

async def checkProductExists(
        db: db, 
        variables: Optional[List[schemas.VariableIn]] = None,
        deposits: Optional[List[schemas.DepositIn]] = None):
    # get all product ids
    all_product_ids = []

    all_product_ids.extend([variable.product_id for variable in variables]) if variables else None
    all_product_ids.extend([deposit.product_id for deposit in deposits]) if deposits else None

    # get products from DB
    products = db.execute(select(model.Product).where(model.Product.id.in_(all_product_ids))).scalars().all()

    found_product_ids = {product.id for product in products}
    missing_product_ids = set(all_product_ids) - found_product_ids
    if missing_product_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Products not found: {list(missing_product_ids)}",
        )
    product_lookup = [{f"{product.id}": product} for product in products]
    
    def add_product_id_obj(list_of_items, product_lookup):
        new_list = []
        for item in list_of_items:
            # Convert to dict if needed, or use __dict__.copy()
            new_item = item.__dict__.copy()
            new_item["product"] = product_lookup.get(item.product_id)
            new_list.append(new_item)
        return new_list

    new_variable = add_product_id_obj(variables, product_lookup)
    new_deposit = add_product_id_obj(deposits, product_lookup)
    new_products = new_variable + new_deposit
    usdProducts = [product for product in new_products if product.currency == model.Currency.USD]
    ngnProducts = [product for product in new_products if product.currency == model.Currency.NGN]
    totals = {"NGN": sum([product.amount for product in ngnProducts]), "USD": sum([product.amount for product in usdProducts])}

    return {"products": new_products, "totals": totals}

async def checkDepositValue(
        deposits: List[schemas.DepositSale],
        db: Session
):
    
    for deposit in deposits:
        product_obj = db.get(model.Product, deposit.product_id)
        if not product_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {deposit.product_id} not found",
            )
        

@transaction.post("/buy")
async def postTransaction(
    db: db,
    variables: Optional[List[schemas.VariableIn]] = None,
    deposits: Optional[List[schemas.DepositIn]] = None,
    portfolio = Security(getPortfolio, scopes=["createUser"])
):
    # Check products exisit
    products_data = await checkProductExists(variables=variables, deposits=deposits, db=db)

    total_ngn = products_data["totals"]["NGN"]
    total_usd = products_data["totals"]["USD"]

    total_amount = total_ngn + (total_usd * 1500.0)

    #get walllet ids
    wallets = await getUserWallets(user_id=portfolio.user_id, db=db)
    wallet_balance = await getWalletBalance(wallet=wallets["ngn"], db=db)

    # check balance sufficiency
    if wallet_balance.get("balance", 0) < total_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

    # Perform wallet transacation -- Paystack // Moniepoint // Anchor wallet debit
    variable_transactions_data = list(filter(lambda x: x["product"].category == "variable", products_data["products"]))
    deposit_transactions_data = list(filter(lambda x: x["product"].category == "deposit", products_data["products"]))
                            
    if variable_transactions_data is not None:
        for trx_data in variable_transactions_data:
            transaction_record = await recordVariableTransaction(
            **trx_data,
            portfolio=portfolio,
            side='buy',
        )
            db.add(transaction_record)

            wallet_transaction = await generateWalletTransaction(
            db=db,
            data=schemas.WalletTransactionCreate(
                amount=trx_data["amount"] if trx_data["product"].currency == model.Currency.NGN else trx_data["amount"] * 1500 ,
                type=model.TransactionType.BUY,
            ),
            wallet=wallets.get("ngn", None)
        )
            db.add(wallet_transaction)

    if deposit_transactions_data is not None:
        for trx_data in deposit_transactions_data:
            transaction_record = await recordDepositTransaction(
            **trx_data,
            portfolio=portfolio,
            side='buy',
        )
            db.add(transaction_record["user_deposit"])

            wallet_transaction = await generateWalletTransaction(
            db=db,
            data=schemas.WalletTransactionCreate(
                amount=trx_data["amount"] if trx_data["product"].currency == model.Currency.NGN else trx_data["amount"] * 1500,
                type=model.TransactionType.BUY,
            ),
            wallet=wallets.get("ngn", None)
        )
            db.add(wallet_transaction)

    # Remove amount from wallet
    db.commit()
    return {
        "message": "Transaction successful"
    }

@transaction.post("/sell")
async def postSellTransaction(
    db: db,
    deposits: Optional[List[schemas.DepositSale]] = None,
    variables: Optional[List[schemas.VariableIn]] = None,
    portfolio = Depends(getPortfolio),
):

    wallets = await getUserWallets(user_id=portfolio.user_id, db=db)

    # check variable is sufficient
    if variables:

            for variable in variables:
                product = db.get(model.Product, variable.product_id)
                if not product:
                    raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {variable.product_id} not found",
                )

            # get product available units
                holding_units = await getNetProductHolding(product=product, portfolio=portfolio, db=db)

            # get latest price
                latest_value = await getLatestPrice(variable=variable.product_id, db=db)

            # compare 
                if holding_units < (variable.amount / latest_value.value):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sell value is more than units held for product {variable.product_id}")

                transaction_record = await recordVariableTransaction(
                product=product,
                amount=variable.amount,
                units=(variable.amount / latest_value.value),
                price=latest_value.value,
                portfolio=portfolio,
                side='sell'
            )
                db.add(transaction_record)

                wallet_transaction = await generateWalletTransaction(
                    db=db,
                    data=schemas.WalletTransactionCreate(
                    amount=variable.amount if product.currency == model.Currency.NGN else variable.amount * 1500,
                    type=model.TransactionType.SELL,

                ), wallet=wallets.get("ngn", None)
            )
                db.add(wallet_transaction)


    if deposits:
        for deposit in deposits:
            deposit_obj = db.get(model.UserDeposit, deposit.deposit_id)
            if not deposit_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Deposit {deposit.deposit_id} not found",
                )

            liquidation_value = await getLiquidationValue(db=db, deposit=deposit_obj)

            if deposit.amount > liquidation_value["current"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sell value is more than liquidation value for deposit {deposit_obj.id}",
                )

            deposit_transaction = await liquidateDeposit(
                deposit=deposit_obj,
                liquidation=liquidation_value,
                portfolio=portfolio,
            )

            db.add(deposit_transaction["deposit"])

            for trx in deposit_transaction["transactions"]:
                db.add(trx)
                wallet_transaction = await generateWalletTransaction(
                    db=db,
                    data=schemas.WalletTransactionCreate(
                        amount=(
                            trx.amount
                            if deposit_transaction["deposit"].transaction.product.currency
                            == model.Currency.NGN
                            else trx.amount * 1500
                        ),
                        type=trx.type,
                    ),
                    wallet=wallets.get("ngn", None),
                )
                db.add(wallet_transaction)


    db.commit()
    return {
        "message": "Transaction successful"
    }