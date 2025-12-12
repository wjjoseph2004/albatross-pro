import streamlit as st
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Albatross Ultimate", page_icon="🦅", layout="wide")

# --- 1. SETUP ---
try:
    API_KEY = st.secrets["ODDS_API_KEY"]
except:
    st.error("API Key missing. Set it in Settings -> Secrets.")
    st.stop()

REGION = 'uk'
MARKET = 'h2h'
TOP_3_KEYS = ['soccer_epl', 'basketball_nba', 'tennis_atp']

# Initialize Session State for API Quota
if 'quota' not in st.session_state:
    st.session_state.quota = "Unknown"

# --- 2. ADVISOR SYSTEM ---
def get_sniper_advice():
    current_hour = datetime.utcnow().hour
    if 6 <= current_hour < 11:
        return "🌅 **Morning:** Target **Tennis (ATP)**. European matches starting."
    elif 11 <= current_hour < 17:
        return "☀️ **Afternoon:** Target **Premier League**. Check for team news."
    elif 17 <= current_hour < 22:
        return "🌆 **Evening:** Target **NBA / US Sports**. Market is waking up."
    else:
        return "🌙 **Night:** Target **NHL / NBA**. Late line moves."

# --- 3. DATA FETCHING (With Quota Tracking) ---
@st.cache_data(ttl=3600)
def get_active_sports():
    url = f'https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}'
    try:
        res = requests.get(url)
        # Update Quota
        if 'x-requests-remaining' in res.headers:
            st.session_state.quota = res.headers['x-requests-remaining']
        return {s['title']: s['key'] for s in res.json() if s['active']}
    except:
        return {}

# --- 4. ARBITRAGE ENGINE (Cached 15 mins) ---
@st.cache_data(ttl=900, show_spinner=False)
def get_arbs_cached(sport_key, investment, selected_bookies_tuple):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {'apiKey': API_KEY, 'regions': REGION, 'markets': MARKET, 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url, params=params)
        # Update Quota on fresh fetch
        if 'x-requests-remaining' in res.headers:
            st.session_state.quota = res.headers['x-requests-remaining']
        events = res.json()
    except:
        return []

    found_arbs = []
    for event in events:
        if 'bookmakers' not in event: continue
        teams = [event['home_team'], event['away_team']]
        best_odds = {}
        
        # Tuple to List for filtering
        selected_bookies_list = list(selected_bookies_tuple)
        valid_bookies = [b for b in event['bookmakers'] if b['title'] in selected_bookies_list]

        for bookie in valid_bookies:
            for market in bookie['markets']:
                if market['key'] == MARKET:
                    for outcome in market['outcomes']:
                        name = outcome['name']
                        price = outcome['price']
                        if name not in best_odds or price > best_odds[name]['price']:
                            best_odds[name] = {'price': price, 'bookie': bookie['title']}
        
        if len(best_odds) != 2: continue

        ip1 = 1 / best_odds[teams[0]]['price']
        ip2 = 1 / best_odds[teams[1]]['price']
        total_ip = ip1 + ip2
        
        if total_ip < 1.0: 
            roi = ((1 / total_ip) - 1) * 100
            stake1 = round(((investment * ip1) / total_ip) * 2) / 2
            stake2 = round(((investment * ip2) / total_ip) * 2) / 2
            profit_money = (stake1 * best_odds[teams[0]]['price']) - (stake1 + stake2)

            found_arbs.append({
                "match": f"{teams[0]} vs {teams[1]}",
                "profit": roi,
                "money": profit_money,
                "t1": teams[0], "b1": stake1, "o1": best_odds[teams[0]]['price'], "bk1": best_odds[teams[0]]['bookie'],
                "t2": teams[1], "b2": stake2, "o2": best_odds[teams[1]]['price'], "bk2": best_odds[teams[1]]['bookie']
            })
    return found_arbs

# --- 5. INTERFACE ---
st.title("🦅 Albatross Ultimate")

# ADVISOR
st.info(get_sniper_advice())

# SIDEBAR METRICS
st.sidebar.header("📊 Live Status")
st.sidebar.metric("API Credits Left", st.session_state.quota, help="Updates after every fresh scan.")
st.sidebar.markdown("---")

st.sidebar.header("⚙️ Settings")
all_uk_bookies = ["William Hill", "Bet365", "Betfair", "Unibet", "Betway", "Ladbrokes", "Coral", "Paddy Power", "Sky Bet", "888sport", "BetVictor", "BoyleSports"]
my_bookies = st.sidebar.multiselect("Bookmakers:", all_uk_bookies, default=["William Hill", "Bet365", "Unibet"])
bookies_tuple = tuple(sorted(my_bookies))
invest = st.sidebar.number_input("Bankroll (£)", value=100)

# EXTERNAL TOOLS (YOUR REQUEST)
st.write("🔍 **Pre-Scan Check:** Are games playing right now?")
col1, col2, col3 = st.columns([1,1,2])
with col1:
    st.link_button("⚽ Check FlashScore", "https://www.flashscore.co.uk")
with col2:
    st.link_button("📡 Check LiveScore", "https://www.livescore.com")

st.markdown("---")

# TABS
tab1, tab2 = st.tabs(["🎯 Manual Scope", "🚀 Fire Sniper (Top 3)"])

with tab1:
    sports = get_active_sports()
    if not sports:
        st.info("Fetching sports list...")
    else:
        choice = st.selectbox("Select Target", list(sports.keys()))
        if st.button("Scan Market"):
            with st.spinner(f"Scanning {choice}..."):
                results = get_arbs_cached(sports[choice], invest, bookies_tuple)
                if not results:
                    st.warning("No arbs found (Results cached 15 mins).")
                else:
                    st.success(f"Found {len(results)} opportunities!")
                    for a in results:
                        # PALPABLE ERROR CHECK
                        color = "#e8f5e9" # Green
                        border = "#c8e6c9"
                        warning_msg = ""
                        if a['profit'] > 20.0:
                            color = "#ffebee" # Red
                            border = "#ffcdd2"
                            warning_msg = "🚨 <b>HIGH RISK:</b> Profit > 20% might be a bookie error. Check carefully!"
                        
                        st.markdown(f"""
                        <div style="background-color:{color}; padding:15px; border-radius:10px; border:1px solid {border}; margin-bottom:10px;">
                            <h4 style="margin:0; color:#2e7d32;">Profit: £{a['money']:.2f} ({a['profit']:.2f}%)</h4>
                            <p style="color:#d32f2f; font-size:0.9em;">{warning_msg}</p>
                            <p><b>{a['match']}</b></p>
                            <hr style="margin:5px 0;">
                            <div style="display:flex; justify-content:space-between;">
                                <div><b>{a['t1']}</b><br>£{a['b1']} @ {a['o1']}<br><small>{a['bk1']}</small></div>
                                <div><b>{a['t2']}</b><br>£{a['b2']} @ {a['o2']}<br><small>{a['bk2']}</small></div>
                            </div>
                        </div>""", unsafe_allow_html=True)

with tab2:
    st.write("Scans **EPL**, **NBA**, and **Tennis**.")
    if st.button("🚀 SCAN TOP 3 NOW", type="primary"):
        all_results = []
        status = st.empty()
        for key in TOP_3_KEYS:
            status.text(f"Scanning {key}...")
            found = get_arbs_cached(key, invest, bookies_tuple)
            all_results.extend(found)
            time.sleep(0.1)
        status.empty()
        
        if not all_results:
            st.info("Sniper scan complete. No arbs found.")
        else:
            st.balloons()
            for a in all_results:
                # PALPABLE ERROR CHECK
                color = "#fff3e0" # Orange
                warning_msg = ""
                if a['profit'] > 20.0:
                    color = "#ffebee" # Red
                    warning_msg = "🚨 HIGH RISK (Possible Error)"

                st.markdown(f"""
                <div style="background-color:{color}; padding:10px; border-radius:5px; border:1px solid #ffe0b2; margin-bottom:10px;">
                    <h4 style="margin:0; color:#e65100;">Profit: £{a['money']:.2f}</h4>
                    <p style="color:red;">{warning_msg}</p>
                    <p>{a['match']}</p>
                    <hr>
                    <b>{a['t1']}</b>: £{a['b1']} @ {a['o1']} ({a['bk1']})<br>
                    <b>{a['t2']}</b>: £{a['b2']} @ {a['o2']} ({a['bk2']})
                </div>""", unsafe_allow_html=True)
