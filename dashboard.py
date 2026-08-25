from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

MODEL_DIR = Path(__file__).resolve().parent / "model"

# Load data
df = pd.read_csv("inventory_forecasting.csv")

# Convert 'Date' to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Title and Sidebar
st.set_page_config(page_title="Inventory KPI Dashboard", layout="wide")
st.title("📦 Inventory KPI Dashboard")

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filter Options")
    selected_region = st.multiselect("Select Region", options=df['Region'].unique(), default=df['Region'].unique())
    selected_category = st.multiselect("Select Category", options=df['Category'].unique(), default=df['Category'].unique())
    selected_store = st.multiselect("Select Store ID", options=df['Store ID'].unique(), default=df['Store ID'].unique())

# Filter data based on selections
filtered_df = df[
    (df['Region'].isin(selected_region)) &
    (df['Category'].isin(selected_category)) &
    (df['Store ID'].isin(selected_store))
]

# KPIs
col1, col2 = st.columns(2)

with col1:
    stockout_rate = round(100 * (filtered_df['Units Sold'] > filtered_df['Inventory Level']).sum() / len(filtered_df), 2)
    st.metric("📉 Stockout Rate (%)", f"{stockout_rate}%")

with col2:
    avg_inventory = round(filtered_df['Inventory Level'].mean(), 2)
    st.metric("📦 Avg Inventory Level", avg_inventory)

# Charts
st.subheader("📈 Inventory Level Over Time")
daily_inventory = filtered_df.groupby('Date')['Inventory Level'].mean().reset_index()
st.line_chart(daily_inventory.rename(columns={'Inventory Level': 'Avg Inventory Level'}).set_index('Date'))

st.subheader("🏬 Total Inventory per Store")
store_inv = filtered_df.groupby('Store ID')['Inventory Level'].sum().reset_index()
fig1 = px.bar(store_inv, x='Store ID', y='Inventory Level', title="Total Inventory by Store", color='Inventory Level')
st.plotly_chart(fig1, width='stretch')

st.subheader("📦 Inventory per Category")
cat_inv = filtered_df.groupby('Category')['Inventory Level'].sum().reset_index()
fig2 = px.bar(cat_inv, x='Category', y='Inventory Level', title="Total Inventory by Category", color='Inventory Level')
st.plotly_chart(fig2, width='stretch')

st.subheader("🌍 Inventory per Region")
reg_inv = filtered_df.groupby('Region')['Inventory Level'].sum().reset_index()
fig3 = px.pie(reg_inv, names='Region', values='Inventory Level', title="Inventory Distribution by Region")
st.plotly_chart(fig3, width='stretch')

# Demand Forecast Model
st.markdown("---")
st.subheader("🔮 Demand Forecast Model")

predictions_path = MODEL_DIR / "forecast_predictions.csv"
importance_path = MODEL_DIR / "feature_importance.csv"

if not predictions_path.exists():
    st.info(
        "No trained forecast yet. Run `py model/train_forecast.py` from the "
        "project root to generate predictions, then reload this page."
    )
else:
    preds_df = pd.read_csv(predictions_path)
    preds_df["Date"] = pd.to_datetime(preds_df["Date"])

    # Respect the sidebar's Region/Category/Store filters so this section
    # stays consistent with the KPIs and charts above.
    filtered_preds = preds_df[
        (preds_df["Region"].isin(selected_region))
        & (preds_df["Category"].isin(selected_category))
        & (preds_df["Store ID"].isin(selected_store))
    ]

    def mape(actual: pd.Series, predicted: pd.Series) -> float:
        nonzero = actual != 0
        return round((((actual[nonzero] - predicted[nonzero]) / actual[nonzero]).abs().mean()) * 100, 2)

    if filtered_preds.empty:
        st.warning("No forecast rows match the current sidebar filters.")
    else:
        model_mape = mape(filtered_preds["Actual"], filtered_preds["Model_Prediction"])
        baseline_mape = mape(filtered_preds["Actual"], filtered_preds["Baseline_Demand_Forecast"])

        col3, col4 = st.columns(2)
        with col3:
            st.metric("🌲 Trained Model MAPE", f"{model_mape}%")
        with col4:
            st.metric(
                "📋 Dataset's Built-in Forecast MAPE",
                f"{baseline_mape}%",
                delta=f"{round(model_mape - baseline_mape, 2)} pp vs trained model",
                delta_color="inverse",
            )
        st.caption(
            "Trained model uses only information legitimately known ahead of "
            "time (price, discount, weather, holiday flag, 7-day rolling sales/"
            "inventory history) — no same-day inventory level. The dataset's "
            "own Demand Forecast column correlates at r≈0.93 with actual Units "
            "Sold, consistent with it being generated as target-plus-noise "
            "rather than an independently derived forecast, which is why it's "
            "a hard baseline to beat fairly. See model/train_forecast.py."
        )

        st.markdown("**Actual vs. Forecast for a Store/Product**")
        pick_col1, pick_col2 = st.columns(2)
        with pick_col1:
            pick_store = st.selectbox("Store ID", options=sorted(filtered_preds["Store ID"].unique()))
        with pick_col2:
            product_options = sorted(filtered_preds.loc[filtered_preds["Store ID"] == pick_store, "Product ID"].unique())
            pick_product = st.selectbox("Product ID", options=product_options)

        series = filtered_preds[
            (filtered_preds["Store ID"] == pick_store) & (filtered_preds["Product ID"] == pick_product)
        ].sort_values("Date")

        fig_forecast = px.line(
            series,
            x="Date",
            y=["Actual", "Baseline_Demand_Forecast", "Model_Prediction"],
            title=f"Actual vs. Forecast — {pick_store} / {pick_product}",
            labels={"value": "Units Sold", "variable": "Series"},
        )
        st.plotly_chart(fig_forecast, width='stretch')

        if importance_path.exists():
            st.markdown("**What drives the trained model's predictions**")
            importance_df = pd.read_csv(importance_path).head(10)
            fig_importance = px.bar(
                importance_df.sort_values("importance"),
                x="importance",
                y="feature",
                orientation="h",
                title="Top 10 Feature Importances (RandomForest)",
            )
            st.plotly_chart(fig_importance, width='stretch')

# Optional: Add more KPIs or trend analysis
st.markdown("---")
st.caption("Developed with ❤️ using Streamlit")
