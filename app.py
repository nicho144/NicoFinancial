import yfinance as yf
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# Fetch Futures Data
def load_futures_data(symbols):
    changes = {}
    for symbol in symbols:
        data = yf.download(symbol, period="2d", interval="1d")
        if 'Adj Close' in data.columns:
            change = data["Adj Close"].iloc[-1] - data["Adj Close"].iloc[-2]
            changes[symbol] = change
    return changes

# Calculate Implied Rate from Fed Funds Futures
def get_implied_rate(symbol):
    data = yf.download(symbol, period="1d", interval="1d")
    if 'Adj Close' in data.columns:
        implied_rate = 100 - data['Adj Close'].iloc[-1]  # Implied rate is 100 minus price
        return implied_rate
    else:
        return None

# Fetch Inflation Data (Example, needs real CPI symbol)
def get_inflation_data():
    inflation_symbol = "CPIAUCNS"  # Example CPI symbol, replace with actual one
    data = yf.download(inflation_symbol, period="1d", interval="1d")
    if 'Adj Close' in data.columns:
        inflation_rate = data['Adj Close'].iloc[-1]
        return inflation_rate
    else:
        return None

# Calculate Real Rate: Nominal Rate - Inflation Rate
def calculate_real_rate(nominal_rate, inflation_rate):
    if nominal_rate is not None and inflation_rate is not None:
        return nominal_rate - inflation_rate
    else:
        return None

# Determine Risk-On or Risk-Off based on multiple factors
def determine_risk_on_off(real_rate_change, vix_change, treasury_spread_change):
    if real_rate_change < 0 and vix_change < 0 and treasury_spread_change < 0:
        return "Risk-On"
    elif real_rate_change > 0 and vix_change > 0 and treasury_spread_change > 0:
        return "Risk-Off"
    else:
        return "Neutral"

# Plotting Yield Curve
def plot_yield_curve():
    # Example data for the Yield Curve (you will replace this with actual yield data)
    maturities = ['1Y', '2Y', '5Y', '10Y', '30Y']
    yields = [0.2, 0.5, 1.0, 1.5, 2.0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=maturities, y=yields, mode='lines+markers', name='Yield Curve'))
    fig.update_layout(title="Treasury Yield Curve",
                      xaxis_title="Maturity",
                      yaxis_title="Yield (%)",
                      template="plotly_dark")
    st.plotly_chart(fig)

# Displaying data on Streamlit
st.title("Financial Risk Analysis Dashboard")

# Example Usage of Data Fetching and Calculation
fed_funds_symbol = "FF=F"  # Example symbol for Fed Funds futures
implied_rate = get_implied_rate(fed_funds_symbol)
inflation_rate = get_inflation_data()
real_rate = calculate_real_rate(implied_rate, inflation_rate)

# Display values on Streamlit
st.write(f"Implied Rate for Fed Funds Futures: {implied_rate}")
st.write(f"Inflation Rate (CPI): {inflation_rate}")
st.write(f"Real Rate: {real_rate}")

# Risk-On / Risk-Off Decision based on example changes
real_rate_change = -0.02  # Example data for changes
vix_change = -0.01  # Example data for VIX change
treasury_spread_change = -0.005  # Example data for Treasury Spread change
risk_status = determine_risk_on_off(real_rate_change, vix_change, treasury_spread_change)
st.write(f"Risk Status: {risk_status}")

# Displaying Yield Curve Plot
plot_yield_curve()

# Example: Loading and displaying Futures Changes
symbols = ["ES=F", "NQ=F", "GC=F"]  # Example futures symbols (S&P, Nasdaq, Gold)
futures_changes = load_futures_data(symbols)
st.write(f"Futures Changes: {futures_changes}")

# Example: Yield Curve and Spread Analysis
treasury_spread_change = -0.02  # Example data for Treasury Spread
if treasury_spread_change < 0:
    st.write("The Treasury Yield Curve is Flattening")
else:
    st.write("The Treasury Yield Curve is Steepening")

# Visualize Yield Curve Movement for the Day
if treasury_spread_change < 0:
    st.write("Treasury Spreads are Narrowing - Risk-On")
else:
    st.write("Treasury Spreads are Widening - Risk-Off")

# Example: Monitoring Unusual Options Activity (Placeholder)
# Placeholder for Unusual Options Activity logic
st.write("Unusual Options Activity: Data pending...")

# Display Premarket Analysis (example data)
st.write("Premarket Analysis: Gold Futures, VIX Futures, DXY Futures, Bond Futures")

# Display Sector Status (example data)
st.write("Sector Status: Pending data")

# Example of Volatility Metrics (VIX Premium)
vix_premium = 0.5  # Example data
if vix_premium > 1:
    st.write("VIX Premium is Expensive - Risk-Off")
else:
    st.write("VIX Premium is Cheap - Risk-On")
