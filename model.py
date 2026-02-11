from typing import List, Optional, Annotated
from datetime import datetime
import uuid
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    text,
    Numeric
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, registry
from sqlalchemy.sql import func
from decimal import Decimal
import enum
import schemas

money = Annotated[Decimal, 20]
rate = Annotated[Decimal, 3]


class Base(DeclarativeBase):
    registry(
        type_annotation_map={
            money: Numeric(20, 2),
            rate: Numeric(3, 2),
        }

    )

class AdminUser(Base):
    __tablename__ = "adminuser"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    phone_number: Mapped[Optional[str]] = mapped_column(unique=True)
    password: Mapped[Optional[str]]
    role: Mapped[schemas.AdminRole]
    createdBy: Mapped[Optional[int]] = mapped_column(ForeignKey("adminuser.id"))
    group: Mapped[schemas.AdminGroup]
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[Optional[str]] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=False)
    first_name: Mapped[str]
    other_names: Mapped[Optional[str]]
    last_name: Mapped[str]
    phone_number: Mapped[str] = mapped_column(unique=True)
    bvn: Mapped[Optional[str]] = mapped_column(unique=True)
    dateOfBirth: Mapped[Optional[datetime]]
    tier: Mapped[Optional[int]] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    wallets: Mapped[List["Wallet"]] = relationship(back_populates="user", lazy='selectin')
    portfolios: Mapped[List["Portfolio"]] = relationship(back_populates="user", lazy='selectin')
    riskProfile: Mapped[Optional["RiskProfile"]] = relationship(back_populates="user", lazy='selectin')
    kyc: Mapped[Optional["Kyc"]] = relationship(back_populates="user", lazy='selectin')
    anchor_user: Mapped[Optional["AnchorUser"]] = relationship(back_populates="user", lazy='selectin')

class UserAddress(Base):
    __tablename__ = "useraddress"
    id: Mapped[int] = mapped_column(primary_key=True)
    kycId: Mapped[int] = mapped_column(ForeignKey("kyc.id"))
    houseNumber: Mapped[Optional[str]]
    addressLineOne: Mapped[str]
    addressLineTwo: Mapped[Optional[str]]
    city: Mapped[str]
    lga: Mapped[Optional[str]]
    state: Mapped[schemas.NigeriaState]
    country: Mapped[schemas.Country]
    postalCode: Mapped[Optional[str]]

    kyc: Mapped[Optional["Kyc"]] = relationship(back_populates="address")

class kycDocument(Base):
    __tablename__ = "kycdocument"
    id: Mapped[int] = mapped_column(primary_key=True)
    kycId: Mapped[int] = mapped_column(ForeignKey("kyc.id"))
    type: Mapped[schemas.UserDocumentType]
    valid: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    kyc: Mapped["Kyc"] = relationship()

    __table_args__ = (UniqueConstraint("kycId", "type"),)

class kycStatus(Base):
    __tablename__ = "kycstatus"

    id: Mapped[int] = mapped_column(primary_key=True)
    kycId: Mapped[int] = mapped_column(ForeignKey("kyc.id"))
    identity: Mapped[bool] = mapped_column(default=False)
    address: Mapped[bool] = mapped_column(default=False)


class Kyc(Base):
    __tablename__ = "kyc"
    id: Mapped[int] = mapped_column(primary_key=True)
    userId: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True)
    gender: Mapped[Optional[schemas.Gender]]
    maidenName: Mapped[Optional[str]]
    idType: Mapped[Optional[schemas.IDType]]
    idNumber: Mapped[Optional[str]]
    idExpirationDate: Mapped[Optional[datetime]]
    addressProofType: Mapped[Optional[schemas.AddressProofType]]
    taxId: Mapped[Optional[str]]
    submitted: Mapped[bool] = mapped_column(default=False)
    verified: Mapped[bool] = mapped_column(default=False)
    identityVerified: Mapped[Optional[bool]] = mapped_column(default=False)
    addressVerified: Mapped[Optional[bool]] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()
    address: Mapped["UserAddress"] = relationship(back_populates="kyc")
    status: Mapped["kycStatus"] = relationship(lazy='selectin')
    nextOfKin: Mapped[Optional["NextOfKin"]] = relationship(back_populates="kyc")

    __table_args__ = (UniqueConstraint("userId", "idType", "idNumber"),
    UniqueConstraint("userId", "taxId"), )

class NextOfKin(Base):
    __tablename__ = "nextofkin"
    id: Mapped[int] = mapped_column(primary_key=True)
    kycId: Mapped[int] = mapped_column(ForeignKey("kyc.id"))
    firstName: Mapped[str]
    lastName: Mapped[str]
    middleName: Mapped[Optional[str]]
    phoneNumber: Mapped[str]
    email: Mapped[str]
    relationship: Mapped[str]

    kyc: Mapped["Kyc"] = relationship(back_populates="nextOfKin")

class AnchorUser(Base):
    __tablename__ = "anchoruser"
    id: Mapped[int] = mapped_column(primary_key=True)
    userId: Mapped[int] = mapped_column(ForeignKey("user.id"))
    customerId: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="anchor_user")
    bankAccount: Mapped[Optional["AnchorAccount"]] = relationship(back_populates="anchorUser", lazy='selectin')

    __table_args__ = (UniqueConstraint("userId", "customerId"),)

class AnchorAccount(Base):
    __tablename__ = "anchoraccount"
    id: Mapped[int] = mapped_column(primary_key=True)
    anchorUserId: Mapped[int] = mapped_column(ForeignKey("anchoruser.id"))
    depositAccountId: Mapped[str] = mapped_column(unique=True)
    accountNumber: Mapped[str]
    bank: Mapped[str]
    name: Mapped[str]
    bankCode: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    anchorUser: Mapped["AnchorUser"] = relationship(back_populates="bankAccount", lazy='selectin')

    __table_args__ = (UniqueConstraint("anchorUserId", "accountNumber"), UniqueConstraint("anchorUserId", "depositAccountId"))

class RiskProfile(Base):
    __tablename__ = "riskprofile"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    monthly_income: Mapped[money]
    primary_income_currency: Mapped[schemas.Currency]
    primary_income_source: Mapped[schemas.IncomeSource]
    annual_rent: Mapped[money]
    is_single: Mapped[bool]
    dependents: Mapped[int] = mapped_column(default=0)
    children: Mapped[int] = mapped_column(default=0)
    wealth_value: Mapped[money]
    household_income: Mapped[schemas.HouseholdIncome] = mapped_column(default=schemas.HouseholdIncome.SINGLE)
    secondary_income_source: Mapped[Optional[schemas.IncomeSource]] = mapped_column(default=schemas.IncomeSource.NONE)
    primary_provider: Mapped[bool] = mapped_column(default=False)   
    objective: Mapped[schemas.WealthObjectiveBase]
    capacity: Mapped[schemas.RiskLevel] = mapped_column(default=schemas.RiskLevel.LOW)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="riskProfile")

class Issuer(Base):
    __tablename__ = "issuer"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    img: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[List["Product"]] = relationship(back_populates="issuer")

class ProductGroupFees(Base):
    __tablename__ = "productgroupfees"
    id: Mapped[int] = mapped_column(primary_key=True)
    productGroupId: Mapped[int] = mapped_column(ForeignKey("productgroup.id"))
    TransactionFeeId: Mapped[int] = mapped_column(ForeignKey("transactionfee.id"))

    __table_args__ = (UniqueConstraint("productGroupId", "TransactionFeeId"),)

    productGroup: Mapped["ProductGroup"] = relationship(back_populates="transactionFees")
    transactionFee: Mapped["TransactionFee"] = relationship(back_populates="productGroups", lazy='selectin')   

class ProductGroup(Base):
    __tablename__ = "productgroup"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[Optional[str]] 
    market: Mapped[schemas.Country]
    productClass: Mapped[schemas.ProductClass]
    assetAccountId: Mapped[int] = mapped_column(ForeignKey("account.id"))
    receivableAccountId: Mapped[int] = mapped_column(ForeignKey("account.id"))
    payableAccountId: Mapped[int] = mapped_column(ForeignKey("account.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[List["Product"]] = relationship(back_populates="productGroup")
    transactionFees: Mapped[List["ProductGroupFees"]] = relationship(back_populates="productGroup")
    stats: Mapped[Optional["ProductGroupStats"]] = relationship(back_populates="productGroup")

class ProductGroupStats(Base):
    __tablename__ = "productgroupstats"
    id: Mapped[int] = mapped_column(primary_key=True)
    productGroupId: Mapped[int] = mapped_column(ForeignKey("productgroup.id"))
    stdDev: Mapped[float]
    variance: Mapped[float]
    correlation: Mapped[float]
    beta: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    productGroup: Mapped["ProductGroup"] = relationship(back_populates="stats")

class TransactionFee(Base):
    __tablename__ = "transactionfee"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(unique=True)
    description: Mapped[Optional[str]]
    sale: Mapped[bool] = mapped_column(default=False)
    purchase: Mapped[bool] = mapped_column(default=False)
    vat: Mapped[bool] = mapped_column(default=True)
    fee: Mapped[float] # in money value (100 = 1 currency unit) if flat, in basis points (100 = 1%) if relative
    feeType: Mapped[schemas.FeeType]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    productGroups: Mapped[List["ProductGroupFees"]] = relationship(back_populates="transactionFee")

class Product(Base):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(primary_key=True)
    issuerId: Mapped[int] = mapped_column(ForeignKey("issuer.id"))
    title: Mapped[str] = mapped_column(index=True, unique=True)
    description: Mapped[Optional[str]]
    productGroupId: Mapped[int] = mapped_column(ForeignKey("productgroup.id"))
    productGroup: Mapped["ProductGroup"] = relationship(back_populates="products")
    riskLevel: Mapped[int]
    horizon: Mapped[int]
    img: Mapped[Optional[str]]
    currency: Mapped[schemas.Currency]
    category: Mapped[str]
    isActive: Mapped[bool] = mapped_column(default=False)
    created: Mapped[datetime] = mapped_column(server_default=func.now())
    lastModified: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    issuer: Mapped["Issuer"] = relationship(back_populates="products", lazy='selectin')

    __mapper_args__ = {
        "polymorphic_identity": "product",
        "polymorphic_on": "category",
    }

class Variable(Product):
    __tablename__ = "variable"
    id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True)
    symbol: Mapped[str] = mapped_column(unique=True)
    productClass: Mapped[schemas.VariableType] = mapped_column()
    
    attributes: Mapped["VariableAttributes"] = relationship(back_populates="variable")
    values: Mapped[List["VariableValue"]] = relationship(back_populates="variable")
    __mapper_args__ = {
        "polymorphic_identity": "variable",
    }

class VariableAttributes(Base):
    __tablename__ = "variableattributes"
    id: Mapped[int] = mapped_column(primary_key=True)
    variableId: Mapped[int] = mapped_column(ForeignKey("variable.id"))
    unitsOutstanding: Mapped[Optional[int]]

    variable: Mapped["Variable"] = relationship(back_populates="attributes")

class Deposit(Product):
    __tablename__ = "deposit"

    id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True)
    minTenor: Mapped[int]
    maxTenor: Mapped[int]
    interestPay: Mapped[schemas.InterestPay]
    fixed: Mapped[bool] = mapped_column(default=True)
    rate: Mapped[int] # in basis points
    penalty: Mapped[Optional[int]] = mapped_column(default=0) # in basis points
    withholdingTax: Mapped[int] = mapped_column(default=100) # in basis points

    __mapper_args__ = {
        "polymorphic_identity": "deposit",
    }

class VariableValue(Base):
    __tablename__ = "variablevalue"
    id: Mapped[int] = mapped_column(primary_key=True)
    variableId: Mapped[int] = mapped_column(ForeignKey("variable.id"))
    price: Mapped[int]
    yieldRate: Mapped[int]
    date: Mapped[datetime]

    variable: Mapped["Variable"] = relationship(back_populates="values")

    __table_args__ = (UniqueConstraint("variableId", "date"),)

class Portfolio(Base):
    __tablename__ = "portfolio"
    id: Mapped[int] = mapped_column(primary_key=True)
    userId: Mapped[int] = mapped_column(ForeignKey("user.id"))
    active: Mapped[bool] = mapped_column(default=True)
    type: Mapped[schemas.PortfolioType] = mapped_column(default=schemas.PortfolioType.LIQUID)
    risk: Mapped[int] = mapped_column(default=1)
    duration: Mapped[Optional[int]]
    created: Mapped[datetime] = mapped_column(server_default=func.now())
    updated: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    description: Mapped[Optional[str]]
    deleted: Mapped[bool] = mapped_column(default=False)
    user: Mapped["User"] = relationship(back_populates="portfolios")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="portfolios")
    transactions: Mapped[List["PortfolioTransaction"]] = relationship(back_populates="portfolio")
    target: Mapped[Optional["PortfolioTarget"]] = relationship(back_populates="portfolio")
    contributionPlan: Mapped[Optional["PortfolioContributionPlan"]] = relationship(back_populates="portfolio")
    allocation: Mapped[Optional["PortfolioAllocation"]] = relationship(back_populates="portfolio")
    stats: Mapped[Optional["PortfolioStats"]] = relationship(back_populates="portfolio")

class PortfolioTarget(Base):
    __tablename__ = "portfoliotarget"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolioId: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))
    amount: Mapped[int]
    currency: Mapped[schemas.Currency]
    targetDate: Mapped[Optional[datetime]]
    created: Mapped[datetime] = mapped_column(server_default=func.now())
    updated: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    portfolio: Mapped["Portfolio"] = relationship(back_populates="target")

class PortfolioContributionPlan(Base):
    __tablename__ = "portfoliocontributionplan"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolioId: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))
    amount: Mapped[int]
    currency: Mapped[schemas.Currency]
    frequency: Mapped[schemas.Frequency]
    startDate: Mapped[datetime]
    nextContributionDate: Mapped[datetime]
    portfolio: Mapped["Portfolio"] = relationship(back_populates="contributionPlan")

class PortfolioAllocation(Base):
    __tablename__ = "portfolioallocation"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolioId: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))
    targetAllocation: Mapped[float]
    productGroupId: Mapped[int] = mapped_column(ForeignKey("productgroup.id"))
    productGroup: Mapped["ProductGroup"] = relationship()

    portfolio: Mapped["Portfolio"] = relationship(back_populates="allocation")

class PortfolioStats(Base):
    __tablename__ = "portfoliostats"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolioId: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))
    portfolio: Mapped["Portfolio"] = relationship(back_populates="stats")
    ngnvalue: Mapped[float]
    usdvalue: Mapped[float]
    date: Mapped[datetime]

class PortfolioDeposit(Base):
    __tablename__ = "portfoliodeposit"
    id: Mapped[int] = mapped_column(primary_key=True)

    transactionId: Mapped[int] = mapped_column(ForeignKey("deposittransaction.id"))
    transaction: Mapped["DepositTransaction"] = relationship(lazy='selectin')
    effectiveDate: Mapped[datetime]
    maturityDate: Mapped[datetime]
    matured: Mapped[bool] = mapped_column(default=False)
    closed: Mapped[bool] = mapped_column(default=False)
    closedDate: Mapped[Optional[datetime]]
    isActive: Mapped[bool] = mapped_column(default=False)
    journalId: Mapped[int] = mapped_column(ForeignKey("journal.id"))
    journal: Mapped["Journal"] = relationship(lazy='selectin')

    __table_args__ = (UniqueConstraint("transactionId", "effectiveDate", "maturityDate"),)

class PortfolioLedger(Base):
    __tablename__ = "portfolioledger"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolioId: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))
    transactionId: Mapped[Optional[int]] = mapped_column(ForeignKey("portfoliotransaction.id"))
    transaction: Mapped[Optional["PortfolioTransaction"]] = relationship(lazy='selectin')
    side: Mapped[schemas.UserLedgerSide]
    amount: Mapped[int]
    date: Mapped[datetime]
    account: Mapped[schemas.PortfolioAccount]

    type: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": "portfolioledger",
        "polymorphic_on": "type",
    }

class DepositLedger(PortfolioLedger):
    __tablename__ = "depositledger"
    id: Mapped[int] = mapped_column(ForeignKey("portfolioledger.id"), primary_key=True)
    portfolioDepositId: Mapped[int] = mapped_column(ForeignKey("portfoliodeposit.id"))
    portfolioDeposit: Mapped["PortfolioDeposit"] = relationship(lazy='selectin')

    __mapper_args__ = {
        "polymorphic_identity": "depositledger",
    }

class VariableLedger(PortfolioLedger):
    __tablename__ = "variableledger"
    id: Mapped[int] = mapped_column(ForeignKey("portfolioledger.id"), primary_key=True)
    variableId: Mapped[int] = mapped_column(ForeignKey("variable.id"))
    variable: Mapped["Variable"] = relationship(lazy='selectin')
    price: Mapped[int]
    units: Mapped[int]

    __mapper_args__ = {
        "polymorphic_identity": "variableledger",
    }

# Association table for many-to-many relationship between PortfolioTransaction and WalletTransaction
class PortfolioWalletTransactionAssociation(Base):
    __tablename__ = 'portfolio_wallet_transaction_association'
    
    portfolioTransactionId: Mapped[int] = mapped_column(ForeignKey('portfoliotransaction.id'), primary_key=True)
    walletTransactionId: Mapped[int] = mapped_column(ForeignKey('wallettransaction.id'), primary_key=True)
    createdAt: Mapped[datetime] = mapped_column(server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    
    # Relationships
    portfolio_transaction: Mapped["PortfolioTransaction"] = relationship(back_populates="wallet_transaction_associations")
    wallet_transaction: Mapped["WalletTransaction"] = relationship(back_populates="portfolio_transaction_associations")

class TransactionBatch(Base):
    __tablename__ = "transactionbatch"
    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4(), primary_key=True)
    createdAt: Mapped[datetime] = mapped_column(server_default=func.now())
    executed: Mapped[Optional[bool]] = mapped_column(default=False)
    executedAt: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    portfolio_transactions: Mapped[List["PortfolioTransaction"]] = relationship(back_populates="batch", lazy='selectin')

class PortfolioTransaction(Base):
    __tablename__ = "portfoliotransaction"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolioId: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))
    type: Mapped[schemas.TransactionType]
    amount: Mapped[int]
    date: Mapped[datetime] = mapped_column(server_default=func.now())
    status: Mapped[schemas.TransactionStatus]
    productId: Mapped[int] = mapped_column(ForeignKey("product.id"))
    product: Mapped["Product"] = relationship(lazy='selectin')
    portfolio: Mapped["Portfolio"] = relationship(back_populates="transactions")
    batchId: Mapped[uuid.UUID] = mapped_column(ForeignKey("transactionbatch.id"))
    batch: Mapped["TransactionBatch"] = relationship(back_populates="portfolio_transactions")
    category: Mapped[str]
    settlement: Mapped[schemas.TransactionStatus]
    
    # Many-to-many relationship with WalletTransaction through association table
    wallet_transaction_associations: Mapped[List["PortfolioWalletTransactionAssociation"]] = relationship(
        back_populates="portfolio_transaction"
    )
    
    # Convenience property to access wallet transactions directly
    @property
    def wallet_transactions(self) -> List["WalletTransaction"]:
        return [assoc.wallet_transaction for assoc in self.wallet_transaction_associations]

    __mapper_args__ = {
        "polymorphic_identity": "portfoliotransaction",
        "polymorphic_on": "category",
    }

class DepositTransaction(PortfolioTransaction):
    __tablename__ = "deposittransaction"
    id: Mapped[int] = mapped_column(ForeignKey("portfoliotransaction.id"), primary_key=True)
    rate: Mapped[Optional[int]] # in basis points (100 = 1%)
    tenor: Mapped[Optional[int]]

    __mapper_args__ = {
        "polymorphic_identity": "deposittransaction",
    }

class VariableTransaction(PortfolioTransaction):
    __tablename__ = "variabletransaction"
    id: Mapped[int] = mapped_column(ForeignKey("portfoliotransaction.id"), primary_key=True)
    units: Mapped[int] # in units
    price: Mapped[int] # in basis points (100 = 1%)

    __mapper_args__ = {
        "polymorphic_identity": "variabletransaction",
    }

class WalletGroup(Base):
    __tablename__ = "walletgroup"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    currency: Mapped[schemas.Currency]
    receivableAccountId: Mapped[int] = mapped_column(ForeignKey("account.id"))
    holdingAccountId: Mapped[int] = mapped_column(ForeignKey('account.id'))
    wallets: Mapped[List["Wallet"]] = relationship(back_populates="walletGroup")

class Wallet(Base):
    __tablename__ = "wallet"

    id: Mapped[int] = mapped_column(primary_key=True)
    userId: Mapped[int] = mapped_column(ForeignKey("user.id"))
    active: Mapped[bool] = mapped_column(default=True)
    walletGroupId: Mapped[int] = mapped_column(ForeignKey("walletgroup.id"))
    walletGroup: Mapped["WalletGroup"] = relationship(lazy='selectin')

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="wallets")
    transactions: Mapped[List["WalletTransaction"]] = relationship(back_populates="wallet")

class WalletTransaction(Base):
    __tablename__ = "wallettransaction"
    id: Mapped[int] = mapped_column(primary_key=True)
    walletId: Mapped[int] = mapped_column(ForeignKey("wallet.id"))
    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")
    settled: Mapped[bool] = mapped_column(default=False)
    settledAt: Mapped[Optional[datetime]]
    type: Mapped[schemas.TransactionType]
    amount: Mapped[int]
    date: Mapped[datetime] = mapped_column(server_default=func.now())
    status: Mapped[schemas.TransactionStatus]
    journalId: Mapped[int] = mapped_column(ForeignKey("journal.id"))
    journal: Mapped["Journal"] = relationship(lazy='selectin')
    
    # Many-to-many relationship with PortfolioTransaction through association table
    portfolio_transaction_associations: Mapped[List["PortfolioWalletTransactionAssociation"]] = relationship(
        back_populates="wallet_transaction"
    )
    
    # Convenience property to access portfolio transactions directly
    @property
    def portfolio_transactions(self) -> List["PortfolioTransaction"]:
        return [assoc.portfolio_transaction for assoc in self.portfolio_transaction_associations]

# financial accounting model

class Account(Base):
    __tablename__ = "account"
    __table_args__ = (UniqueConstraint("code", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[int] = mapped_column(unique=True, index=True)  # e.g., "1000", "2000-01"
    name: Mapped[str] = mapped_column(unique=True)
    level: Mapped[int] = mapped_column(default=1)
    description: Mapped[Optional[str]]
    is_header: Mapped[bool] = mapped_column(default=False)  # True for header, False for detail
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("account.id"), nullable=True)
    currency: Mapped[schemas.Currency]  # If you use multi-currency
    account_type: Mapped[schemas.AccountType]  # e.g., "asset", "liability", "income", "expense", etc.
    as_of: Mapped[datetime] = mapped_column(server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

        # Relationships
    parent: Mapped[Optional["Account"]] = relationship("Account", remote_side=[id], back_populates="children")
    children: Mapped[List["Account"]] = relationship("Account", back_populates="parent", cascade="all, delete-orphan")
    entries: Mapped[List["JournalEntry"]] = relationship(back_populates="account")


class Journal(Base):
    __tablename__ = "journal"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(server_default=func.now())

    entries: Mapped[List["JournalEntry"]] = relationship(back_populates="journal")

class JournalEntry(Base):
    __tablename__ = "journalentry"
    id: Mapped[int] = mapped_column(primary_key=True)
    accountId: Mapped[int] = mapped_column(ForeignKey("account.id"))
    journalId: Mapped[int] = mapped_column(ForeignKey("journal.id"))
    amount: Mapped[int]
    side: Mapped[schemas.EntrySide]  # e.g., "credit", "debit"
    description: Mapped[Optional[str]]

    journal: Mapped[Optional["Journal"]] = relationship(back_populates="entries")
    account: Mapped[Optional["Account"]] = relationship(back_populates="entries", lazy='selectin')

