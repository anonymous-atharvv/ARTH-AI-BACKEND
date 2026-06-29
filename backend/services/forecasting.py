# backend/services/forecasting.py
"""
Simple but principled cash flow forecasting.
Uses weighted moving average with day-of-week seasonality.
No ML dependency — works with 30+ days of data.
"""
from datetime import date, timedelta
from collections import defaultdict
import numpy as np
from config import settings

async def forecast_cash_flow(db, user_id: str, forecast_days: int = 30) -> dict:
    """
    Returns forecasted daily net cash flow for next N days.
    Method: STL decomposition-lite with DoW seasonality.
    """
    from models.transaction import Transaction
    from sqlalchemy import select, and_

    # Need 90 days of history for reliable seasonal patterns
    history_days = 90
    cutoff = (date.today() - timedelta(days=history_days)).isoformat()

    result = await db.execute(
        select(Transaction).where(
            and_(Transaction.user_id == user_id, Transaction.transaction_date >= cutoff)
        )
    )
    txs = result.scalars().all()

    if len(txs) < 30:
        if settings.DEMO_MODE:
            # Let's generate a mock forecast for demonstration with standard weekly seasonality
            forecast = []
            cumulative = 0
            dow_avg = {0: 1500.0, 1: 1800.0, 2: 1200.0, 3: 2000.0, 4: 2500.0, 5: 3500.0, 6: -500.0}
            for i in range(1, forecast_days + 1):
                forecast_date = date.today() + timedelta(days=i)
                dow = forecast_date.weekday()
                daily_forecast = dow_avg[dow]
                cumulative += daily_forecast
                forecast.append({
                    "date": forecast_date.isoformat(),
                    "label": forecast_date.strftime("%b %d"),
                    "forecast_net": round(daily_forecast, 0),
                    "cumulative": round(cumulative, 0),
                    "day_of_week": forecast_date.strftime("%A"),
                    "is_forecast": True,
                })
            avg_daily = sum(f["forecast_net"] for f in forecast) / len(forecast)
            return {
                "available": True,
                "forecast": forecast,
                "projected_monthly_net": round(avg_daily * 30, 0),
                "confidence": "medium",
                "based_on_days": history_days,
            }
        else:
            return {"available": False, "reason": "Need 30+ transactions for forecasting"}

    # Build daily net by day-of-week
    dow_nets = defaultdict(list)  # 0=Monday, 6=Sunday
    for t in txs:
        # Safeguard: handle date objects directly or as string
        tx_date_val = t.transaction_date
        if hasattr(tx_date_val, "isoformat"):
            tx_date = tx_date_val
        else:
            tx_date_str = str(tx_date_val)[:10]
            tx_date = date.fromisoformat(tx_date_str)
            
        sign = 1 if t.type == "income" else -1
        dow = tx_date.weekday()
        # We aggregate per-date, then bucket by DoW
        dow_nets[dow].append((tx_date, sign * float(t.amount)))

    # Calculate DoW averages
    dow_avg = {}
    for dow, entries in dow_nets.items():
        # Group by date first
        date_totals = defaultdict(float)
        for d, amount in entries:
            date_totals[d] += amount
        dow_avg[dow] = np.mean(list(date_totals.values())) if date_totals else 0

    # Generate forecast
    forecast = []
    cumulative = 0
    for i in range(1, forecast_days + 1):
        forecast_date = date.today() + timedelta(days=i)
        dow = forecast_date.weekday()
        daily_forecast = dow_avg.get(dow, np.mean(list(dow_avg.values())) if dow_avg else 0)
        cumulative += daily_forecast
        forecast.append({
            "date": forecast_date.isoformat(),
            "label": forecast_date.strftime("%b %d"),
            "forecast_net": round(daily_forecast, 0),
            "cumulative": round(cumulative, 0),
            "day_of_week": forecast_date.strftime("%A"),
            "is_forecast": True,
        })

    avg_daily = np.mean([f["forecast_net"] for f in forecast])
    return {
        "available": True,
        "forecast": forecast,
        "projected_monthly_net": round(avg_daily * 30, 0),
        "confidence": "medium" if len(txs) >= 60 else "low",
        "based_on_days": history_days,
    }
