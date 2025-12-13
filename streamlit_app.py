import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Albatross Diamond", page_icon="🦅", layout="wide")

# --- 1. SETUP (YOUR PRIVATE KEY) ---
# This is YOUR personal key. Do not share this file with anyone.
API_KEY = "ccc71cee1188b0ff21fe42e9a7d174cd"

REGION = 'uk'
MARKET = 'h2h'

# --- TRANSLATOR (Readable Names) ---
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
        if 'x-requests-remaining' in res.headers: st.session_state.quota = res.headers['x-requests-remaining']
        
        active_sports = {}
        for s in res.json():
            if not s['active']: continue
            # Hybrid Name Logic
            if s['key'] in SPORT_LABELS: display_name = SPORT_LABELS[s['key']]
            else: display_name = s['title']
            active_sports[display_name] = s['key']
        return active_sports
    except:
        return {}

# --- 4. ENGINE (With Test Mode Logic) ---
def get_arbs_engine(sport_key, investment, selected_bookies_tuple, ghost_mode, test_mode):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {'apiKey': API_KEY, 'regions': REGION, 'markets': MARKET, 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url, params=params)
        if 'x-requests-remaining' in res.headers: st.session_state.quota = res.headers['x-requests-remaining']
        events = res.json()
    except:
        return []

    results = []
    
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
