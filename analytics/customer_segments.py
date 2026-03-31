"""
Customer segmentation using RFM (Recency, Frequency, Monetary) clustering.
Uses scikit-learn KMeans.
"""
import asyncio

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from core.celery_app import celery_app
from core.db import execute, fetch
from core.logger import logger

SEGMENT_LABELS = {
    0: "champions",
    1: "loyal",
    2: "potential",
    3: "at_risk",
    4: "hibernating",
}


async def compute_rfm() -> pd.DataFrame:
    rows = await fetch(
        """
        SELECT buyer_phone,
               EXTRACT(DAY FROM NOW() - MAX(created_at)) as recency,
               COUNT(*) as frequency,
               SUM(sale_price_idr) as monetary
        FROM orders
        WHERE buyer_phone IS NOT NULL AND buyer_phone != ''
        GROUP BY buyer_phone
        HAVING COUNT(*) >= 1
        """
    )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    df["recency"] = df["recency"].astype(int)
    df["frequency"] = df["frequency"].astype(int)
    df["monetary"] = df["monetary"].astype(int)

    return df


async def segment_customers(n_clusters: int = 5) -> dict:
    df = await compute_rfm()

    if df.empty or len(df) < n_clusters:
        return {"error": "insufficient_data", "count": len(df)}

    features = df[["recency", "frequency", "monetary"]].values

    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=min(n_clusters, len(df)), random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(scaled)

    # Assign labels based on cluster centers
    centers = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_),
        columns=["recency", "frequency", "monetary"],
    )

    # Sort by monetary desc to assign best labels to best clusters
    cluster_rank = centers["monetary"].rank(ascending=False).astype(int) - 1
    label_map = {cluster: SEGMENT_LABELS.get(rank, f"segment_{rank}") for cluster, rank in cluster_rank.items()}
    df["segment"] = df["cluster"].map(label_map)

    # Save to DB
    for _, row in df.iterrows():
        await execute(
            """
            INSERT INTO customer_segments (customer_phone, segment, recency_days, frequency, monetary_idr)
            VALUES ($1, $2, $3, $4, $5)
            """,
            row["buyer_phone"], row["segment"],
            int(row["recency"]), int(row["frequency"]), int(row["monetary"]),
        )

    summary = df.groupby("segment").agg(
        count=("buyer_phone", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
    ).to_dict("index")

    logger.info("customer_segmentation_done", total=len(df), segments=len(summary))
    return {"total": len(df), "segments": summary}


@celery_app.task(name="analytics.customer_segments.run_segmentation")
def run_segmentation():
    return asyncio.run(segment_customers())
