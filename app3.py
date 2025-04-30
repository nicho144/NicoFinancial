# app.py - Full Financial Dashboard with Hardcoded FRED API Key
# ALL original features included

import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import requests

# --- HARDWIRED FRED API KEY ---
FRED_API_KEY = "dceb19d6ccadfb4115c3ac2493b7d5ed"
fred = Fred(api_key=FRED_API_KEY)

# --- Fetch Treasury Yields ---
def get_treasury_yields():
    return {
        'DGS2': round(fred.get_series('DGS2')[-1], 2),
        'DGS5': round(fred.get_series('DGS5')[-1], 2),
        'DGS10': round(fred.get_series('DGS10')[-1], 2)
    }

yields = get_treasury_yields()

# --- Get Previous Day Yields ---
def get_prev_day_yields():
    yesterday = datetime.today() - timedelta(days=1)
    return {
        'DGS2': round(fred.get_series('DGS2', observation_end=yesterday)[-1], 2),
        'DGS5': round(fred.get_series('DGS5', observation_end=yesterday)[-1], 2),
        'DGS10': round(fred.get_series('DGS10', observation_end=yesterday)[-1], 2)
    }

prev_yields = get_prev_day_yields()

# --- Yield Curve Spreads Today ---
slope_2y10y = yields['DGS10'] - yields['DGS2']
slope_2y5y = yields['DGS5'] - yields['DGS2']

# --- Yesterday Comparison ---
prev_slope_2y10y = prev_yields['DGS10'] - prev_yields['DGS2']
prev_slope_2y5y = prev_yields['DGS5'] - prev_yields['DGS2']

# --- Implied Fed Funds Rate via Fed Funds Futures ---
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
    except Exception as e:
        return {'error': f"Fed Fund Futures error: {e}"}

implied_rate = get_implied_fed_rate()

# --- Real Interest Rates ---
def get_real_interest_rate():
    try:
        fed_rate = round(fred.get_series('DFF')[-1], 2)
        breakeven = round(fred.get_series('T10YIE')[-1], 2)
        real_rate = round(fed_rate - breakeven, 2)
        flow_signal = "Gold Preferred" if real_rate < 0 else "Bonds Preferred"
        return {
            'fed': fed_rate,
            'inflation': breakeven,
            'real': real_rate,
            'flow': flow_signal
        }
    except:
        return {'error': "Could not calculate real rates"}

real_rate = get_real_interest_rate()

# --- Market Price Validation ---
def get_market_prices():
    prices = {}
    for ticker in ['SPY', 'GLD', 'DX-Y.NYB', 'ZN=F', 'ES=F']:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            today = round(hist.iloc[-1]['Close'], 2)
            yesterday = round(hist.iloc[-2]['Close'], 2)
            prices[ticker] = {
                'price': today,
                'change': today - yesterday,
                'signal': "Bullish" if (ticker in ['SPY','ES=F'] and today > yesterday) or \
                                    (ticker in ['ZN=F','GLD','DX-Y.NYB'] and today < yesterday) \
                            else "Bearish" if (ticker in ['SPY','ES=F'] and today < yesterday) or \
                                     (ticker in ['ZN=F','GLD','DX-Y.NYB'] and today > yesterday) \
                                 else "Neutral"
            }
        except:
            prices[ticker] = {'price': None, 'change': 0}
    return prices

market_data = get_market_prices()

# --- VIX Term Structure Proxy ---
def get_vix_term_structure():
    url = "https://cdn.cboe.com/api/global/us_indices/dashboard/volatility_dashboard_data.json"
    try:
        response = requests.get(url).json()
        vix_spot = response["data"]["vix"]
        vix_futures = response["data"]["vix_futures"]
        front = vix_futures[0]["value"]
        back = vix_futures[1]["value"]
        spread = round(back - front, 2)
        signal = "Contango" if spread > 0 else "Backwardation"
        return {
            'spot': round(vix_spot, 2),
            'front': round(front, 2),
            'back': round(back, 2),
            'spread': spread,
            'signal': signal
        }
    except:
        return {"error": "Could not fetch VIX data"}

vix_data = get_vix_term_structure()

# --- Risk Mode Aggregation ---
risk_score = 0
if slope_2y10y > prev_slope_2y10y:
    risk_score += 1
if market_data['SPY']['signal'] == "Bullish":
    risk_score += 1
if implied_rate['change'] > 0:
    risk_score += 1
if vix_data.get("signal", "") == "Contango":
    risk_score += 1

risk_mode = "🟢 Risk On" if risk_score >= 3 else "🔴 Risk Off"

# --- Gold vs Bonds Flow Signal ---
gold_bond_signal = "--"
if real_rate['flow'] == "Gold Preferred" and market_data['GLD']['change'] > 0:
    gold_bond_signal = "🟡 Gold More Attractive"
elif real_rate['flow'] == "Bonds Preferred" and market_data['ZN=F']['change'] < 0:
    gold_bond_signal = "🟢 Bonds Preferred"
else:
    gold_bond_signal = "⚪ Neutral"

# --- Streamlit UI ---

st.set_page_config(layout='wide', page_title="Financial Dashboard")

st.title("🌐 Enhanced Financial Sentiment Dashboard")
st.markdown(f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

# --- Section 1: Yield Curve ---
with st.expander("🏛️ US Treasury Yield Curve", expanded=True):
    df_curve = pd.DataFrame({
        'Tenor': ['2Y', '5Y', '10Y'],
        'Today (%)': [yields['DGS2'], yields['DGS5'], yields['DGS10']],
        'Yesterday (%)': [prev_yields['DGS2'], prev_yields['DGS5'], prev_yields['DGS10']]
    })

    st.write("### Yield Curve Today vs Yesterday")
    st.dataframe(df_curve, use_container_width=True)

    fig = px.line(df_curve.melt(id_vars='Tenor'), x='Tenor', y='value', color='variable',
                  title="📉 Treasury Yield Curve Over Time", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# --- Section 2: Spreads ---
with st.expander("📊 Yield Spreads Analysis"):
    col1, col2 = st.columns(2)
    col1.metric("2Y–10Y Spread", f"{slope_2y10y} bps",
                delta=f"{round(slope_2y10y - prev_slope_2y10y, 2)} bps")
    col2.metric("2Y–5Y Spread", f"{slope_2y5y} bps",
                delta=f"{round(slope_2y5y - prev_slope_2y5y, 2)} bps")

    st.write("#### Spread Changes from Yesterday:")
    st.write(f"2Y–10Y: {get_bullish_signal(slope_2y10y - prev_slope_2y10y)}")
    st.write(f"2Y–5Y: {get_bullish_signal(slope_2y5y - prev_slope_2y5y)}")

# --- Section 3: Fed Funds & Inflation ---
with st.expander("🏦 Fed Funds & Real Interest Rate"):
    st.write("### Core Inputs")
    st.write(f"📌 Fed Funds Rate: `{real_rate['fed']}%`")
    st.write(f"📌 Breakeven Inflation: `{real_rate['inflation']}%`")
    st.write(f"📈 Real Interest Rate: `{real_rate['real']}%` → {real_rate['flow']}")

# --- Section 4: Implied Fed Expectations ---
with st.expander("🔮 Implied Fed Funds Rate from Futures"):
    st.write(f"Today: `{implied_rate['today']}%`")
    st.write(f"Yesterday: `{implied_rate['prev']}%`")
    st.write(f"Change: `{implied_rate['change']} bps`")
    st.write(f"Market Interpretation: **{implied_rate['signal']}**")

# --- Section 5: Futures Monitor ---
with st.expander("💱 Futures Prices (SPY, GLD, ZN, DX)", True):
    df_futures = pd.DataFrame(market_data).T
    df_futures.index.name = 'Asset'
    df_futures.reset_index(inplace=True)
    df_futures.rename(columns={'index': 'Asset'}, inplace=True)
    cols = st.columns(len(market_data))
    assets = list(market_data.keys())
    for i, ticker in enumerate(assets):
        cols[i].metric(ticker, f"{market_data[ticker]['price']}", delta=f"{market_data[ticker]['change']}")
        cols[i].write("*" + ("Bullish" if market_data[ticker]['signal'] == "Bullish" else "Bearish") + "*")

# --- Section 6: VIX Term Structure ---
with st.expander("📉 VIX Term Structure", False):
    if "error" not in vix_data:
        st.write(f"Spot VIX: {vix_data['spot']}")
        st.write(f"Front Month VIX Future: {vix_data['front']}")
        st.write(f"Next Month VIX Future: {vix_data['back']}")
        st.write(f"Curve Shape: **{vix_data['signal']}**")
    else:
        st.warning("Could not retrieve live VIX data.")

# --- Section 7: Institutional Money Flow Prediction ---
with st.expander("🧠 Institutional Money Flow Signal", True):
    st.markdown(f"#### Gold vs Bonds Today: `{gold_bond_signal}`")

# --- Section 8: Final Risk Mode Summary ---
with st.expander("🔥 Final Market Risk Sentiment", True):
    st.markdown(f"# **{risk_mode}**")
    st.write("Based on yield spreads, volatility term structure, and futures price movement")

# --- Footer ---
st.markdown("---")
st.markdown("Built using Python + Streamlit | Data sources: FRED, Yahoo Finance, CBOE")

# --- Helper Function ---
def get_bullish_signal(change):
    if change > 0:
        return "Bullish ↑"
    elif change < 0:
        return "Bearish ↓"
    else:
        return "Neutral →"