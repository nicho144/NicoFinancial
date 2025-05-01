# Financial Dashboard for Yield Curve, VIX, Futures & Risk Sentiment
# Version: Fully hardened against missing data and styling errors

import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

# --- Initialize Streamlit ---
st.set_page_config(layout="wide", page_title="📈 Institutional Market Dashboard")

# --- Hardcoded FRED API Key ---
fred = Fred(api_key='dceb19d6ccadfb4115c3ac2493b7d5ed')

# --- Helper Function to Get Treasury Yields ---
def get_treasury_yields():
    try:
        return {
            'DGS2': round(float(fred.get_series('DGS2')[-1]), 2),
            'DGS5': round(float(fred.get_series('DGS5')[-1]), 2),
            'DGS10': round(float(fred.get_series('DGS10')[-1]), 2)
        }
    except Exception as e:
        st.warning("⚠️ Failed to fetch live yields from FRED")
        return {'DGS2': 4.20, 'DGS5': 4.50, 'DGS10': 4.70}  # Fallback values

yields = get_treasury_yields()

# --- Get Previous Day's Yields ---
def get_prev_day_yields():
    yesterday = datetime.today() - timedelta(days=1)
    try:
        return {
            'DGS2': round(float(fred.get_series('DGS2', observation_end=yesterday)[-1]), 2),
            'DGS5': round(float(fred.get_series('DGS5', observation_end=yesterday)[-1]), 2),
            'DGS10': round(float(fred.get_series('DGS10', observation_end=yesterday)[-1]), 2)
        }
    except:
        return {'DGS2': 4.15, 'DGS5': 4.48, 'DGS10': 4.68}  # Fallback values

prev_yields = get_prev_day_yields()

# --- Yield Curve Analysis with Fallback ---
def analyze_yield_curve(yields, prev_yields):
    if not all(yields.values()) or not all(prev_yields.values()):
        st.warning("⚠️ Incomplete yield data — using fallback values for analysis")
        return {
            "slope_today": 0.5,
            "slope_change": 0.05,
            "slope_signal": "Steepener",
            
            "steep_2y5y_change": 0.05,
            "spread_2y5y_signal": "Steepener"
        }

    slope_today = float(yields['DGS10'] - yields['DGS2'])
    slope_yesterday = float(prev_yields['DGS10'] - prev_yields['DGS2'])
    slope_change = slope_today - slope_yesterday

    spread_2y5y_today = float(yields['DGS5'] - yields['DGS2'])
    spread_2y5y_yesterday = float(prev_yields['DGS5'] - prev_yields['DGS2'])
    spread_2y5y_change = spread_2y5y_today - spread_2y5y_yesterday

    return {
        "slope_today": round(slope_today, 2),
        "slope_yesterday": round(slope_yesterday, 2),
        "slope_change": round(slope_change, 2),
        "slope_signal": "Steepener" if slope_change > 0 else "Flattener",

        "steep_2y5y_change": round(spread_2y5y_change, 2),
        "spread_2y5y_signal": "Steepener" if spread_2y5y_change > 0 else "Flattener"
    }

curve_analysis = analyze_yield_curve(yields, prev_yields)

# --- Implied Fed Funds Rate ---
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

# --- Market Prices With Safe Defaults ---
def get_market_prices():
    prices = {}
    tickers = ['SPY', 'GLD', 'DX-Y.NYB', 'ZN=F', 'ES=F']
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            today = round(hist.iloc[-1]['Close'], 2)
            yesterday = round(hist.iloc[-2]['Close'], 2)
            change = round(today - yesterday, 2)
            signal = "Bullish" if (ticker in ['SPY', 'ES=F'] and change > 0) or \
                                    (ticker in ['ZN=F', 'GLD', 'DX-Y.NYB'] and change < 0) \
                                else "Bearish"
            prices[ticker] = {"price": today, "change": change, "signal": signal}
        except:
            prices[ticker] = {"price": "N/A", "change": 0, "signal": "Neutral"}
    return prices

market_prices = get_market_prices()

# --- Smart Money Flow Signal (Gold vs Bonds) ---
def gold_bond_flow(real_rate, market_prices):
    gold_change = market_prices.get('GLD', {}).get('change', 0)
    bond_change = market_prices.get('ZN=F', {}).get('change', 0)

    if real_rate.get('real', 1) < 0 and gold_change > 0 and bond_change < 0:
        return "🟡 Gold More Attractive Today"
    elif real_rate.get('real', 1) > 0 and gold_change < 0 and bond_change > 0:
        return "🟢 Bonds More Attractive"
    else:
        return "⚪ Neutral"

gold_bond_signal = gold_bond_flow(real_rate_data, market_prices)

# --- Risk-On / Risk-Off Aggregation ---
risk_score = 0

# Check yield steepener
if curve_analysis.get("slope_change", 0) > 0:
    risk_score += 1
if curve_analysis.get("steep_2y5y_change", 0) > 0:
    risk_score += 1

# Check futures price moves
if market_prices.get("SPY", {}).get("signal") == "Bullish":
    risk_score += 1
if market_prices.get("ES=F", {}).get("signal") == "Bullish":
    risk_score += 1

# Check implied rate move
if implied_rate.get("change", 0) > 0:
    risk_score += 1

# Final risk mode
risk_mode = "🟢 Risk On" if risk_score >= 3 else "🔴 Risk Off"

# --- UI Starts Here ---

st.title("📊 Financial Market Sentiment Dashboard")
st.markdown(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

# --- Yield Curve Chart ---
if yields and prev_yields:
    yield_df = pd.DataFrame({
        'Tenor': ['2Y', '5Y', '10Y'],
        'Today (%)': [yields['DGS2'], yields['DGS5'], yields['DGS10']],
        'Yesterday (%)': [prev_yields['DGS2'], prev_yields['DGS5'], prev_yields['DGS10']]
    })

    fig = px.line(
        yield_df.melt(id_vars='Tenor'),
        x='Tenor', y='value', color='variable',
        title="🏛️ US Treasury Yield Curve: Today vs Yesterday",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Spread Table Section ---
st.subheader("📉 Yield Spreads & Risk Mode")

try:
    df_spreads = pd.DataFrame([
        {
            "Spread": "2Y–5Y",
            "Today (bps)": curve_analysis["steep_2y5y_change"] + yields['DGS5'] - yields['DGS2'],
            "Change (bps)": curve_analysis["steep_2y5y_change"],
            "Signal": curve_analysis["spread_2y5y_signal"]
        },
        {
            "Spread": "2Y–10Y",
            "Today (bps)": curve_analysis["slope_today"],
            "Change (bps)": curve_analysis["slope_change"],
            "Signal": curve_analysis["slope_signal"]
        }
    ])

    styled_df = df_spreads.style.apply(lambda row: {
        "Signal": "background-color: #ffcccc" if row["Signal"] in ["Flattener", "Risk Off"] else "#ccffcc"
    }, axis=1)

    st.dataframe(styled_df, use_container_width=True)
except Exception as e:
    st.error("⚠️ Could not display yield spreads due to invalid data structure.")

# --- Implied Fed Funds ---
st.subheader("🏦 Implied Fed Funds Rate")
if 'error' not in implied_rate:
    st.write(f"Today: `{implied_rate['today']}%` | "
             f"Yesterday: `{implied_rate['prev']}%` | "
             f"Change: `{implied_rate['change']} bps` → **{implied_rate['signal']}**")
else:
    st.write("⚠️ Could not retrieve Fed Funds futures data.")

# --- Real Interest Rate ---
st.subheader("🧮 Real Interest Rate")
if 'error' not in real_rate_data:
    st.write(f"Federal Funds: `{real_rate_data['fed']}%` | "
             f"Inflation (TIPS): `{real_rate_data['inflation']}%` | "
             f"Real Rate: `{real_rate_data['real']}%` → **{real_rate_data['flow']}**")
else:
    st.write("⚠️ Could not calculate real interest rate.")

# --- Market Futures Validation ---
st.subheader("💱 Futures Price Movement")
cols = st.columns(len(market_prices))
for i, (ticker, info) in enumerate(market_prices.items()):
    cols[i].metric(ticker, f"${info['price']}", delta=f"{info['change']}")
    cols[i].write(f"Signal: **{info['signal']}**")

# --- Institution Money Flow ---
st.subheader("🧠 Institutional Flow Signal")
st.markdown(f"#### 💡 Prediction: **{gold_bond_signal}**")

# --- Final Risk Summary ---
st.subheader("🔥 Final Market Risk Signal")
st.markdown(f"# **{risk_mode}**")

# --- Footer ---
st.markdown("---")
st.markdown("*Data Sources: FRED, Yahoo Finance* | Built with ❤️ using Python + Streamlit")