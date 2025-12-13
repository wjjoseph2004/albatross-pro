import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Albatross Diamond", page_icon="🦅", layout="wide")

# --- 1. SETUP (YOUR PRIVATE KEY) ---
API_KEY = "ccc71cee1188b0ff21fe42e9a7d174cd"
REGION = 'uk'
MARKET = 'h2h'

# --- TRANSLATOR ---
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
if 'quota' not in st.session_state:
    st.session_state.quota = "Unknown"
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=["Date", "Match", "Profit (£)", "Bookie 1", "Bookie 2"])

# --- 2. ADVISOR ---
def get_sniper_advice():
    h = datetime.utcnow().hour
    if 6 <= h < 11: return "🌅 **Morning:** Target **🎾 Tennis (ATP)**."
    elif 11 <= h < 17: return "☀️ **Afternoon:** Target **🇬🇧 Premier League**."
    elif 17 <= h < 22: return "🌆 **Evening:** Target **🇺🇸 NBA**."
    else: return "🌙 **Night:** Target **🇺🇸 NHL / NBA**."

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_active_sports():
    url = f'https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}'
    try:
        res = requests.get(url)
        if 'x-requests-remaining' in res.headers:
            st.session_state.quota = res.headers['x-requests-remaining']
        
        active_sports = {}
        for s in res.json():
            if not s['active']: continue
            if s['key'] in SPORT_LABELS:
                name = SPORT_LABELS[s['key']]
            else:
                name = s['title']
            active_sports[name] = s['key']
        return active_sports
    except:
        return {}

# --- 4. ENGINE ---
def get_arbs_engine(sport_key, investment, selected_bookies_tuple, ghost_mode, test_mode):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {'apiKey': API_KEY, 'regions': REGION, 'markets': MARKET, 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url, params=params)
        if 'x-requests-remaining' in res.headers:
            st.session_state.quota = res.headers['x-requests-remaining']
        events = res.json()
    except:
        return []

    results = []
    
    for event in events:
        if 'bookmakers' not in event: continue
        
        try:
            start_dt = datetime.strptime(event['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
            start_str = start_dt.strftime("%H:%M")
        except:
            start_str = "Soon"
            
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
        
        if total_ip < 1.0 or test_mode: 
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

            results.append({
                "match": f"{teams[0]} vs {teams[1]}",
                "start": start_str,
                "profit_pct": roi,
                "profit_money": profit_money,
                "t1": teams[0], "b1": stake1, "o1": best_odds[teams[0]]['price'], "bk1": best_odds[teams[0]]['bookie'],
                "t2": teams[1], "b2": stake2, "o2": best_odds[teams[1]]['price'], "bk2": best_odds[teams[1]]['bookie']
            })
            
    return results

# --- 5. INTERFACE ---
st.title("🦅 Albatross Diamond")
st.info(get_sniper_advice())

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

st.write("🔍 **Pre-Scan Tools:**")
c1, c2 = st.columns([1,1])
c1.link_button("⚽ FlashScore", "https://www.flashscore.co.uk")
c2.link_button("📡 LiveScore", "https://www.livescore.com")
st.markdown("---")

test_mode = st.checkbox("🛠️ **Test Mode** (Show All Odds)", value=True)

tab1, tab2, tab3, tab4 = st.tabs(["🎯 Scanner", "🚀 Top 3", "📒 Ledger", "📘 Help"])

def display_arbs(results):
    count = 0
    sorted_results = sorted(results, key=lambda x: x['profit_pct'], reverse=True)
    
    for a in sorted_results:
        if not test_mode and a['profit_money'] < min_profit: continue
        count += 1
        
        if a['profit_pct'] > 0:
            color = "#e8f5e9"
            border = "#c8e6c9"
            title_color = "#2e7d32"
            status = "WIN"
        else:
            color = "#f5f5f5"
            border = "#ddd"
            title_color = "#666"
            status = "NO ARB"

        if a['profit_pct'] > 20.0:
            color = "#ffebee"
            status = "⚠️ ERROR?"
        
        q1 = f"{a['bk1']} {a['t1']} vs {a['t2']} odds"
        q2 = f"{a['bk2']} {a['t1']} vs {a['t2']} odds"
        l1 = f"https://www.google.com/search?q={q1.replace(' ', '+')}"
        l2 = f"https://www.google.com/search?q={q2.replace(' ', '+')}"

        st.markdown(f"""
        <div style="background-color:{color}; padding:15px; border-radius:10px; border:1px solid {border}; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; color:{title_color};">{status}: £{a['profit_money']:.2f} ({a['profit_pct']:.2f}%)</h4>
                <span style="background-color:#fff; padding:2px 8px; border-radius:5px; font-size:0.8em;">🕒 {a['start']}</span>
            </div>
            <p><b>{a['match']}</b></p>
            <hr style="margin:5px 0;">
            <div style="display:flex; justify-content:space-between; font-size:0.9em;">
                <div style="width:48%">
                    <b>{a['t1
