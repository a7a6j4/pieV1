from typing import List, Optional, Annotated
from datetime import datetime
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
    group: Mapped[schemas.AdminGroup]
    role: Mapped[schemas.AdminRole]
    createdBy: Mapped[Optional[int]] = mapped_column(ForeignKey("adminuser.id"))
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
    phone_number: Mapped[Optional[str]] = mapped_column(unique=True)
    tier: Mapped[Optional[int]] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    wallets: Mapped[List["Wallet"]] = relationship(back_populates="user")
    portfolios: Mapped[List["Portfolio"]] = relationship(back_populates="user", lazy='selectin')
    riskProfile: Mapped[Optional["RiskProfile"]] = relationship(back_populates="user", lazy='selectin')
    kyc: Mapped[Optional["Kyc"]] = relationship(back_populates="user", lazy='selectin')
    anchor_user: Mapped[Optional["AnchorUser"]] = relationship(back_populates="user")
    user_address: Mapped[Optional["UserAddress"]] = relationship(back_populates="user")

class UserAddress(Base):
    __tablename__ = "useraddress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    house_number: Mapped[Optional[str]]
    address_line_1: Mapped[str]
    address_line_2: Mapped[Optional[str]]
    lga: Mapped[Optional[str]]
    state: Mapped[str]
    country: Mapped[str]
    postal_code: Mapped[Optional[str]]

    user: Mapped["User"] = relationship(back_populates="user_address")


class Kyc(Base):
    __tablename__ = "kyc"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    bvn: Mapped[str]
    idType: Mapped[schemas.IDType]
    idNumber: Mapped[str]
    idFrontImage: Mapped[Optional[str]]
    idBackImage: Mapped[Optional[str]]
    idExpirationDate: Mapped[datetime]
    selfieImage: Mapped[Optional[str]]
    addresslineOne: Mapped[str]
    addresslineTwo: Mapped[Optional[str]]
    city: Mapped[str]
    state: Mapped[schemas.NigeriaState]
    postalCode: Mapped[str]
    addressProofType: Mapped[schemas.AddressProofType]
    addressProofImage: Mapped[Optional[str]]
    taxId: Mapped[Optional[str]]
    is_complete: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="kyc")

class AnchorUser(Base):
    __tablename__ = "anchoruser"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    anchor_customer_id: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="anchor_user")

class RiskProfile(Base):
    __tablename__ = "riskprofile"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    gender: Mapped[str]
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

class UserBankAccount(Base):
    __tablename__ = "userbankaccount"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id"))
    nuban: Mapped[str]

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

class Bank(Base):
    __tablename__ = "bank"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    code: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

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

class Product(Base):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(primary_key=True)
    issuer_id: Mapped[int] = mapped_column(ForeignKey("issuer.id"))
    title: Mapped[str] = mapped_column(index=True, unique=True)
    description: Mapped[Optional[str]]
    risk_level: Mapped[int]
    horizon: Mapped[int]
    img: Mapped[Optional[str]]
    currency: Mapped[schemas.Currency]
    category: Mapped[str]
    product_class: Mapped[Optional[schemas.ProductClass]] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    issuer: Mapped["Issuer"] = relationship(back_populates="products", lazy='selectin')
    allocation: Mapped[List["ProductAllocation"]] = relationship(back_populates="product")

    __mapper_args__ = {
        "polymorphic_identity": "product",
        "polymorphic_on": "category",
    }

class ProductAllocation(Base):
    __tablename__ = "productallocation"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    asset_class: Mapped[schemas.AssetClass]
    allocation: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["Product"] = relationship()

class DataSource(enum.Enum):

    API="API"
    LOCAL="LOCAL"

class Benchmark(Base):

    __tablename__ = "benchmark"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[Optional[str]]
    source: Mapped[DataSource]
    currency: Mapped[schemas.Currency]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    history: Mapped[List["BenchmarkHistory"]] = relationship(back_populates="benchmark")

class BenchmarkHistory(Base):

    __tablename__ = "benchmarkhistory"
    __table_args__ = (UniqueConstraint("benchmark_id", "date"),)
    
    id: Mapped[int] = mapped_column(primary_key=True)
    benchmark_id: Mapped[int] = mapped_column(ForeignKey("benchmark.id"))
    value: Mapped[float]
    date: Mapped[datetime] = mapped_column()

    benchmark: Mapped["Benchmark"] = relationship(back_populates="history")

class Variable(Product):
    __tablename__ = "variable"
    id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True)
    symbol: Mapped[str] = mapped_column(unique=True)
    benchmark_id: Mapped[Optional[int]] = mapped_column(ForeignKey("benchmark.id"))
    values: Mapped[List["VariableValue"]] = relationship()

    benchmark: Mapped[Optional["Benchmark"]] = relationship(lazy='selectin')
    character: Mapped[Optional["VariableCharacter"]] = relationship(back_populates="variable", lazy='selectin')

    __mapper_args__ = {
        "polymorphic_identity": "variable",
    }

class ProductValue(Base):
    __tablename__ = "productvalue"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": "productvalue",
        "polymorphic_on": "type",
    }

class VariableValue(ProductValue):
    __tablename__ = "variablevalue"
    __mapper_args__ = {
        "polymorphic_identity": "variablevalue",
    }
    __table_args__ = (UniqueConstraint("var_id", "date"),)

    id: Mapped[int] = mapped_column(ForeignKey("productvalue.id"), primary_key=True)
    var_id: Mapped[int] = mapped_column(ForeignKey("variable.id"))
    date: Mapped[datetime] = mapped_column(server_default=func.now())
    value: Mapped[money]
    last_update: Mapped[datetime] = mapped_column(server_default=func.now())

    variable: Mapped[Optional["Variable"]] = relationship(back_populates="values")

class VariableCharacter(Base):
    __tablename__ = "variablecharacter"
    id: Mapped[int] = mapped_column(primary_key=True)
    variable_id: Mapped[int] = mapped_column(ForeignKey("variable.id"), unique=True)
    std_dev: Mapped[float]
    variance: Mapped[float]
    beta: Mapped[float]
    float: Mapped[Optional[float]]
    avgDailyTurnover: Mapped[Optional[float]]

    last_update: Mapped[datetime] = mapped_column(server_default=func.now())
    variable: Mapped[Optional["Variable"]] = relationship()

class Deposit(Product):
    __tablename__ = "deposit"

    id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True)
    min_tenor: Mapped[int]
    max_tenor: Mapped[int]
    interest_pay: Mapped[str]
    fixed: Mapped[bool] = mapped_column(default=True)
    penalty: Mapped[Optional[rate]]
    tax: Mapped[bool] = mapped_column(default=True)

    rates: Mapped[List["DepositRate"]] = relationship(back_populates="deposit")

    __mapper_args__ = {
        "polymorphic_identity": "deposit",
    }

class DepositRate(ProductValue):
    __tablename__ = "depositrate"
    __mapper_args__ = {
        "polymorphic_identity": "depositrate",
    }
    __table_args__ = (UniqueConstraint("deposit_id", "date"),)

    id: Mapped[int] = mapped_column(ForeignKey("productvalue.id"), primary_key=True)
    deposit_id: Mapped[int] = mapped_column(ForeignKey("deposit.id"))
    date: Mapped[datetime] = mapped_column(server_default=func.now())
    rate: Mapped[rate]

    deposit: Mapped["Deposit"] = relationship(back_populates="rates")

class VariableHolding(Base):
    __tablename__ = "variableholding"
    id: Mapped[int] = mapped_column(primary_key=True)
    units: Mapped[money]
    price: Mapped[money]
    transaction_id: Mapped[int] = mapped_column(ForeignKey("portfoliotransaction.id"))
    date: Mapped[datetime] = mapped_column(server_default=func.now())
    
    transaction: Mapped[Optional["PortfolioTransaction"]] = relationship(lazy='selectin')

class UserDeposit(Base):
    __tablename__ = "userdeposit"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("portfoliotransaction.id"))
    amount: Mapped[money]
    tenor: Mapped[int]
    rate: Mapped[rate]
    start_date: Mapped[datetime]
    maturity_date: Mapped[datetime]
    matured: Mapped[bool] = mapped_column(default=False)
    closed_on: Mapped[Optional[datetime]]
    closed: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    transaction: Mapped[Optional["PortfolioTransaction"]] = relationship()

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str]  # e.g., "deposit", "withdrawal"
    amount: Mapped[money]
    status: Mapped[schemas.TrasnsactionStatus]
    currency: Mapped[schemas.Currency]
    journal_id: Mapped[int] = mapped_column(ForeignKey("journal.id"))
    date: Mapped[datetime] = mapped_column(server_default=func.now())
    type: Mapped[schemas.TransactionType]  # e.g., "deposit", "withdrawal"
    
    journal: Mapped[Optional["Journal"]] = relationship()

    __mapper_args__ = {
        "polymorphic_identity": "transaction",
        "polymorphic_on": "category",
    }

class WalletTransaction(Transaction):
    __tablename__ = "wallettransaction"
    id: Mapped[int] = mapped_column(ForeignKey("transaction.id"), primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallet.id"))

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")

    __mapper_args__ = {
        "polymorphic_identity": "wallettransaction",
    }
        
class PortfolioTransaction(Transaction):
    __tablename__ = "portfoliotransaction"

    id: Mapped[int] = mapped_column(ForeignKey("transaction.id"), primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))

    portfolio: Mapped["Portfolio"] = relationship()
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    product: Mapped[Optional["Product"]] = relationship(lazy='selectin')

    __mapper_args__ = {
        "polymorphic_identity": "portfoliotransaction",
    }

class Wallet(Base):
    __tablename__ = "wallet"
    __table_args__ = (UniqueConstraint("currency", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="wallets")
    currency: Mapped[schemas.Currency]
    transactions: Mapped[List["WalletTransaction"]] = relationship(back_populates="wallet", lazy='selectin')


class Portfolio(Base):
    __tablename__ = "portfolio"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    active: Mapped[bool] = mapped_column(default=True)
    type: Mapped[schemas.PortfolioType] = mapped_column(default=schemas.PortfolioType.LIQUID)
    risk: Mapped[int] = mapped_column(default=1)
    duration: Mapped[Optional[int]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    description: Mapped[Optional[str]]
    deleted_at: Mapped[Optional[datetime]]

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="portfolios")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="portfolios")
    # target: Mapped[Optional["Target"]] = relationship(back_populates="portfolio")
    # contribution_plan: Mapped[Optional["ContributionPlan"]] = relationship(back_populates="portfolio")

class PortfolioValue(Base):
    __tablename__ = "portfoliovalue"
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"))
    usdValue: Mapped[Decimal]
    ngnValue: Mapped[Decimal]
    totalUsd: Mapped[Decimal]
    totalNgn: Mapped[Decimal]
    date: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (UniqueConstraint("portfolio_id", "date"),)

class Target(Base):
    __tablename__ = "target"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"), unique=True)
    amount: Mapped[Decimal]
    currency: Mapped[schemas.Currency]
    target_date: Mapped[Optional[datetime]]
    achieved: Mapped[bool] = mapped_column(default=False)
    achieved_date: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship()

    __table_args__ = (
        UniqueConstraint("portfolio_id", name="unique_target_portfolio"),
    )

class ContributionPlan(Base):
    __tablename__ = "contribution_plan"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(ForeignKey("portfolio.id"), nullable=True, unique=True)
    amount: Mapped[Decimal]
    currency: Mapped[schemas.Currency]
    frequency: Mapped[schemas.Frequency]
    start_date: Mapped[datetime]
    end_date: Mapped[Optional[datetime]]
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # Relationships
    portfolio: Mapped[Optional["Portfolio"]] = relationship()
    schedules: Mapped[List["ContributionSchedule"]] = relationship(back_populates="contribution_plan")

class ContributionSchedule(Base):
    __tablename__ = "contribution_schedule"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    contribution_plan_id: Mapped[int] = mapped_column(ForeignKey("contribution_plan.id"))
    due_date: Mapped[datetime]
    amount: Mapped[Decimal]
    status: Mapped[str] = mapped_column(default="pending")  # pending, completed, missed
    completed_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    contribution_plan: Mapped["ContributionPlan"] = relationship(back_populates="schedules")

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
    entries: Mapped[List["Entries"]] = relationship(back_populates="account")


class Journal(Base):
    __tablename__ = "journal"
    journal_date: Mapped[datetime] = mapped_column(server_default=func.now())
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(server_default=func.now())

    entries: Mapped[List["Entries"]] = relationship(back_populates="journal")

class Entries(Base):
    __tablename__ = "entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    journal_id: Mapped[int] = mapped_column(ForeignKey("journal.id"))
    amount: Mapped[money]
    side: Mapped[schemas.EntrySide]  # e.g., "credit", "debit"
    description: Mapped[Optional[str]]

    journal: Mapped[Optional["Journal"]] = relationship(back_populates="entries")
    account: Mapped[Optional["Account"]] = relationship(back_populates="entries", lazy='selectin')

class CashFlowStatus(Base):
    __tablename__ = "cashflowstatus"
    id: Mapped[int] = mapped_column(primary_key=True) 
    status: Mapped[schemas.TrasnsactionStatus]
    type: Mapped[schemas.CashFlowType]
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction.id"))
    transaction: Mapped[Optional[PortfolioTransaction]] = relationship(lazy='selectin')


    

