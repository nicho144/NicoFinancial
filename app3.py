# app.py - Financial Dashboard (Robust Key Handling)
import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

# --- FRED API Setup ---
FRED_API_KEY = "dceb19d6ccadfb4115c3ac2493b7d5ed"
fred = Fred(api_key=FRED_API_KEY)

# --- Helper Function to Get Treasury Yields ---
def get_treasury_yields():
    try:
        return {
            'DGS2': round(fred.get_series('DGS2')[-1], 2),
            'DGS5': round(fred.get_series('DGS5')[-1], 2),
            'DGS10': round(fred.get_series('DGS10')[-1], 2)
        }
    except Exception as e:
        st.error("Failed to fetch yields from FRED")
        return {'DGS2': None, 'DGS5': None, 'DGS10': None}

yields = get_treasury_yields()

# --- Get Previous Day Yields for Curve Comparison ---
def get_prev_day_yields():
    yesterday = datetime.today() - timedelta(days=1)
    try:
        return {
            'DGS2': round(fred.get_series('DGS2', observation_end=yesterday)[-1], 2),
            'DGS5': round(fred.get_series('DGS5', observation_end=yesterday)[-1], 2),
            'DGS10': round(fred.get_series('DGS10', observation_end=yesterday)[-1], 2)
        }
    except:
        return {'DGS2': None, 'DGS5': None, 'DGS10': None}

prev_yields = get_prev_day_yields()

# --- Analyze Yield Curve Changes ---
def analyze_yield_curve(yields, prev_yields):
    if not all(yields.values()) or not all(prev_yields.values()):
        return {"error": "Missing yield data"}

    return {
        "slope_today": yields['DGS10'] - yields['DGS2'],
        "slope_yesterday": prev_yields['DGS10'] - prev_yields['DGS2'],
        "slope_change": (yields['DGS10'] - yields['DGS2']) - (prev_yields['DGS10'] - prev_yields['DGS2']),

        "steep_2y5y_today": yields['DGS5'] - yields['DGS2'],
        "steep_2y5y_yesterday": prev_yields['DGS5'] - prev_yields['DGS2'],
        "steep_2y5y_change": (yields['DGS5'] - yields['DGS2']) - (prev_yields['DGS5'] - prev_yields['DGS2']),
    }

curve_analysis = analyze_yield_curve(yields, prev_yields)

# --- Implied Fed Funds Rate (from Futures) ---
def get_implied_fed_rate():
    try:
        ff = yf.Ticker("FF=F")
        hist = ff.history(period="2d")
        today_price = hist.iloc[-1]['Close']
        yesterday_price = hist.iloc[-2]['Close']
        implied_rate = round(100 - today_price, 2)
        prev_rate = round(100 - yesterday_price, 2)
        change = round(implied_rate - prev_rate, 2)
        signal = "Risk Off" if change > 0 else "Risk On"
        return {
            'today': implied_rate,
            'prev': prev_rate,
            'change': change,
            'signal': signal
        }
    except:
        return {'error': True}

implied_rate = get_implied_fed_rate()

# --- Real Interest Rate Calculation ---
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
        return {'error': True}

real_rate_data = get_real_interest_rate()

# --- Market Prices With Safety ---
def get_market_prices():
    prices = {}
    tickers = ['SPY', 'GLD', 'DX-Y.NYB', 'ZN=F', 'ES=F']
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            today = hist.iloc[-1]['Close']
            yesterday = hist.iloc[-2]['Close']
            change = round(today - yesterday, 2)
            price = round(today, 2)

            # Generate signal based on asset class behavior
            if ticker in ['SPY', 'ES=F']:
                signal = "Bullish" if change > 0 else "Bearish"
            elif ticker in ['ZN=F', 'GLD', 'DX-Y.NYB']:
                signal = "Bullish" if change < 0 else "Bearish"  # Bonds/Dollar work inversely
            else:
                signal = "Neutral"

            prices[ticker] = {
                "price": price,
                "change": change,
                "signal": signal
            }

        except Exception as e:
            prices[ticker] = {
                "price": "N/A",
                "change": 0,
                "signal": "Neutral"
            }
    return prices

market_prices = get_market_prices()

# --- Gold vs Bonds Flow Signal ---
def gold_bond_flow(real_rate, market_prices):
    gold_change = market_prices.get('GLD', {}).get('change', 0)
    bond_change = market_prices.get('ZN=F', {}).get('change', 0)

    if real_rate.get('real', 0) < 0 and gold_change > 0 and bond_change < 0:
        return "🟡 Gold More Attractive Today"
    elif real_rate.get('real', 0) > 0 and gold_change < 0 and bond_change > 0:
        return "🟢 Bonds More Attractive"
    else:
        return "⚪ Neutral"

gold_bond_signal = gold_bond_flow(real_rate_data, market_prices)

# --- Risk-On / Risk-Off Aggregation ---
risk_score = 0
if curve_analysis.get("slope_change", 0) > 0:
    risk_score += 1
if market_prices.get("SPY", {}).get("signal") == "Bullish":
    risk_score += 1
if implied_rate.get("signal") == "Risk Off":
    risk_score += 1
if market_prices.get("DX-Y.NYB", {}).get("change") > 0:
    risk_score += 1

risk_mode = "🟢 Risk On" if risk_score <= 2 else "🔴 Risk Off"

# --- Streamlit UI ---

st.set_page_config(layout="wide", page_title="📈 Institutional Market Dashboard")

st.title("📊 Financial Market Sentiment Dashboard")
st.markdown(f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

# --- Section: Yield Curve Chart ---
if 'error' not in curve_analysis:
    yield_chart_data = pd.DataFrame({
        "Tenor": ["2Y", "5Y", "10Y"],
        "Today (%)": [yields['DGS2'], yields['DGS5'], yields['DGS10']],
        "Yesterday (%)": [prev_yields['DGS2'], prev_yields['DGS5'], prev_yields['DGS10']]
    })

    fig = px.line(
        yield_chart_data.melt(id_vars='Tenor'),
        x='Tenor', y='value', color='variable',
        title="🏛️ US Treasury Yield Curve: Today vs Yesterday",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Could not load yield curve comparison.")

# --- Section: Spreads Table ---
if 'error' not in curve_analysis:
    st.subheader("📉 Yield Spreads Analysis")
    df_spreads = pd.DataFrame({
        "Spread": ["2Y–5Y", "2Y–10Y"],
        "Today (bps)": [
            round(curve_analysis["steep_2y5y_today"], 2),
            round(curve_analysis["slope_today"], 2)
        ],
        "Change (bps)": [
            round(curve_analysis["steep_2y5y_change"], 2),
            round(curve_analysis["slope_change"], 2)
        ],
        "Interpretation": [
            "Steepener ↑" if curve_analysis["steep_2y5y_today"] > curve_analysis["steep_2y5y_yesterday"] else "Flattener ↓",
            "Curve Steepened ↑" if curve_analysis["slope_change"] > 0 else "Curve Flattened ↓"
        ]
    })
    st.dataframe(df_spreads.style.apply(lambda row: {
        "Spread": "background-color: #ffcccc" if row["Change (bps)"] < 0 else "#ccffcc"
    }, axis=1), use_container_width=True)

# --- Section: Implied Fed Rate ---
st.subheader("🏦 Implied Fed Funds Expectations")
if 'error' not in implied_rate:
    st.write(f"Today: `{implied_rate['today']}%` | "
             f"Yesterday: `{implied_rate['prev']}%` | "
             f"Change: `{implied_rate['change']} bps` → **{implied_rate['signal']}**")
else:
    st.write("⚠️ Could not retrieve Fed Futures data")

# --- Section: Real Interest Rate ---
st.subheader("🧮 Real Interest Rate")
if 'error' not in real_rate_data:
    st.write(f"Federal Funds: `{real_rate_data['fed']}%` | "
             f"Inflation (Breakeven): `{real_rate_data['inflation']}%` | "
             f"Real Rate: `{real_rate_data['real']}%` → **{real_rate_data['flow']}**")
else:
    st.write("⚠️ Could not calculate real interest rate")

# --- Section: Market Futures Validation ---
st.subheader("💱 Futures Price Movement")
cols = st.columns(len(market_prices))
for i, (ticker, info) in enumerate(market_prices.items()):
    cols[i].metric(ticker, f"${info['price']}", delta=f"{info['change']}")
    cols[i].write(f"Signal: **{info['signal']}**")

# --- Section: Institutional Flow Prediction ---
st.subheader("🧠 Smart Money: Gold or Bonds?")
st.markdown(f"#### 💡 Today's Flow Signal: **{gold_bond_signal}**")

# --- Final Risk Mode Summary ---
st.subheader("🔥 Final Market Risk Sentiment")
st.markdown(f"# **{risk_mode}**")

# --- Footer ---
st.markdown("---")
st.markdown("*Data Sources: FRED, Yahoo Finance* | Dashboard built with Python + Streamlit")