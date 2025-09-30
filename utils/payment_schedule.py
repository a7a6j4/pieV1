from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional

def generate_schedule_dates(
    start_date: datetime, 
    frequency: str, 
    duration: Optional[int] = None, 
    default_periods: int = 12
) -> List[datetime]:
    """
    Generate a list of dates based on frequency and duration
    
    Args:
        start_date (datetime): The starting date
        frequency (str): The frequency type ('daily', 'weekly', 'monthly', 'quarterly', 'semiannually', 'annually')
        duration (Optional[int]): The number of periods. If None, 0, or negative, will use default_periods
        default_periods (int): Number of periods to generate when duration is not specified (default: 12)
        
    Returns:
        List[datetime]: List of dates for the schedule
    """
    dates = []
    frequency_map = {
        'daily': lambda d: d + timedelta(days=1),
        'weekly': lambda d: d + timedelta(weeks=1),
        'monthly': lambda d: d + relativedelta(months=1),
        'quarterly': lambda d: d + relativedelta(months=3),
        'semiannually': lambda d: d + relativedelta(months=6),
        'annually': lambda d: d + relativedelta(years=1)
    }

    if frequency.lower() not in frequency_map:
        raise ValueError(f"Unsupported frequency: {frequency}. Must be one of {', '.join(frequency_map.keys())}")

    # Use default_periods if duration is None, 0, or negative
    periods = default_periods if duration is None or duration <= 0 else duration

    current_date = start_date
    dates.append(current_date)
    
    for _ in range(periods - 1):  # -1 because we already added the start date
        current_date = frequency_map[frequency.lower()](current_date)
        dates.append(current_date)
    
    return dates
