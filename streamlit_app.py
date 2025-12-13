import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# PAGE CONFIG
st.set_page_config(page_title="Albatross Diamond", page_icon="🦅", layout="wide")

# --- DARK MODE & STYLING (The New Look) ---
st.markdown("""
<style>
    /* Force Dark Theme Background */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    /* Make Input Boxes Dark & Sleek */
    .stTextInput > div > div > input { color: #FAFAFA; background-color: #262730; }
    .stSelectbox > div > div > div { color: #FAFAFA; background-color: #262730; }
    .stNumberInput > div > div > input { color: #FAFAFA; background-color: #262730; }
    
    /* Metrics (Credit Counter) */
    [data-testid="stMetricValue"] { color: #00FF00; font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP ---
API_KEY = "ccc71cee1188b0ff21fe42e9a7d174cd"
REGION = 'uk'
MARKET = 'h2h'

# --- TRANSLATOR ---
SPORT_LABELS = {
    "soccer_epl": "🇬🇧 Premier League",
    "soccer_uefa_champs_league": "🇪🇺 Champions League",
    "soccer_england_champ": "🇬🇧 Championship",
    "basketball_nba": "🇺🇸 NBA",
    "americanfootball_nfl": "🇺🇸 NFL",
    "icehockey_nhl": "🇺🇸 NHL",
    "baseball_mlb": "🇺🇸 MLB",
    "tennis_atp": "🎾 Tennis (ATP)",
    "tennis_wta": "🎾 Tennis (WTA)"
}
TOP_3_KEYS = ['soccer_epl', 'basketball_nba', 'tennis_atp']

# SESSION STATE
if 'quota' not in st.session_state:
    st.session_state.quota = "Checking..."
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=["Date","Match","Profit","Bookie 1","Bookie 2"])

# --- 2. ADVISOR ---
def get_sniper_advice():
    h = datetime.utcnow().hour
    if 6 <= h < 11: return "🌅 Morning: Target Tennis."
    elif 11 <= h < 17: return "☀️ Afternoon: Target Premier League."
    elif 17 <= h < 22: return "🌆 Evening: Target NBA."
    else: return "🌙 Night: Target NHL / NBA."



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
            if s['key'] in SPORT_LABELS: name = SPORT_LABELS[s['key']]
            else: name = s['title']
            active_sports[name] = s['key']
        return active_sports
    except: return {}

# --- 4. ENGINE ---
def get_arbs_engine(sport_key, investment, selected_bookies_tuple, ghost_mode, test_mode):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {'apiKey':API_KEY, 'regions':REGION, 'markets':MARKET, 'oddsFormat':'decimal'}
    try:
        res = requests.get(url, params=params)
        if 'x-requests-remaining' in res.headers:
            st.session_state.quota = res.headers['x-requests-remaining']
        events = res.json()
    except: return []

    results = []
    for event in events:
        if 'bookmakers' not in event: continue
        try:
            start_dt = datetime.strptime(event['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
            start_str = start_dt.strftime("%H:%M")
        except: start_str = "Soon"
            
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
                stake1 = round(raw_stake1); stake2 = round(raw_stake2)
            else:
                stake1 = round(raw_stake1 * 2) / 2; stake2 = round(raw_stake2 * 2) / 2
            
            ret1 = stake1 * best_odds[teams[0]]['price']
            ret2 = stake2 * best_odds[teams[1]]['price']
            profit_money = min(ret1, ret2) - (stake1 + stake2)

            results.append({
                "match": f"{teams[0]} vs {teams[1]}", "start": start_str,
                "profit_pct": roi, "profit_money": profit_money,
                "t1": teams[0], "b1": stake1, "o1": best_odds[teams[0]]['price'], "bk1": best_odds[teams[0]]['bookie'],
                "t2": teams[1], "b2": stake2, "o2": best_odds[teams[1]]['price'], "bk2": best_odds[teams[1]]['bookie']
            })
    return results
