import streamlit as st
import pandas as pd
import plotly.express as px

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
st.plotly_chart(fig1, use_container_width=True)

st.subheader("📦 Inventory per Category")
cat_inv = filtered_df.groupby('Category')['Inventory Level'].sum().reset_index()
fig2 = px.bar(cat_inv, x='Category', y='Inventory Level', title="Total Inventory by Category", color='Inventory Level')
st.plotly_chart(fig2, use_container_width=True)

st.subheader("🌍 Inventory per Region")
reg_inv = filtered_df.groupby('Region')['Inventory Level'].sum().reset_index()
fig3 = px.pie(reg_inv, names='Region', values='Inventory Level', title="Inventory Distribution by Region")
st.plotly_chart(fig3, use_container_width=True)

# Optional: Add more KPIs or trend analysis
st.markdown("---")
st.caption("Developed with ❤️ using Streamlit")
