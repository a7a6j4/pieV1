import model
import schemas
from database import db
from fastapi import Query, HTTPException, status
from typing import Optional, List


# define a transaction class to process purchase and sale transactions
# the class object will intialised used pydantic models for purchase and sale transactions
# the class will group products by currency and categorize them into variable and deposit products
# the class will have methods to check if the products are valid, get the total transaction consideration which includes asset cost and transaction fees
# the class will check if the user has sufficient funds to cover purchase or check if the user has sufficient assets to cover sale
# the class will generate remove amount from wallet and mark transaction as pending for purchase and and remove assets from portfolio for sale and mark transaction as pending for sale


class Transaction:

    withHoldingTax = 0.0075

    def __init__(self, db: db, user: model.User, portfolio: model.Portfolio):
        self.db = db
        self.user = user
        self.portfolio = portfolio

    async def getProductObjects(self):
        pass

    async def getTransactionFees(self):
        pass

    async def calculateTransactionFees(self):
        pass

class PurchaseTransaction(Transaction):
    def __init__(self, db: db, user: model.User, portfolio: model.Portfolio, variables: Optional[list[schemas.VariableIn]] = None, deposits: Optional[list[schemas.DepositIn]] = None):
        super().__init__(db, user, portfolio)
        self.variables = variables
        self.deposits = deposits

    # async def getProductObjects(self):
    #     new_variables = [{"product": await getDbProduct(product_id=x.product_id, db=db), "amount": x.amount} for x in self.variables]
    #     new_deposits = [{"product": await getDbProduct(product_id=x.product_id, db=db), "amount": x.amount} for x in self.deposits]
    #     all_products = new_variables + new_deposits
    #     return all_products

    async def getTransactionFees(self):
        pass

    async def calculateTransactionFees(self):
        pass