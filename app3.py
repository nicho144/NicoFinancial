"""
Financial Dashboard with Yield Curve Analysis & Risk Sentiment Engine
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from fredapi import Fred
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="📈 Market Sentiment Dashboard")

# --- Load FRED API Key from secrets.toml ---
try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except KeyError:
    st.error("FRED API key not found. Please set it in `.streamlit/secrets.toml`")
    st.stop()

# Initialize Fred API
fred = Fred(api_key= 'dceb19d6ccadfb4115c3ac2493b7d5ed')

# --- Helper Functions ---

@st.cache_data(ttl="1d")
def get_treasury_yields():
    try:
        return {
            'DGS2': round(fred.get_series('DGS2')[-1], 2),
            'DGS5': round(fred.get_series('DGS5')[-1], 2),
            'DGS10': round(fred.get_series('DGS10')[-1], 2)
        }
    except Exception as e:
        st.warning("Failed to fetch yields.")
        return {'DGS2': None, 'DGS5': None, 'DGS10': None}

@st.cache_data(ttl="1d")
def get_implied_fed_rate():
    try:
        ff = yf.Ticker("FF=F")
        hist = ff.history(period="2d")
        today_price = hist.iloc[-1]['Close']
        yesterday_price = hist.iloc[-2]['Close']
        implied_rate = round(100 - today_price, 2)
        prev_rate = round(100 - yesterday_price, 2)
        change = round(implied_rate - prev_rate, 2)
        return {
            'today': implied_rate,
            'prev': prev_rate,
            'change': change,
            'signal': "Risk Off" if change > 0 else "Risk On"
        }
    except:
        return {'error': "Could not fetch Fed Futures"}

@st.cache_data(ttl="1d")
def get_real_interest_rate():
    try:
        fed_rate = round(fred.get_series('DFF')[-1], 2)
        breakeven = round(fred.get_series('T10YIE')[-1], 2)
        real_rate = round(fed_rate - breakeven, 2)
        flow_signal = "Bonds Preferred" if real_rate > 0 else "Gold Preferred"
        return {
            'fed': fed_rate,
            'inflation': breakeven,
            'real': real_rate,
            'flow': flow_signal
        }
    except:
        return {'error': "Could not calculate real rates"}

@st.cache_data(ttl="1d")
def analyze_yield_curve(yields):
    try:
        yesterday = {k: fred.get_series(k, observation_end=datetime.now() - timedelta(days=1))[-1] for k in yields}
        slope_today = yields['DGS10'] - yields['DGS2']
        slope_yesterday = yesterday['DGS10'] - yesterday['DGS2']
        slope_change = round(slope_today - slope_yesterday, 2)

        spread_2y5y_today = yields['DGS5'] - yields['DGS2']
        spread_2y5y_yesterday = yesterday['DGS5'] - yesterday['DGS2']
        spread_2y5y_change = round(spread_2y5y_today - spread_2y5y_yesterday, 2)

        return {
            'slope': round(slope_today, 2),
            'slope_change': slope_change,
            'slope_signal': "Steepener" if slope_change > 0 else "Flattener",

            'spread_2y5y': round(spread_2y5y_today, 2),
            'spread_2y5y_change': spread_2y5y_change,
            'spread_2y5y_signal': "Steepener" if spread_2y5y_change > 0 else "Flattener",
        }
    except:
        return {'error': "Could not analyze curve"}

@st.cache_data(ttl="1h")
def get_market_prices():
    tickers = ['GC=F', 'ES=F', 'ZN=F', 'DX-Y.NYB']
    prices = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            today = hist.iloc[-1]['Close']
            yesterday = hist.iloc[-2]['Close']
            change = round(today - yesterday, 2)
            prices[ticker] = {"price": round(today, 2), "change": change}
        except:
            prices[ticker] = {"price": "N/A", "change": 0}
    return prices

# --- UI Begins ---

st.title("📊 Financial Market Sentiment Dashboard")
st.markdown("Generated: " + str(datetime.now().strftime("%Y-%m-%d %H:%M")))

# --- Data Fetching Section ---

with st.spinner("Fetching latest data..."):
    yields = get_treasury_yields()
    implied_rate = get_implied_fed_rate()
    real_rate = get_real_interest_rate()
    curve_analysis = analyze_yield_curve(yields)
    market_prices = get_market_prices()

# --- Main Table Generation ---

data = []

# Add Implied Fed Rate Row
data.append({
    "Indicator": "Implied Fed Funds Rate",
    "Today": f"{implied_rate['today']}%",
    "Yesterday": f"{implied_rate['prev']}%",
    "Change": f"{implied_rate['change']} bps",
    "Market Signal": "Hawkish Surprise" if implied_rate['change'] > 0 else "Dovish Surprise",
    "Risk Sentiment": implied_rate['signal']
})

# Real Interest Rate
data.append({
    "Indicator": "Real Interest Rate",
    "Today": f"{real_rate['real']}%",
    "Yesterday": "--",
    "Change": "--",
    "Market Signal": real_rate['flow'],
    "Risk Sentiment": "Bonds Favored" if real_rate['flow'] == "Bonds Preferred" else "Gold Favored"
})

# Yield Curve Slope
data.append({
    "Indicator": "2Y–10Y Spread",
    "Today": f"{curve_analysis['slope']} bps",
    "Yesterday": f"{curve_analysis['slope'] - curve_analysis['slope_change']} bps",
    "Change": f"{curve_analysis['slope_change']} bps",
    "Market Signal": curve_analysis['slope_signal'],
    "Risk Sentiment": "Risk On" if curve_analysis['slope_signal'] == "Steepener" else "Risk Off"
})

# 2Y–5Y Spread
data.append({
    "Indicator": "2Y–5Y Spread",
    "Today": f"{curve_analysis['spread_2y5y']} bps",
    "Yesterday": f"{curve_analysis['spread_2y5y'] - curve_analysis['spread_2y5y_change']} bps",
    "Change": f"{curve_analysis['spread_2y5y_change']} bps",
    "Market Signal": curve_analysis['spread_2y5y_signal'],
    "Risk Sentiment": "Risk On" if curve_analysis['spread_2y5y_signal'] == "Steepener" else "Risk Off"
})

# VIX Term Structure (placeholder logic using gold price movement)
vix_signal = "Contango" if market_prices['GC=F']['change'] > 0 else "Backwardation"
risk_vix = "Risk On" if vix_signal == "Contango" else "Risk Off"
data.append({
    "Indicator": "VIX Term Structure Proxy",
    "Today": vix_signal,
    "Yesterday": "--",
    "Change": "--",
    "Market Signal": "Volatility Regime Shift",
    "Risk Sentiment": risk_vix
})

# Convert to DataFrame
df = pd.DataFrame(data)

# Display Table
st.subheader("🔍 Market Indicators Summary")
st.dataframe(df.style.apply(lambda row: {
    "Risk Sentiment": "background-color: #ffcccc" if row["Risk Sentiment"] in ["Risk Off", "Gold Favored"] else "#ccffcc"
}, axis=1), use_container_width=True)

# --- Asset Class Projections ---

asset_projections = []
gold_signal = "Bullish" if df[df["Indicator"]=="Real Interest Rate"]["Market Signal"].iloc[0] == "Gold Preferred" else "Bearish"
spy_signal = "Bullish" if df[df["Indicator"]=="2Y–10Y Spread"]["Risk Sentiment"].iloc[0] == "Risk On" else "Bearish"
bond_signal = "Bearish" if df[df["Indicator"]=="Implied Fed Funds Rate"]["Change"].iloc[0] > "0 bps" else "Bullish"
usd_signal = "Bullish" if df[df["Indicator"]=="Real Interest Rate"]["Market Signal"].iloc[0] == "Bonds Preferred" else "Bearish"

asset_df = pd.DataFrame([
    {"Asset": "Gold (GC=F)", "Projection": gold_signal, "Reason": "Based on real rates"},
    {"Asset": "S&P 500 (SPY)", "Projection": spy_signal, "Reason": "Curve steepness implies risk-on"},
    {"Asset": "Treasury Bonds", "Projection": bond_signal, "Reason": "Rising expectations imply bear flattener"},
    {"Asset": "US Dollar Index (DXY)", "Projection": usd_signal, "Reason": "Real rate carry advantage"}
])

st.subheader("🎯 Asset Class Projections")
st.dataframe(asset_df.style.apply(lambda row: {
    "Projection": "color: green" if row["Projection"] == "Bullish" else "color: red"
}, axis=1), use_container_width=True)

# --- Visual Chart: Yield Curve Today vs Yesterday ---

yield_data = pd.DataFrame({
    'Tenor': ['2Y', '5Y', '10Y'],
    'Today (%)': [yields['DGS2'], yields['DGS5'], yields['DGS10']],
    'Yesterday (%)': [
        fred.get_series('DGS2', observation_end=datetime.now() - timedelta(days=1))[-1],
        fred.get_series('DGS5', observation_end=datetime.now() - timedelta(days=1))[-1],
        fred.get_series('DGS10', observation_end=datetime.now() - timedelta(days=1))[-1]
    ]
})

fig = px.line(yield_data.melt(id_vars='Tenor'),
              x='Tenor', y='value', color='variable',
              title="Treasury Yield Curve: Today vs Yesterday",
              labels={'value': 'Yield (%)', 'variable': 'Period'},
              markers=True)

st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("*Data sources: FRED, Yahoo Finance* | Dashboard built with Python + Streamlit")