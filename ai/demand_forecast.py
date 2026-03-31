"""
Demand forecast — predict product demand using time series analysis.
Uses scikit-learn (linear regression with seasonal features) instead of Prophet
to keep dependencies lightweight.

Harbolnas dates: 1.1, 2.2, ..., 12.12
Payday: 1st, 2nd, 25th, 26th, 27th of each month
"""
import asyncio
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from core.celery_app import celery_app
from core.db import fetch
from core.logger import logger


HARBOLNAS_DATES = [(m, m) for m in range(1, 13)]  # (month, day)
PAYDAY_DAYS = {1, 2, 25, 26, 27}


def _build_features(dates: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"date": dates})
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_payday"] = df["day_of_month"].isin(PAYDAY_DAYS).astype(int)
    df["is_harbolnas"] = df.apply(
        lambda r: int((r["date"].month, r["date"].day) in HARBOLNAS_DATES),
        axis=1,
    )
    df["trend"] = np.arange(len(df))

    # Cyclical encoding for day of week and month
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    feature_cols = [
        "trend", "is_weekend", "is_payday", "is_harbolnas",
        "dow_sin", "dow_cos", "month_sin", "month_cos",
    ]
    return df[feature_cols]


async def forecast_product(product_id: int, horizon_days: int = 14) -> dict:
    rows = await fetch(
        """
        SELECT created_at::date as date, SUM(quantity) as qty
        FROM orders WHERE product_id = $1
        GROUP BY date ORDER BY date
        """,
        product_id,
    )

    if not rows or len(rows) < 14:
        return {"product_id": product_id, "error": "insufficient_data", "min_days": 14}

    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"])

    # Fill missing dates with 0
    date_range = pd.date_range(df["date"].min(), df["date"].max())
    df = df.set_index("date").reindex(date_range, fill_value=0).rename_axis("date").reset_index()

    X = _build_features(df["date"])
    y = df["qty"].values

    model = Ridge(alpha=1.0)
    model.fit(X, y)

    # Predict future
    future_dates = pd.Series([
        df["date"].max() + timedelta(days=i + 1)
        for i in range(horizon_days)
    ])
    X_future = _build_features(future_dates)
    X_future["trend"] = np.arange(len(df), len(df) + horizon_days)

    predictions = model.predict(X_future)
    predictions = np.maximum(predictions, 0).round().astype(int)

    total_forecast = int(predictions.sum())
    daily_avg = round(predictions.mean(), 1)

    logger.info(
        "demand_forecast",
        product_id=product_id, horizon=horizon_days,
        total=total_forecast, daily_avg=daily_avg,
    )

    return {
        "product_id": product_id,
        "horizon_days": horizon_days,
        "total_forecast": total_forecast,
        "daily_avg": daily_avg,
        "daily_predictions": [
            {"date": str(future_dates.iloc[i].date()), "qty": int(predictions[i])}
            for i in range(horizon_days)
        ],
    }


@celery_app.task(name="ai.demand_forecast.forecast_all")
def forecast_all():
    async def _run():
        products = await fetch("SELECT id FROM products WHERE is_active = TRUE")
        results = []
        for p in products:
            result = await forecast_product(p["id"])
            if "error" not in result:
                results.append(result)
        return {"forecasted": len(results)}

    return asyncio.run(_run())
