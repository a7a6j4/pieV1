import schemas

async def runAssesment(data: schemas.RiskProfileSchema):

  total_score = 0

  for key, value in data.model_dump().items():
    if key == "is_single":
      if value:
        total_score += 3
      else:
        total_score += 2
    
    if key == "household_income":
      if value == schemas.HouseholdIncome.SINGLE:
        total_score += 1
      elif value == schemas.HouseholdIncome.DOUBLE:
        total_score += 3
    
    if key == "primary_provider":
      if value:
        total_score += 3
      else:
        total_score += 1
    
    if key == "monthly_income":
      if value <= 1000000:
        total_score += 1
      elif value <= 3000000:
        total_score += 2
      elif value <= 5000000:
        total_score += 3
      elif value <= 75000000:
        total_score += 4
      elif value <= 10000000:
        total_score += 5
      elif value <= 15000000:
        total_score += 6
      else:
        total_score += 7
    
    if key == "annual_rent":
      if value <= 1000000:
        total_score += 7
      elif value <= 3000000:
        total_score += 6
      elif value <= 5000000:
        total_score += 5
      elif value <= 75000000:
        total_score += 4
      elif value <= 10000000:
        total_score += 3
      elif value <= 15000000:
        total_score += 2
      else:
        total_score += 1

    if key == "primary_income_currency":
      if value == "USD":
        total_score += 3
      elif value == "NGN":
        total_score += 1
    
    if key == "primary_income_source":
      if value == schemas.IncomeSource.SALARY:
        total_score += 2
      elif value == schemas.IncomeSource.BUSINESS:
        total_score += 1
      elif value == schemas.IncomeSource.INVESTMENT:
        total_score += 3
      elif value == schemas.IncomeSource.OTHER:
        total_score += 2

    if key == "children":
      if value < 1:
        total_score += 4
      if value < 2:
        total_score += 3
      if value < 3:
        total_score += 2
      if value >= 3:
        total_score += 1

    if key == 'dependents':
      if value < 1:
        total_score += 4
      if value < 2:
        total_score += 3
      if value < 3:
        total_score += 2
      if value >= 3:
        total_score += 1

    if key == "wealth_value":
      if value <= 1000000:
        total_score += 1
      elif value <= 3000000:
        total_score += 2
      elif value <= 5000000:
        total_score += 3
      elif value <= 75000000:
        total_score += 4
      elif value <= 10000000:
        total_score += 5
      elif value <= 15000000:
        total_score += 6
      else:
        total_score += 7

  if total_score <= 15:
    return schemas.RiskLevel.LOW
  elif total_score <= 25:
    return schemas.RiskLevel.MODERATE
  else:
    return schemas.RiskLevel.HIGH

