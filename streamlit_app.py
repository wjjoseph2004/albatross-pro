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

# --- TRANSLATOR (Readable Names) ---
# We use these for the big sports. Everything else will just use its normal name.
SPORT_LABELS = {
    "soccer_epl": "🇬🇧 Premier League",
    "soccer_uefa_champs_league": "🇪🇺 Champions League",
    "soccer_england_champ": "🇬🇧 Championship",
    "soccer_fa_cup": "🇬🇧 FA Cup",
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_italy_serie_a": "🇮🇹 Serie A",
    "soccer_france_ligue_one": "🇫🇷 Ligue 1",
    "basketball_nba": "🇺🇸 NBA",
    "americanfootball_nfl": "🇺🇸 NFL",
    "icehockey_nhl": "🇺🇸 NHL",
    "baseball_mlb": "🇺🇸 MLB",
    "tennis_atp": "🎾 Tennis (ATP)",
    "tennis_wta": "🎾 Tennis (WTA)",
    "cricket_test_match": "🏏 Cricket (Test)",
    "rugby_union_premiership_rugby": "🏉 Rugby Premiership",
    "mma_mixed_martial_arts": "🥊 MMA / UFC"
}

TOP_3_KEYS = ['soccer_epl', 'basketball_nba', 'tennis_atp']

# Session State
if 'quota' not in st.session_state: st.session_state.quota = "Unknown"
if 'ledger' not in st.session_state: 
    st.session_state.ledger = pd.DataFrame(columns=["Date", "Match", "Profit (£)", "Bookie 1", "Bookie 2"])

# --- 2. ADVISOR ---
def get_sniper_advice():
    h = datetime.utcnow().hour
    if 6 <= h < 11: 
        return "🌅 **Morning:** Target **🎾 Tennis (ATP)**. European matches starting."
    elif 11 <= h < 17: 
        return "☀️ **Afternoon:** Target **🇬🇧 Premier League**. Check team news."
    elif 17 <= h < 22: 
        return "🌆 **Evening:** Target **🇺🇸 NBA**. US market waking up."
    else: 
        return "🌙 **Night:** Target **🇺🇸 NHL / NBA**. Late moves."

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_active_sports():
    url = f'https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}'
    try:
        res = requests.get(url)
        if 'x-requests-remaining' in res.headers: st.session_state.quota = res.headers['x-requests-remaining']
        
        active_sports = {}
        for s in res.json():
            if not s['active']: continue
            
            # HYBRID LOGIC: Use fancy name if we have it, otherwise use default title
            if s['key'] in SPORT_LABELS:
                display_name = SPORT_LABELS[s['key']]
            else:
                display_name = s['title']
            
            active_sports[display_name] = s['key']
            
        return active_sports
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
    if not sports: st.info("Fetching sports list (or none active)...")
    else:
        # Sort keys
        sorted_names = sorted(list(sports.keys()))
        choice_name = st.selectbox("Select Target Sport", sorted_names)
        choice_key = sports[choice_name]

        if st.button("Scan Market"):
            with st.spinner(f"Scanning {choice_name}..."):
                res = get_arbs_cached(choice_key, invest, bookies_tuple, ghost_mode)
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
