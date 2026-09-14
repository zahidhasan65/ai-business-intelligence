import pandas as pd
from pathlib import Path

OUT = Path("ml/outputs")

master_path = OUT / "product_management_master_phase3_7_final.csv"
pred_path = OUT / "demand_test_predictions_phase2_4.csv"
anom_path = OUT / "product_anomaly_intelligence_phase3.csv"

master = pd.read_csv(master_path)
pred = pd.read_csv(pred_path)

# ---------------------------------------------------------
# 1. FIX FORECAST GROWTH
# ---------------------------------------------------------
master["forecast_growth_pct"] = (
    (master["forecast_demand"] / master["last_month_demand"].replace(0, pd.NA)) - 1
) * 100

master["forecast_growth_pct"] = master["forecast_growth_pct"].round(4)

# ---------------------------------------------------------
# 2. ADD ACTUAL vs EXPECTED DEMAND FROM HOLDOUT PREDICTIONS
# ---------------------------------------------------------
pred_latest = (
    pred.sort_values(["product_id", "month"])
        .drop_duplicates("product_id", keep="last")
        [["product_id", "month", "demand_units", "predicted_demand", "residual"]]
        .copy()
)

pred_latest = pred_latest.rename(columns={
    "month": "anomaly_month",
    "demand_units": "actual_demand",
    "predicted_demand": "expected_demand",
    "residual": "forecast_residual"
})

# Remove old versions if rerunning
for col in [
    "anomaly_month",
    "actual_demand",
    "expected_demand",
    "forecast_residual"
]:
    if col in master.columns:
        master = master.drop(columns=[col])

master = master.merge(
    pred_latest,
    on="product_id",
    how="left"
)

# ---------------------------------------------------------
# 3. ANOMALY TYPE
# ---------------------------------------------------------
master["anomaly_type"] = "normal"

master.loc[
    master["forecast_residual"] >= 2,
    "anomaly_type"
] = "forecast_demand_spike"

master.loc[
    master["forecast_residual"] <= -2,
    "anomaly_type"
] = "forecast_demand_drop"

# Preserve historical anomaly information when available
if anom_path.exists():
    historical = pd.read_csv(anom_path)

    if "product_id" in historical.columns and "anomaly_type" in historical.columns:
        h = historical[["product_id", "anomaly_type"]].drop_duplicates("product_id")
        h = h.rename(columns={"anomaly_type": "historical_anomaly_type"})

        master = master.merge(h, on="product_id", how="left")

        master.loc[
            master["historical_anomaly_type"].notna() &
            master["historical_anomaly_type"].ne("normal") &
            master["anomaly_type"].eq("normal"),
            "anomaly_type"
        ] = master["historical_anomaly_type"]

        master = master.drop(columns=["historical_anomaly_type"])

# ---------------------------------------------------------
# 4. SAVE UPDATED MASTER
# ---------------------------------------------------------
master.to_csv(master_path, index=False)

# Update calibrated trend output
trend_cols = [
    "product_id",
    "category",
    "forecast_demand",
    "forecast_growth_pct",
    "forecast_vs_3m_pct",
    "meaningful_forecast_pct",
    "forecast_delta_vs_3m",
    "growth_signal",
    "trend_strength"
]

master[trend_cols].to_csv(
    OUT / "product_calibrated_trends_phase3_7_final.csv",
    index=False
)

# Update anomaly output
anomaly_cols = [
    "product_id",
    "category",
    "anomaly_month",
    "actual_demand",
    "expected_demand",
    "forecast_residual",
    "anomaly_type",
    "anomaly_severity",
    "anomaly_flag",
    "risk_score",
    "decision_priority"
]

master[anomaly_cols].to_csv(
    OUT / "product_anomaly_decision_risk_phase3_7_final.csv",
    index=False
)

print("\n=== PHASE 6.1 PATCH COMPLETE ===")
print("Products:", len(master))
print("Unique products:", master.product_id.nunique())
print("Forecast growth NULL:", int(master.forecast_growth_pct.isna().sum()))
print("Actual demand NULL:", int(master.actual_demand.isna().sum()))
print("Expected demand NULL:", int(master.expected_demand.isna().sum()))
print("\nAnomaly types:")
print(master.anomaly_type.value_counts(dropna=False))
