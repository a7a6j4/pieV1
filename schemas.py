from pydantic import BaseModel, model_validator, field_validator, Field as field
from typing import Optional, List, Annotated
from datetime import datetime, date
from decimal import Decimal
import enum
class NigeriaState(enum.Enum):

    KANO = "KANO"  
    LAGOS = "LAGOS"
    KADUNA = "KADUNA"
    KATSINA = "KATSINA"
    OYO = "OYO"
    RIVERS = "RIVERS"
    BAUCHI = "BAUCHI"
    JIGAWA = "JIGAWA"
    BENUE = "BENUE"
    ANAMBRA = "ANAMBRA"
    BORNO = "BORNO"
    DELTA = "DELTA"
    NIGER = "NIGER"
    IMO = "IMO"
    AKWA_IBOM = "AKWA_IBOM"
    OGUN = "OGUN"
    SOKOTO = "SOKOTO"   
    ONDO = "ONDO"
    OSUN = "OSUN"
    KOGI = "KOGI"
    ZAMFARA = "ZAMFARA"
    ENUGU = "ENUGU"
    KEBBI = "KEBBI"
    EDO = "EDO"
    PLATEAU = "PLATEAU"
    ADAMAWA = "ADAMAWA"
    CROSSRIVER = "CROSSRIVER"
    ABIA = "ABIA"
    EKITI = "EKITI"
    KWARA = "KWARA"
    GOMBE = "GOMBE"
    YOBE = "YOBE"
    TARABA = "TARABA"   
    EBONYI = "EBONYI"
    NASARAWA = "NASARAWA"
    BAYELSA = "BAYELSA"
    FCT = "FCT"


class AssetClass(enum.Enum):
    USEQUITY='US Equities'
    NGEQUITY='Nigeria Equities'    
    USBONDS='US Bonds'
    USTREASURY='US Treasury'
    NGBONDS='Nigeria Bonds'
    NGTREASURY='Nigeria Treasury Bills'
    USCPAPER='US Commercial Debt'
    NGCPAPER='Nigeria Commercial Paper'
    USCORP='US Corporate Bond'
    NGCORP='Nigeria Corporate Bond'
    GLOBALEQUITY='Global Equities'
    NGREAL='Nigeria Real Estate'
    USREAL='US Real Estate'
    NGPRIVATE='Nigeria Private Debt'
    USPRIVATE='US Private Debt'
    USDEPOSIT='USD Deposits'
    NGDEPOSIT='NGN Deposits'
    NGEURO='Nigeria Eurobonds'
    SSEUR0='Sub-Sahara Africa Eurobonds'
    FREUR0='Frontier Market Eurobonds'
    FIXEDINCOME='Fixed Income'
    MONEYMARKET='Money Market'
    OTHER='Other'

class ProductClass(enum.Enum):
    DEPOSIT = "Deposit"
    EQUITY = "Equity"
    ETF = "Etf"
    FUND = 'Fund'
    CRYPTO = "Crypto"
    MUTUAL_FUND = "Mutual Fund"

class RiskLevel(enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

class HouseholdIncome(enum.Enum):
    SINGLE = "single"
    DOUBLED = "double"

class IncomeSource(enum.Enum):
    SALARY = "salary"
    BUSINESS = "business"
    INVESTMENT = "investment"
    RENT = "rent"
    OTHER = "other"
    NONE = "none"

class Currency(enum.Enum):
    NGN = "NGN"
    USD = "USD"

class EntrySide(enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    INVESTMENT = "investment"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    LIQUIDATION = "liquidation"
    FEE = "fee"
    TAX = "tax"
    TRANSFER = "transfer"
    BUY = "buy"
    SELL = "sell"

class PortfolioType(enum.Enum):
    TARGET = "target"
    GROWTH = "growth"
    EMERGENCY = "emergency"
    LIQUID = "liquid"
    INCOME = "income"
    INVEST = "invest"

class Frequency(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"

class VariableType(enum.Enum):
    STOCK = "stock"
    BOND = "bond"
    MUTUAL_FUND = "mutual_fund"
    MONEY_MARKET = "money_market"
    ETF = "etf"
    COMMODITY = "commodity"
    REAL_ESTATE = "real_estate"
    CRYPTOCURRENCY = "cryptocurrency"
    OTHER = "other"

class InterestPay(enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALFYEARLY = "half-yearly"
    ANNUALLY = "annually"
    ATMATURITY = "at-maturity"

class TrasnsactionStatus(enum.Enum):
    PENDING = "pending"
    REVERSED = "reversed"
    COMPLETED = "completed"
    FAILED = "failed"

class AccountType(enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"
    INCOME = "income"

class WealthObjectiveBase(enum.Enum):
    INDEPENDENCE = "independence"
    RETIREMENT = "retirement"
    EDUCATION = "education"
    OTHER = "other"
    GROWTH = "growth"
    INCOME = "income"

class AdminGroup(enum.Enum):
    EXECUTIVE = "executive"
    OPERATIONS = "operations"
    SUPPORT = "support"
    SUPER = "superAdmin"
    ADMIN = "admin"

class AdminRole(enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    APPROVE = "approve"
    SUPER = "superAdmin"

class CashFlowType(enum.Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"


inflow_types = [
   TransactionType.DEPOSIT,
   TransactionType.SELL,
   TransactionType.INTEREST,
   TransactionType.LIQUIDATION,
]
outflow_types = [
   TransactionType.WITHDRAWAL,
   TransactionType.BUY,
   TransactionType.FEE,
   TransactionType.TAX,
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
    type: VariableType

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
    currency: Currency
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
    household_income: HouseholdIncome = HouseholdIncome.SINGLE
    primary_provider: bool = False
    monthly_income: Decimal
    primary_income_currency: Currency
    primary_income_source: IncomeSource
    annual_rent: Decimal
    dependents: int = 0
    children: int = 0
    wealth_value: Decimal
    secondary_income_source: Optional[IncomeSource] = None
    objective: WealthObjectiveBase

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
    type: PortfolioType
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
    currency: Currency

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
    
    @field_validator('start_date')
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
    type: Optional[PortfolioType] = None
    description: Optional[str] = None
    risk: Optional[int] = None

class AccountBase(BaseModel):
    account_type: AccountType
    code: int
    name: str
    currency: Currency
    description: Optional[str] = None
    as_of: Optional[Annotated[datetime, field(le=date.today())]] = None
    is_header: bool = False
    parent_id: Optional[int] = None
    
    @field_validator('as_of')
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
    type: TransactionType

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
    transaction_type: TransactionType
    status: TrasnsactionStatus
    transaction_date: datetime
    side: EntrySide

class AccountSchema(BaseModel):
    id: int
    account_type: AccountType




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
    side: EntrySide
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
    side: EntrySide
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AccountBalanceSchema(BaseModel):
    account_id: int
    balance: Decimal
    currency: Currency
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
    currency: Currency = Currency.NGN
    amount: Optional[float] = None

class IncomeAdvisoryCreate(BaseModel):
    frequency: Frequency
    currency: Currency = Currency.NGN
    income: Optional[float] = None
    investment: Optional[float] = None
    duration: Optional[int] = None
    liquidation: bool = False

class growthParams(BaseModel):
    targetAmount: Annotated[Optional[float], field(gt=0)] = None
    investment: Annotated[Optional[float], field(gt=0)] = None
    targetDate: Annotated[Optional[datetime], field(gt=date.today())] = None
    currency: Currency = Currency.NGN
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
    currency: Currency = Currency.NGN
    duration: int

class SignupCreate(BaseModel):
    first_name: str
    last_name: str
    other_name: Optional[str] = None
    telephone: str
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
    group: AdminGroup
    role: AdminRole

opr = {
    "signUp" : {
        "seconds": 300,
        "name": "Signup",
        "subject": "Your Signup OTP"
    },
    "createPassword" : {
        "seconds": 90,
        "name": "Create Password",
        "subject": "Create Password OTP"
    },
    "resetPassword" : {
        "seconds": 180,
        "name": "Reset Password",
        "subject": "Reset Password OTP"
    },
    "login" : {
        "seconds": 3600,
        "name": "Access Token",
        "subject": "Your Pie Access Token"
    }
}


class AnchorAccountCreate(BaseModel):
    first_name: str
    last_name: str
    maiden_name: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: NigeriaState
    postal_code: str
    email: str
    phone_number: str
    doing_business_as: Optional[str] = None
    is_sole_proprietor: bool = False

# payload = { "data": { "attributes": {
#             "fullName": {
#                 "firstName": "John",
#                 "lastName": "Asuquo",
#                 "maidenName": "John Asuquo"
#             },
#             "address": {
#                 "country": "NG",
#                 "state": "LAGOS",
#                 "addressLine_1": "52 Unity Road, By Co-Op Villas, Badore, Ajah",
#                 "city": "Lagos",
#                 "postalCode": "105101"
#             },
#             "email": "ani@cleva.ng",
#             "phoneNumber": "08082835454",
#             "doingBusinessAs": "Cleva Platforms Nigeria Ltd",
#             "isSoleProprietor": False
#         } } }
# headers = {
#     "accept": "application/json",
#     "content-type": "application/json",
#     "x-anchor-key": "hfVz5.1f836e3cf846c4fb0695e31cf2a4f2eff8869c878f950a65385658c5aca2e0834f064e545e355d852b734b0b6918e88dd0d2"
# }


class Address(BaseModel):
    addressLine_1: str
    addressLine_2: Optional[str] = None
    city: str
    postalCode: str
    state: NigeriaState

class Gender(enum.Enum):
    MALE = "Male"
    FEMALE = "Female"

class AnchorKycLevel2(BaseModel):
    dateOfBirth: datetime
    gender: Gender = field(description="Gender must be either Male or Female")
    bvn: str = field(max_length=11, min_length=11, description="BVN must be 11 digits")
    selfieImage: str

class IDType(enum.Enum):
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    VOTERS_CARD = "VOTERS_CARD"
    PASSPORT = "PASSPORT"
    NATIONAL_ID = "NATIONAL_ID"
    NIN_SLIP = "NIN_SLIP"

class AnchorKycLevel3(BaseModel):
    idType: IDType
    idNumber: str
    idExpirationDate: datetime

class OtpType(enum.Enum):
    SIGNUP = "signUp"
    CREATE_PASSWORD = "createPassword"
    RESET_PASSWORD = "resetPassword"

class AddressProofType(enum.Enum):
    BANK_STATEMENT = "BANK_STATEMENT"
    UTILITY_BILL = "UTILITY_BILL"
    ADDRESS_PROOF = "ADDRESS_PROOF"

class KycCreate(BaseModel):
    maidenName: Optional[str] = None
    address: Address
    dateOfBirth: datetime
    gender: Gender = field(description="Gender must be either Male or Female")
    bvn: str = field(max_length=11, min_length=11, description="BVN must be 11 digits")
    idType: IDType
    idNumber: str
    idExpirationDate: datetime
    addressProofType: AddressProofType
    phoneNumber: str

class AnchorKycCreate(KycCreate):
    firstName: str
    lastName: str
    middleName: Optional[str] = None
    email: str
    phoneNumber: str
    
class KycUpdate(BaseModel):
    maidenName: Optional[str] = None
    addressLine_1: Optional[str] = None
    addressLine_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[NigeriaState] = None
    postalCode: Optional[str] = None
    dateOfBirth: Optional[datetime] = None
    gender: Optional[str] = None
    bvn: Optional[str] = None
    selfieImage: Optional[str] = None
    idType: Optional[IDType] = None
    idNumber: Optional[str] = None
    idFrontImage: Optional[str] = None
    idBackImage: Optional[str] = None
    idExpirationDate: Optional[datetime] = None


class AnchorAccountCreate(BaseModel):
    firstName: str
    lastName: str
    maidenName: Optional[str] = None
    addressLine_1: str
    addressLine_2: Optional[str] = None
    city: str
    state: NigeriaState
    postalCode: str
    email: str
    phoneNumber: str
    dateOfBirth: datetime
    gender: str
    bvn: str
    selfieImage: str
    idType: IDType
    idNumber: str
    idFrontImage: str
    idBackImage: str
    idExpirationDate: datetime

class UserDocumentType(enum.Enum):
    PASSPORT = "PASSPORT"
    FRONT_ID = "FRONT_ID"
    BACK_ID = "BACK_ID"
    SELFIE = "SELFIE"
    PROOF_OF_ADDRESS = "PROOF_OF_ADDRESS"

class TargetCreate(BaseModel):
    amount: float
    date: Optional[datetime] = None

class CommitmentCreate(BaseModel):
    amount: float
    frequency: Optional[str] = None
    duration: Optional[int] = None

class TargetCommit(BaseModel):
  target: Optional[TargetCreate]
  commitment: Optional[CommitmentCreate]