from ctypes import Union
from click import File
from fastapi import UploadFile
from pydantic import BaseModel, model_validator, field_validator, Field as field
from typing import Optional, List, Annotated
from datetime import datetime, date, timedelta
from decimal import Decimal
import enum

class Country(enum.Enum):
    """
    A list of ISO 3166-1 alpha-2 country codes.
    The value of each member is the same as its name.
    """
    # N-G and A-D
    NG = 'NG'  # Nigeria
    AF = 'AF'  # Afghanistan
    AX = 'AX'  # Åland Islands
    AL = 'AL'  # Albania
    DZ = 'DZ'  # Algeria
    AS = 'AS'  # American Samoa
    AD = 'AD'  # Andorra
    # A
    AO = 'AO'  # Angola
    AI = 'AI'  # Anguilla
    AQ = 'AQ'  # Antarctica
    AG = 'AG'  # Antigua and Barbuda
    AR = 'AR'  # Argentina
    AM = 'AM'  # Armenia
    AW = 'AW'  # Aruba
    AU = 'AU'  # Australia
    AT = 'AT'  # Austria
    AZ = 'AZ'  # Azerbaijan
    # B
    BH = 'BH'  # Bahrain
    BS = 'BS'  # Bahamas
    BD = 'BD'  # Bangladesh
    BB = 'BB'  # Barbados
    BY = 'BY'  # Belarus
    BE = 'BE'  # Belgium
    BZ = 'BZ'  # Belize
    BJ = 'BJ'  # Benin
    BM = 'BM'  # Bermuda
    BT = 'BT'  # Bhutan
    BO = 'BO'  # Bolivia (Plurinational State of)
    BQ = 'BQ'  # Bonaire, Sint Eustatius and Saba
    BA = 'BA'  # Bosnia and Herzegovina
    BW = 'BW'  # Botswana
    BV = 'BV'  # Bouvet Island
    BR = 'BR'  # Brazil
    IO = 'IO'  # British Indian Ocean Territory
    BN = 'BN'  # Brunei Darussalam
    BG = 'BG'  # Bulgaria
    BF = 'BF'  # Burkina Faso
    BI = 'BI'  # Burundi
    # C
    KH = 'KH'  # Cambodia
    CM = 'CM'  # Cameroon
    CA = 'CA'  # Canada
    CV = 'CV'  # Cabo Verde
    KY = 'KY'  # Cayman Islands
    CF = 'CF'  # Central African Republic
    TD = 'TD'  # Chad
    CL = 'CL'  # Chile
    CN = 'CN'  # China
    CX = 'CX'  # Christmas Island
    CC = 'CC'  # Cocos (Keeling) Islands
    CO = 'CO'  # Colombia
    KM = 'KM'  # Comoros
    CG = 'CG'  # Congo
    CD = 'CD'  # Congo (Democratic Republic of the)
    CK = 'CK'  # Cook Islands
    CR = 'CR'  # Costa Rica
    CI = 'CI'  # Côte d'Ivoire
    HR = 'HR'  # Croatia
    CU = 'CU'  # Cuba
    CW = 'CW'  # Curaçao
    CY = 'CY'  # Cyprus
    CZ = 'CZ'  # Czechia
    # D-E
    DK = 'DK'  # Denmark
    DJ = 'DJ'  # Djibouti
    DM = 'DM'  # Dominica
    DO = 'DO'  # Dominican Republic
    EC = 'EC'  # Ecuador
    EG = 'EG'  # Egypt
    SV = 'SV'  # El Salvador
    GQ = 'GQ'  # Equatorial Guinea
    ER = 'ER'  # Eritrea
    EE = 'EE'  # Estonia
    ET = 'ET'  # Ethiopia
    # F
    FK = 'FK'  # Falkland Islands (Malvinas)
    FO = 'FO'  # Faroe Islands
    FJ = 'FJ'  # Fiji
    FI = 'FI'  # Finland
    FR = 'FR'  # France
    GF = 'GF'  # French Guiana
    PF = 'PF'  # French Polynesia
    TF = 'TF'  # French Southern Territories
    # G
    GA = 'GA'  # Gabon
    GM = 'GM'  # Gambia
    GE = 'GE'  # Georgia
    DE = 'DE'  # Germany
    GH = 'GH'  # Ghana
    GI = 'GI'  # Gibraltar
    GR = 'GR'  # Greece
    GL = 'GL'  # Greenland
    GD = 'GD'  # Grenada
    GP = 'GP'  # Guadeloupe
    GU = 'GU'  # Guam
    GT = 'GT'  # Guatemala
    GG = 'GG'  # Guernsey
    GN = 'GN'  # Guinea
    GW = 'GW'  # Guinea-Bissau
    GY = 'GY'  # Guyana
    # H-I
    HT = 'HT'  # Haiti
    HM = 'HM'  # Heard Island and McDonald Islands
    VA = 'VA'  # Holy See
    HN = 'HN'  # Honduras
    HK = 'HK'  # Hong Kong
    HU = 'HU'  # Hungary
    IS = 'IS'  # Iceland
    IN = 'IN'  # India
    ID = 'ID'  # Indonesia
    IR = 'IR'  # Iran (Islamic Republic of)
    IQ = 'IQ'  # Iraq
    IE = 'IE'  # Ireland
    IM = 'IM'  # Isle of Man
    IL = 'IL'  # Israel
    IT = 'IT'  # Italy
    # J-K
    JM = 'JM'  # Jamaica
    JP = 'JP'  # Japan
    JE = 'JE'  # Jersey
    JO = 'JO'  # Jordan
    KZ = 'KZ'  # Kazakhstan
    KE = 'KE'  # Kenya
    KI = 'KI'  # Kiribati
    KP = 'KP'  # Korea (Democratic People's Republic of)
    KR = 'KR'  # Korea (Republic of)
    KW = 'KW'  # Kuwait
    KG = 'KG'  # Kyrgyzstan
    # L
    LA = 'LA'  # Lao People's Democratic Republic
    LV = 'LV'  # Latvia
    LB = 'LB'  # Lebanon
    LS = 'LS'  # Lesotho
    LR = 'LR'  # Liberia
    LY = 'LY'  # Libya
    LI = 'LI'  # Liechtenstein
    LT = 'LT'  # Lithuania
    LU = 'LU'  # Luxembourg
    # M
    MO = 'MO'  # Macao
    MK = 'MK'  # North Macedonia
    MG = 'MG'  # Madagascar
    MW = 'MW'  # Malawi
    MY = 'MY'  # Malaysia
    MV = 'MV'  # Maldives
    ML = 'ML'  # Mali
    MT = 'MT'  # Malta
    MH = 'MH'  # Marshall Islands
    MQ = 'MQ'  # Martinique
    MR = 'MR'  # Mauritania
    MU = 'MU'  # Mauritius
    YT = 'YT'  # Mayotte
    MX = 'MX'  # Mexico
    FM = 'FM'  # Micronesia (Federated States of)
    MD = 'MD'  # Moldova (Republic of)
    MC = 'MC'  # Monaco
    MN = 'MN'  # Mongolia
    ME = 'ME'  # Montenegro
    MS = 'MS'  # Montserrat
    MA = 'MA'  # Morocco
    MZ = 'MZ'  # Mozambique
    MM = 'MM'  # Myanmar
    # N
    NA = 'NA'  # Namibia
    NR = 'NR'  # Nauru
    NP = 'NP'  # Nepal
    NL = 'NL'  # Netherlands
    NC = 'NC'  # New Caledonia
    NZ = 'NZ'  # New Zealand
    NI = 'NI'  # Nicaragua
    NE = 'NE'  # Niger
    NU = 'NU'  # Niue
    NF = 'NF'  # Norfolk Island
    MP = 'MP'  # Northern Mariana Islands
    NO = 'NO'  # Norway
    # O-P
    OM = 'OM'  # Oman
    PK = 'PK'  # Pakistan
    PW = 'PW'  # Palau
    PS = 'PS'  # Palestine, State of
    PA = 'PA'  # Panama
    PG = 'PG'  # Papua New Guinea
    PY = 'PY'  # Paraguay
    PE = 'PE'  # Peru
    PH = 'PH'  # Philippines
    PN = 'PN'  # Pitcairn
    PL = 'PL'  # Poland
    PT = 'PT'  # Portugal
    PR = 'PR'  # Puerto Rico
    # Q-R
    QA = 'QA'  # Qatar
    RE = 'RE'  # Réunion
    RO = 'RO'  # Romania
    RU = 'RU'  # Russian Federation
    RW = 'RW'  # Rwanda
    # S
    BL = 'BL'  # Saint Barthélemy
    SH = 'SH'  # Saint Helena, Ascension and Tristan da Cunha
    KN = 'KN'  # Saint Kitts and Nevis
    LC = 'LC'  # Saint Lucia
    MF = 'MF'  # Saint Martin (French part)
    PM = 'PM'  # Saint Pierre and Miquelon
    VC = 'VC'  # Saint Vincent and the Grenadines
    WS = 'WS'  # Samoa
    SM = 'SM'  # San Marino
    ST = 'ST'  # Sao Tome and Principe
    SA = 'SA'  # Saudi Arabia
    SN = 'SN'  # Senegal
    RS = 'RS'  # Serbia
    SC = 'SC'  # Seychelles
    SL = 'SL'  # Sierra Leone
    SG = 'SG'  # Singapore
    SX = 'SX'  # Sint Maarten (Dutch part)
    SK = 'SK'  # Slovakia
    SI = 'SI'  # Slovenia
    SB = 'SB'  # Solomon Islands
    SO = 'SO'  # Somalia
    ZA = 'ZA'  # South Africa
    GS = 'GS'  # South Georgia and the South Sandwich Islands
    SS = 'SS'  # South Sudan
    ES = 'ES'  # Spain
    LK = 'LK'  # Sri Lanka
    SD = 'SD'  # Sudan
    SR = 'SR'  # Suriname
    SJ = 'SJ'  # Svalbard and Jan Mayen
    SZ = 'SZ'  # Eswatini
    SE = 'SE'  # Sweden
    CH = 'CH'  # Switzerland
    SY = 'SY'  # Syrian Arab Republic
    # T
    TW = 'TW'  # Taiwan (Province of China)
    TJ = 'TJ'  # Tajikistan
    TZ = 'TZ'  # Tanzania, United Republic of
    TH = 'TH'  # Thailand
    TL = 'TL'  # Timor-Leste
    TG = 'TG'  # Togo
    TK = 'TK'  # Tokelau
    TO = 'TO'  # Tonga
    TT = 'TT'  # Trinidad and Tobago
    TN = 'TN'  # Tunisia
    TR = 'TR'  # Turkey
    TM = 'TM'  # Turkmenistan
    TC = 'TC'  # Turks and Caicos Islands
    TV = 'TV'  # Tuvalu
    # U-V
    UG = 'UG'  # Uganda
    UA = 'UA'  # Ukraine
    AE = 'AE'  # United Arab Emirates
    GB = 'GB'  # United Kingdom of Great Britain and Northern Ireland
    US = 'US'  # United States of America
    UM = 'UM'  # United States Minor Outlying Islands
    UY = 'UY'  # Uruguay
    UZ = 'UZ'  # Uzbekistan
    VU = 'VU'  # Vanuatu
    VE = 'VE'  # Venezuela (Bolivarian Republic of)
    VN = 'VN'  # Viet Nam
    VG = 'VG'  # Virgin Islands (British)
    VI = 'VI'  # Virgin Islands (U.S.)
    # W-Z
    WF = 'WF'  # Wallis and Futuna
    EH = 'EH'  # Western Sahara
    YE = 'YE'  # Yemen
    ZM = 'ZM'  # Zambia
    ZW = 'ZW'  # Zimbabwe
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
    BIMONTHLY = "bimonthly"
    SEMIANNUALLY = "semiannually"

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
    CUSTOM = "custom"

class TransactionStatus(enum.Enum):
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

class ProductCategory(enum.Enum):
    VARIABLE = "variable"
    DEPOSIT = "deposit"

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

class FeeType(enum.Enum):
    FLAT = "flat"
    RELATIVE = "relative"

class FeeClass(enum.Enum):
    COMMISSION = "commission"
    TAX = "tax"
    THIRDPARTY = "thirdparty"

class ProductGroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    market: Country

class ProductGroupCreate(ProductGroupBase):
    feeIds: Optional[List[int]] = None

class ProductGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    market: Optional[Country] = None
    feeIds: Optional[List[int]] = None

class ProductGroupSchema(ProductGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
class TransactionFeeBase(BaseModel):
    title: str
    description: Optional[str] = None
    sale: bool = False
    purchase: bool = False
    vat: bool = True
    feeType: FeeType = FeeType.FLAT
    fee: Optional[float] = None

class TransactionFeeCreate(TransactionFeeBase):
    pass

class TransactionFeeSchema(TransactionFeeBase):
    id: int
    created_at: datetime
    updated_at: datetime

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


class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    riskLevel: int
    horizon: int
    img: Optional[str] = None
    currency: Currency
    isActive: bool = True
    productGroupId: int

class VariableBase(ProductBase):
    symbol: str
    productClass: VariableType

class DepositBase(ProductBase):
    minTenor: int
    maxTenor: int
    interestPay: InterestPay
    penalty: Optional[int]
    withholdingTax: int
    fixed: bool = False
    rate: int

class VariableCreate(VariableBase):
    pass

class DepositCreate(DepositBase):
    pass

class ProductSchema(ProductBase):
    id: int
    issuerId: int
    
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

class TargetCreate(BaseModel):
    amount: float
    currency: Currency
    targetDate: Optional[datetime] = None

class IncomeCreate(BaseModel):
    amount: float
    currency: Currency
    frequency: Frequency

class PortfolioBase(BaseModel):
    active: bool = True
    closed: bool = False
    risk: Optional[int] = 1
    duration: Optional[int] = 1
    description: Optional[str] = None

class PortfolioSchema(PortfolioBase):
    id: int
    userId: int
    created: datetime
    updated: datetime

    income: Optional[IncomeCreate]
    target: Optional[TargetCreate]

    class Config:
        from_attributes = True

class UserOut(UserSchema):
    portfolios: List[PortfolioSchema]


class CommitmentCreate(BaseModel):
    amount: float
    currency: Currency
    frequency: Frequency
    startDate: Optional[datetime] = datetime.now()

class AllocationCreate(BaseModel):
  targetAllocation: float
  productGroupId: int

class PortfolioObjectiveCreate(BaseModel):
  target: Optional[TargetCreate] = None
  income: Optional[IncomeCreate] = None

class PortfolioCreate(PortfolioBase):
    target: Optional[TargetCreate] = None
    income: Optional[IncomeCreate] = None

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
    status: TransactionStatus
    transaction_date: datetime
    side: EntrySide

class AccountSchema(BaseModel):
    id: int
    account_type: AccountType
    class Config:
        from_attributes = True

class PurchaseOrder(BaseModel):
  productId: int
  amount: float
  tenor: Optional[int] = None

class SaleOrder(BaseModel):
    id: int
    amount: float
    type: ProductCategory
    
class VariableIn(BaseModel):
  product_id: int
  amount: float

class DepositIn(BaseModel):
   product_id: int
   amount: float
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
    firstName: str
    lastName: str
    otherNames: Optional[str] = None
    phoneNumber: str
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "firstName": "Jane",
                "lastName": "Doe",
                "otherNames": "Ann",
                "phoneNumber": "+2348012345678",
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

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc3ODYyMDQsIm90cCI6IjEzNTkyIiwiZmlyc3RfbmFtZSI6IkpvaG4iLCJsYXN0X25hbWUiOiJBc3VxdW8iLCJvdGhlcl9uYW1lIjoiIiwidGVsZXBob25lIjpudWxsLCJlbWFpbCI6InBpZV90ZXN0XzFAeW9wbWFpbC5jb20ifQ.8CN0JipmThERMqgVarKEFGS2m0oDL49vpNPki7Q142c",
                "token_type": "bearer",
                "expires_in": 90,
                "limit": "login"
            }
        }

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
        "seconds": 300,
        "name": "Create Password",
        "subject": "Create Password OTP"
    },
    "resetPassword" : {
        "seconds": 600,
        "name": "Reset Password",
        "subject": "Reset Password OTP"
    },
    "login" : {
        "seconds": 3600,
        "name": "Access Token",
        "subject": "Your Pie Access Token"
    }
}

class PortfolioAccount(enum.Enum):
    ASSET = "asset"
    INTEREST = "interest"
    TAX = "tax"
    DIVIDEND = "dividend"
    PROFIT_LOSS = "profit_loss"

class UserLedgerSide(enum.Enum):
    IN = "in"
    OUT = "out"

class UserLedgerType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    INVESTMENT = "investment"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    LIQUIDATION = "liquidation"
    FEE = "fee"
    TAX = "tax"


class Gender(enum.Enum):
    MALE = "Male"
    FEMALE = "Female"

class IDType(enum.Enum):
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    VOTERS_CARD = "VOTERS_CARD"
    PASSPORT = "PASSPORT"
    NATIONAL_ID = "NATIONAL_ID"
    NIN_SLIP = "NIN_SLIP"

class AnchorAccountCreate(BaseModel):
    firstName: str
    lastName: str
    middleName: Optional[str] = None
    maidenName: Optional[str] = None
    addressLineOne: str
    addressLineTwo: Optional[str] = None
    city: str
    state: NigeriaState
    postalCode: str
    email: str
    phoneNumber: str
    dateOfBirth: datetime
    gender: Gender
    bvn: str = field(max_length=11, min_length=11, description="BVN must be 11 digits")
    idType: IDType
    idNumber: str
    expiryDate: datetime

class Address(BaseModel):
    houseNumber: Optional[str] = None
    addressLineOne: str
    addressLineTwo: Optional[str] = None
    city: str
    state: NigeriaState
    country: Country = field(default=Country.NG)
    postalCode: Optional[str] = None

class AnchorKycLevel2(BaseModel):
    dateOfBirth: datetime
    gender: Gender = field(description="Gender must be either Male or Female")
    bvn: str = field(max_length=11, min_length=11, description="BVN must be 11 digits")
    selfieImage: str


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

class kycIdentityCreate(BaseModel):
    idType: IDType
    idNumber: str
    idExpirationDate: Optional[datetime] = None

class NextOfKinCreate(BaseModel):
    firstName: str
    lastName: str
    middleName: Optional[str] = None
    phoneNumber: str
    email: str
    relationship: str

class KycBvnCreate(BaseModel):
    bvn: str = field(max_length=11, min_length=11, description="BVN must be 11 digits")
    dateOfBirth: datetime = field(description="Date of birth must be in the format YYYY-MM-DD")

class KycCreate(BaseModel):
    maidenName: str
    nextOfKin: NextOfKinCreate
    gender: Gender = field(description="Gender must be either Male or Female")
    identity: kycIdentityCreate
    # addressProofType: Optional[AddressProofType] = None
    # taxId: Optional[str] = None

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


class UserDocumentType(enum.Enum):
    PASSPORT = "PASSPORT"
    FRONT_ID = "FRONT_ID"
    BACK_ID = "BACK_ID"
    SELFIE = "SELFIE"
    PROOF_OF_ADDRESS = "PROOF_OF_ADDRESS"

class AnchorMode(enum.Enum):
    SANDBOX = "sandbox"
    LIVE = "live"

class WalletGroupCreate(BaseModel):
  name: str
  description: Optional[str] = None
  currency: Currency
  receivableAccountId: int


class AnchorBalanceData(BaseModel):
  availableBalance: float
  ledgerBalance: float
  hold: float
  pending: float

  class Config:
    from_attributes = True

class AnchorBalanceResponse(BaseModel):
  data: AnchorBalanceData

  class Config:
    from_attributes = True

nextdate_map = {
  Frequency.MONTHLY: timedelta(days=30),
  Frequency.BIMONTHLY: timedelta(days=60),
  Frequency.QUARTERLY: timedelta(days=90),
  Frequency.SEMIANNUALLY: timedelta(days=180),
  Frequency.ANNUALLY: timedelta(days=365),
}

default_description_map = {
  PortfolioType.GROWTH: "Investments in the pursuit of long term growth and financial independence",
  PortfolioType.TARGET: "Investments to achieve a specific financial goal",
  PortfolioType.INVEST: "Investments in long term and high risk assets",
  PortfolioType.LIQUID: "Investments in short term and high liquid assets",
  PortfolioType.EMERGENCY: "Protection against financial emergencies and sudden loss of income",
  PortfolioType.INCOME: "Investing to earn income to meet current financial needs",
}