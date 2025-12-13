import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Albatross Diamond", page_icon="🦅", layout="wide")

# --- 1. SETUP ---
try:
    API_KEY = st.secrets["ODDS_API_KEY"]
except:
    st.error("API Key missing. Set it in Settings -> Secrets.")
    st.stop()

REGION = 'uk'
MARKET = 'h2h'
TOP_3_KEYS = ['soccer_epl', 'basketball_nba', 'tennis_atp']

# Initialize Session State
if 'quota' not in st.session_state: st.session_state.quota = "Unknown"
if 'ledger' not in st.session_state: 
    st.session_state.ledger = pd.DataFrame(columns=["Date", "Match", "Profit (£)", "Bookie 1", "Bookie 2"])

# --- 2. ADVISOR ---
def get_sniper_advice():
    h = datetime.utcnow().hour
    if 6 <= h < 11: return "🌅 **Morning:** Target **Tennis**. European matches starting."
    elif 11 <= h < 17: return "☀️ **Afternoon:** Target **EPL**. Check team news."
    elif 17 <= h < 22: return "🌆 **Evening:** Target **NBA**. US market waking up."
    else: return "🌙 **Night:** Target **NHL/NBA**. Late moves."

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_active_sports():
    url = f'https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}'
    try:
        res = requests.get(url)
        if 'x-requests-remaining' in res.headers: st.session_state.quota = res.headers['x-requests-remaining']
        return {s['title']: s['key'] for s in res.json() if s['active']}
    except:
        return {}

# --- 4. ENGINE (Cached 15m) ---
@st.cache_data(ttl=900, show_spinner=False)
def get_arbs_cached(sport_key, investment, selected_bookies_tuple, ghost_mode):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {'apiKey': API_KEY, 'regions': REGION, 'markets': MARKET, 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url, params=params)
        if 'x-requests-remaining' in res.headers: st.session_state.quota = res.headers['x-requests-remaining']
        events = res.json()
    except:
        return []

    found_arbs = []
    for event in events:
        if 'bookmakers' not in event: continue
        teams = [event['home_team'], event['away_team']]
        best_odds = {}
        
        bookies_list = list(selected_bookies_tuple)
        valid_bookies = [b for b in event['bookmakers'] if b['title'] in bookies_list]

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
            raw_stake1 = (investment * ip1) / total_ip
            raw_stake2 = (investment * ip2) / total_ip
            
            if ghost_mode:
                stake1 = round(raw_stake1)
                stake2 = round(raw_stake2)
            else:
                stake1 = round(raw_stake1 * 2) / 2
                stake2 = round(raw_stake2 * 2) / 2
            
            ret1 = stake1 * best_odds[teams[0]]['price']
            ret2 = stake2 * best_odds[teams[1]]['price']
            profit_money = min(ret1, ret2) - (stake1 + stake2)

            found_arbs.append({
                "match": f"{teams[0]} vs {teams[1]}",
                "profit_pct": roi,
                "profit_money": profit_money,
                "t1": teams[0], "b1": stake1, "o1": best_odds[teams[0]]['price'], "bk1": best_odds[teams[0]]['bookie'],
                "t2": teams[1], "b2": stake2, "o2": best_odds[teams[1]]['price'], "bk2": best_odds[teams[1]]['bookie']
            })
    return found_arbs

# --- 5. INTERFACE ---
st.title("🦅 Albatross Diamond")
st.info(get_sniper_advice())

# SIDEBAR
st.sidebar.header("📊 Live Status")
st.sidebar.metric("API Credits", st.session_state.quota)
st.sidebar.markdown("---")

st.sidebar.header("⚙️ Settings")
all_uk_bookies = ["William Hill", "Bet365", "Betfair", "Unibet", "Betway", "Ladbrokes", "Coral", "Paddy Power", "Sky Bet", "888sport", "BetVictor", "BoyleSports"]
my_bookies = st.sidebar.multiselect("Bookmakers:", all_uk_bookies, default=["William Hill", "Bet365", "Unibet"])
bookies_tuple = tuple(sorted(my_bookies))
invest = st.sidebar.number_input("Bankroll (£)", value=100)

st.sidebar.subheader("🛡️ Safety & Filters")
min_profit = st.sidebar.slider("Min Profit (£)", 0.0, 10.0, 0.50)
ghost_mode = st.sidebar.checkbox("👻 Ghost Mode", value=False)

# RESTORED: PRE-SCAN TOOLS
st.write("🔍 **Pre-Scan Tools (Check before you click!):**")
c1, c2 = st.columns([1,1])
c1.link_button("⚽ Check FlashScore", "https://www.flashscore.co.uk")
c2.link_button("📡 Check LiveScore", "https://www.livescore.com")
st.markdown("---")

# TABS
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Manual Scope", "🚀 Fire Sniper", "📒 My Ledger", "📘 Help Guide"])

def display_arbs(results):
    count = 0
    for a in results:
        if a['profit_money'] < min_profit: continue
        count += 1
        
        color = "#e8f5e9"
        border = "#c8e6c9"
        warn = ""
        if a['profit_pct'] > 20.0:
            color = "#ffebee"
            warn = "🚨 <b>HIGH RISK:</b> >20% Profit. Possible Error."
        
        # RESTORED: GOOGLE SEARCH LINKS
        search_q1 = f"{a['bk1']} {a['t1']} vs {a['t2']} odds"
        search_q2 = f"{a['bk2']} {a['t1']} vs {a['t2']} odds"
        link1 = f"https://www.google.com/search?q={search_q1.replace(' ', '+')}"
        link2 = f"https://www.google.com/search?q={search_q2.replace(' ', '+')}"

        st.markdown(f"""
        <div style="background-color:{color}; padding:15px; border-radius:10px; border:1px solid {border}; margin-bottom:10px;">
            <h4 style="margin:0; color:#2e7d32;">Profit: £{a['profit_money']:.2f} ({a['profit_pct']:.2f}%)</h4>
            <p style="color:#d32f2f; font-size:0.9em;">{warn}</p>
            <p><b>{a['match']}</b></p>
            <hr style="margin:5px 0;">
            <div style="display:flex; justify-content:space-between;">
                <div style="width:48%">
                    <b>{a['t1']}</b><br>
                    <span style="font-size:1.1em; color:blue;">£{a['b1']:.2f}</span> @ {a['o1']}<br>
                    <small>{a['bk1']}</small><br>
                    <a href="{link1}" target="_blank" style="text-decoration:none; font-size:0.8em;">🔎 Find on Google</a>
                </div>
                <div style="width:48%">
                    <b>{a['t2']}</b><br>
                    <span style="font-size:1.1em; color:blue;">£{a['b2']:.2f}</span> @ {a['o2']}<br>
                    <small>{a['bk2']}</small><br>
                    <a href="{link2}" target="_blank" style="text-decoration:none; font-size:0.8em;">🔎 Find on Google</a>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
    
    if count == 0: st.warning(f"No arbs found above £{min_profit:.2f} profit.")
    else: st.success(f"Showing {count} opportunities.")

with tab1:
    sports = get_active_sports()
    if not sports: st.info("Fetching sports...")
    else:
        choice = st.selectbox("Target Sport", list(sports.keys()))
        if st.button("Scan Market"):
            with st.spinner(f"Scanning {choice}..."):
                res = get_arbs_cached(sports[choice], invest, bookies_tuple, ghost_mode)
                if not res: st.warning("No data found.")
                else: display_arbs(res)

with tab2:
    st.write("Scans **EPL, NBA, Tennis**.")
    if st.button("🚀 SCAN TOP 3", type="primary"):
        all_res = []
        stat = st.empty()
        for k in TOP_3_KEYS:
            stat.text(f"Scanning {k}...")
            found = get_arbs_cached(k, invest, bookies_tuple, ghost_mode)
            all_res.extend(found)
            time.sleep(0.1)
        stat.empty()
        if not all_res: st.info("No arbs found.")
        else: 
            st.balloons()
            display_arbs(all_res)

with tab3:
    st.write("### 📒 My Profit Tracker")
    with st.form("add_bet"):
        c1, c2, c3 = st.columns(3)
        date = c1.date_input("Date")
        match = c2.text_input("Match")
        profit = c3.number_input("Profit (£)", min_value=0.0, step=0.1)
        bk1 = c1.selectbox("Bookie 1", all_uk_bookies)
        bk2 = c2.selectbox("Bookie 2", all_uk_bookies)
        if st.form_submit_button("💾 Log Win"):
            new_row = {"Date": date, "Match": match, "Profit (£)": profit, "Bookie 1": bk1, "Bookie 2": bk2}
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_row])], ignore_index=True)
            st.success("Win Logged!")
            
    if not st.session_state.ledger.empty:
        st.write("### 📈 Your Growth")
        st.line_chart(st.session_state.ledger.set_index("Date")["Profit (£)"].cumsum())
        
        # EXPORT BUTTON
        csv = st.session_state.ledger.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name="albatross_ledger.csv", mime="text/csv")
        
        st.dataframe(st.session_state.ledger)
    else:
        st.info("No wins logged yet.")

with tab4:
    st.write("## 📘 How to Use Albatross")
    st.markdown("""
    ### 1. The Golden Rule 🛑
    * **Never bet on Red Cards:** If you see a card with a RED background (Profit > 20%), it is likely a bookie error. If you bet on it, your account might be restricted. **Stick to Green/White cards.**
    
    ### 2. How to "Snipe" 🔫
    * **Morning (8-10am):** Scan `Tennis`.
    * **Afternoon (1-2pm):** Scan `Soccer (EPL)`.
    * **Evening (6-10pm):** Scan `NBA / US Sports`.
    * **Tip:** Use the **Blue Advisor Box** at the top of the screen; it tells you the best current target.
    
    ### 3. What is "Ghost Mode"? 👻
    * **OFF:** The app tells you to bet `£42.50`. This maximizes profit but looks mathematical.
    * **ON:** The app rounds the bet to `£43.00`. You lose a few pennies of profit, but you look like a "normal" gambler. **Recommended for new accounts.**
    
    ### 4. Saving Credits 💳
    * You have 500 scans per month.
    * The app has a **15-minute memory**. If you scan the Premier League twice in 10 minutes, the second scan is **FREE**.
    """)
