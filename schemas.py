from pydantic import BaseModel, model_validator, field_validator, Field as field, validator
from typing import Optional, List, Annotated
from datetime import datetime, date
from decimal import Decimal
from . import model
import enum
from . import model


inflow_types = [
    model.TransactionType.DEPOSIT,
    model.TransactionType.SELL,
    model.TransactionType.INTEREST,
    model.TransactionType.LIQUIDATION,
]
outflow_types = [
    model.TransactionType.WITHDRAWAL,
    model.TransactionType.BUY,
    model.TransactionType.FEE,
    model.TransactionType.TAX,
]

# Add this validator function at the top of the file
def validate_date_not_past(v):
    if v is not None and v < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
        raise ValueError("Date cannot be in the past")
    return v

class IssuerBase(BaseModel):
    name: str

class IssuerCreate(IssuerBase):
    pass

class IssuerSchema(IssuerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VariableBase(BaseModel):
    symbol: str
    type: model.VariableType

class DepositBase(BaseModel):
    min_tenor: int
    max_tenor: int
    interest_pay: str
    penalty: Optional[Decimal] = None
    tax: Optional[bool] = None
    fixed: bool = None

class VariableCreate(VariableBase):
    pass

class DepositCreate(DepositBase):
    pass

class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    risk_level: int
    horizon: int
    img: Optional[str] = None
    currency: model.Currency
    is_active: bool = True

class ProductCreate(ProductBase):
    variable_data: Optional[VariableBase] = None
    deposit_data: Optional[DepositBase] = None

class ProductSchema(ProductBase):
    id: int
    issuer_id: int
    
    class Config:
        from_attributes = True

class VariableValueBase(BaseModel):
    value: Decimal
    date: Annotated[datetime, field(le=datetime.now())]

class VariableValueCreate(VariableValueBase):
    var_id: int

class VariableValueSchema(VariableValueBase):
    id: int
    var_id: int

    class Config:
        from_attributes = True

class DepositRateBase(BaseModel):
    rate: float
    date: Annotated[datetime, field(le=datetime.now())]
    
class DepositRateCreate(DepositRateBase):
    pass

class DepositRateSchema(DepositRateBase):
    id: int
    deposit_id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    first_name: str
    other_names: Optional[str] = None
    last_name: str
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int
    is_active: bool
    tier: Optional[int]
    created_at: datetime
    updated_at: datetime
    email: str
    # wallets: m
    # portfolios: model.Portfolio
    # riskProfile: model.RiskProfile
    # kyc: model.Kyc

    class Config:

        from_attributes = True

class RiskProfileBase(BaseModel):
    is_single: bool
    household_income: model.HouseholdIncome = model.HouseholdIncome.SINGLE
    primary_provider: bool = False
    monthly_income: Decimal
    primary_income_currency: model.Currency
    primary_income_source: model.IncomeSource
    annual_rent: Decimal
    dependents: int = 0
    children: int = 0
    wealth_value: Decimal
    secondary_income_source: Optional[model.IncomeSource] = None
    objective: model.WealthObjectiveBase

class RiskProfileUpdate(RiskProfileBase):
    pass

class RiskProfileCreate(RiskProfileBase):
    pass

class RiskProfileSchema(RiskProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PortfolioBase(BaseModel):
    type: model.PortfolioType
    active: bool = True
    closed: bool = False
    risk: Optional[int] = None
    duration: Optional[int] = None
    description: Optional[str] = None


class PortfolioSchema(PortfolioBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TargetBase(BaseModel):
    amount: Decimal
    date: Annotated[Optional[datetime], field(gt=date.today())]
    currency: model.Currency

class TargetCreate(TargetBase):
    pass

class TargetSchema(TargetBase):
    id: int
    portfolio_id: int
    commitment_id: Optional[int] = None
    achieved: bool

    class Config:
        from_attributes = True

class PortfolioCreate(BaseModel):
    description: Optional[str] = None
    risk: Optional[int] = field(le=4)
    target: Optional[TargetCreate] = None

class CommitmentBase(BaseModel):
    amount: Decimal = Decimal(0)
    frequency: Optional[str] = None
    start_date: Optional[Annotated[datetime, field(le=date.today())]] = None
    duration: int = 0
    active: bool = False
    
    @validator('start_date')
    def validate_start_date(cls, v):
        return validate_date_not_past(v)

class CommitmentCreate(CommitmentBase):
    pass

class CommitmentSchema(CommitmentBase):
    id: int
    portfolio_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TargetCommitCreate(BaseModel):
    target: Optional[TargetCreate] = None
    commitment: Optional[CommitmentCreate] = None

class PortfolioAttributesCreate(BaseModel):
    target: Optional[TargetCreate] = None
    plan: Optional[CommitmentCreate] = None
    targetAllocation: Optional[float] = None

class PortfolioAttributesUpdate(PortfolioAttributesCreate):
    type: Optional[model.PortfolioType] = None
    description: Optional[str] = None
    risk: Optional[int] = None

class AccountBase(BaseModel):
    account_type: model.AccountType
    code: int
    name: str
    currency: model.Currency
    description: Optional[str] = None
    as_of: Optional[Annotated[datetime, field(le=date.today())]] = None
    is_header: bool = False
    parent_id: Optional[int] = None
    
    @validator('as_of')
    def validate_as_of(cls, v):
        return validate_date_not_past(v)

class AccountCreate(AccountBase):
    pass

class AccountSchema(AccountBase):
    id: int
    name: str

    class Config:
        from_attributes = True

class WalletTransactionBase(BaseModel):
    amount: Decimal
    type: model.TransactionType

class WalletTransactionCreate(WalletTransactionBase):
    pass

class JournalEntries(BaseModel):
    amount: float
    account_id: int
    description: Optional[str] = None

class WalletTransactionSchema(WalletTransactionBase):
    id: int
    journal: JournalEntries
    transaction_date: datetime

    class Config:
        from_attributes = True

class WalleTransactionOut(WalletTransactionSchema):
    amount: int
    transaction_type: model.TransactionType
    status: model.TrasnsactionStatus
    transaction_date: datetime
    side: model.EntrySide

class AccountSchema(BaseModel):
    id: int
    account_type: model.AccountType




    class Config:
        from_attributes = True

class VariableIn(BaseModel):
  product_id: int
  amount: Decimal

class DepositIn(BaseModel):
   product_id: int
   amount: Decimal
   tenor: int

class DepositSale(BaseModel):
    deposit_id: int
    amount: int

class TransactionIn(BaseModel):
  variables: List[VariableIn]
  deposits: List[DepositIn]

class EntrySchema(BaseModel):
    id: int
    account_id: int
    journal_id: int
    amount: Decimal
    side: model.EntrySide
    description: Optional[str] = None

    class Config:
        from_attributes = True

class EntryOut(EntrySchema):
    account: AccountSchema

class JournalSchema(BaseModel):
    id: int
    account_id: int
    journal_id: int
    amount: Decimal
    side: model.EntrySide
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AccountBalanceSchema(BaseModel):
    account_id: int
    balance: Decimal
    currency: model.Currency
    as_of: datetime

    class Config:
        from_attributes = True

class AccountStatisticsSchema(BaseModel):
    total_entries: int
    total_amount: float
    total_debits: float
    total_credits: float
    balance: float

class AccountSummarySchema(BaseModel):
    account: AccountSchema
    statistics: AccountStatisticsSchema

    class Config:
        from_attributes = True

class BenchmarkCreate(BaseModel):

    symbol: str
    name: str
    description: Optional[str] = None
    currency: str
    source: model.DataSource

class BenchmarkMeta(BaseModel):
    date: datetime
    value: float
    marketCap: Optional[float] = None
    oneMonthReturn: Optional[float] = None
    threeMonthReturn: Optional[float] = None
    sixMonthReturn: Optional[float] = None
    oneYearReturn: Optional[float] = None
    threeYearReturn: Optional[float] = None
    fiveYearReturn: Optional[float] = None
    tenYearReturn: Optional[float] = None
    stdDev: Optional[float] = None

class SavingsRecommendationCreate(BaseModel):
    tenor: Optional[int] = None
    currency: model.Currency = model.Currency.NGN
    amount: Optional[float] = None

class IncomeAdvisoryCreate(BaseModel):
    frequency: model.Frequency
    currency: model.Currency = model.Currency.NGN
    income: Optional[float] = None
    investment: Optional[float] = None
    duration: Optional[int] = None
    liquidation: bool = False

class growthParams(BaseModel):
    targetAmount: Annotated[Optional[float], field(gt=0)] = None
    investment: Annotated[Optional[float], field(gt=0)] = None
    targetDate: Annotated[Optional[datetime], field(gt=date.today())] = None
    currency: model.Currency = model.Currency.NGN
    duration: Optional[int] = None
    target: bool

    @model_validator(mode='after')
    def validate_target_amount(self):
        if self.targetAmount is not None and self.investment is not None and self.investment > self.targetAmount:
            raise ValueError("Investment must be less than target amount")
        return self

    @field_validator('target')
    def validate_target(cls, v, info):
        data = info.data
        targetAmount = data.get('targetAmount')
        duration = data.get('duration')
        targetDate = data.get('targetDate')
        if v:
            if targetAmount is None:
                raise ValueError("If target is true, targetAmount must not be None.")
            if duration is None and targetDate is None:
                raise ValueError("If target is true, either duration or targetDate must not be None.")
        return v

    @model_validator(mode='after')
    def validate_duration_if_target_false(self):
        if self.target is False and self.duration is None:
            raise ValueError('If target is False, duration must not be None')
        return self

class GrowthRecommendationCreate(BaseModel):
    amount: Optional[float] = None
    currency: model.Currency = model.Currency.NGN
    duration: int

class SignupCreate(BaseModel):
    first_name: str
    last_name: str
    other_name: Optional[str] = None
    telephone: Optional[str] = None
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "other_name": "Ann",
                "telephone": "+2348012345678",
                "email": "jane.doe@example.com"
            }
        }
    
class TokenResponse(BaseModel):
    token: str
    token_type: str
    expires_in: int


    class Config:
        json_schema_extra = {
            "example": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc3ODYyMDQsIm90cCI6IjEzNTkyIiwiZmlyc3RfbmFtZSI6IkpvaG4iLCJsYXN0X25hbWUiOiJBc3VxdW8iLCJvdGhlcl9uYW1lIjoiIiwidGVsZXBob25lIjpudWxsLCJlbWFpbCI6InBpZV90ZXN0XzFAeW9wbWFpbC5jb20ifQ.8CN0JipmThERMqgVarKEFGS2m0oDL49vpNPki7Q142c",
                "token_type": "bearer",
                "expires_in": 90
            }
        }

class AccessLimit(enum.Enum):
    PASSWORD = "createPassword"
    LOGIN = "login"
    CREATE_ACCOUNT = "createAccount"
    READ_USER = "readUser"
    CREATE_USER = "createUser"
    READ_ADMIN = "readAdmin"
    APPROVE_ADMIN = "approveAdmin"
    CREATE_ADMIN = "createAdmin"


class SigninTokenResponse(TokenResponse):
    limit: AccessLimit
    refresh: Optional[str] = None

class AdminUserCreate(BaseModel):
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    email: str
    group: model.AdminGroup
    role: model.AdminRole