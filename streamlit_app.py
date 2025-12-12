import streamlit as st

import requests

import time

from datetime import datetime



st.set_page_config(page_title="Albatross Sniper", page_icon="🦅", layout="wide")



# --- 1. KEYS & SETUP ---

try:

    API_KEY = st.secrets["ODDS_API_KEY"]

except:

    st.error("API Key missing. Please set it in Settings -> Secrets.")

    st.stop()



REGION = 'uk'

MARKET = 'h2h'



# Define our "Sniper Targets" (The Top 3)

TOP_3_KEYS = ['soccer_epl', 'basketball_nba', 'tennis_atp']



# --- 2. TIME-BASED ADVISOR ---

def get_sniper_advice():

    # Get current hour (approx UK time based on server UTC)

    current_hour = datetime.utcnow().hour

    

    if 6 <= current_hour < 11:

        return "🌅 **Morning Session:** Best Target: **Tennis (ATP/WTA)**. Asian matches finishing, European starting."

    elif 11 <= current_hour < 17:

        return "☀️ **Lunch/Afternoon:** Best Target: **Premier League (EPL)**. Team news often breaks now."

    elif 17 <= current_hour < 22:

        return "🌆 **Evening Session:** Best Target: **NBA Basketball**. US Bookies are waking up."

    elif 22 <= current_hour or current_hour < 6:

        return "🌙 **Night Owl:** Best Target: **NHL / NBA**. Late US line movements."

    else:

        return "🎯 **General:** Scan your favorites."



# --- 3. FETCH DATA ---

@st.cache_data(ttl=3600)

def get_active_sports():

    url = f'https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}'

    try:

        res = requests.get(url)

        data = res.json()

        return {s['title']: s['key'] for s in data if s['active']}

    except:

        return {}



# --- 4. ARBITRAGE ENGINE ---

def get_arbs(sport_key, investment, selected_bookies):

    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'

    params = {'apiKey': API_KEY, 'regions': REGION, 'markets': MARKET, 'oddsFormat': 'decimal'}

    

    try:

        res = requests.get(url, params=params)

        events = res.json()

    except:

        return []



    found_arbs = []

    for event in events:

        if 'bookmakers' not in event: continue

        

        teams = [event['home_team'], event['away_team']]

        best_odds = {}

        

        # Filter Bookies

        valid_bookies = [b for b in event['bookmakers'] if b['title'] in selected_bookies]



        for bookie in valid_bookies:

            for market in bookie['markets']:

                if market['key'] == MARKET:

                    for outcome in market['outcomes']:

                        name = outcome['name']

                        price = outcome['price']

                        if name not in best_odds or price > best_odds[name]['price']:

                            best_odds[name] = {'price': price, 'bookie': bookie['title']}

        

        if len(best_odds) != 2: continue



        # MATH

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



# --- 5. THE INTERFACE ---

st.title("🦅 Albatross Sniper")



# THE ADVISOR BOX

st.info(get_sniper_advice())



# SIDEBAR

st.sidebar.header("⚙️ Configuration")

all_uk_bookies = ["William Hill", "Bet365", "Betfair", "Unibet", "Betway", "Ladbrokes", "Coral", "Paddy Power", "Sky Bet", "888sport", "BetVictor", "BoyleSports"]

my_bookies = st.sidebar.multiselect("Active Accounts:", all_uk_bookies, default=["William Hill", "Bet365", "Unibet"])

st.sidebar.markdown("---")

invest = st.sidebar.number_input("Bankroll (£)", value=100)



# TABS

tab1, tab2 = st.tabs(["🎯 Manual Scope", "🚀 Fire Sniper (Top 3)"])



# TAB 1: MANUAL

with tab1:

    sports = get_active_sports()

    if not sports:

        st.info("Loading sports list...")

    else:

        choice = st.selectbox("Select Target Sport", list(sports.keys()))

        if st.button("Scan Market"):

            with st.spinner(f"Scanning {choice}..."):

                results = get_arbs(sports[choice], invest, my_bookies)

                if not results:

                    st.warning("No arbs found in this market.")

                else:

                    st.success(f"Found {len(results)} opportunities!")

                    for a in results:

                        st.markdown(f"""

                        <div style="background-color:#e8f5e9; padding:10px; border-radius:5px; border:1px solid #c8e6c9; margin-bottom:10px;">

                            <h4 style="margin:0; color:#2e7d32;">Profit: £{a['money']:.2f}</h4>

                            <p style="font-size:0.9em;">{a['match']}</p>

                            <hr style="margin:5px 0;">

                            <b>{a['t1']}</b>: £{a['b1']} @ {a['o1']} ({a['bk1']})<br>

                            <b>{a['t2']}</b>: £{a['b2']} @ {a['o2']} ({a['bk2']})

                        </div>

                        """, unsafe_allow_html=True)



# TAB 2: AUTO SNIPER

with tab2:

    st.write("Scans **EPL**, **NBA**, and **Tennis** simultaneously.")

    st.caption("⚠️ Uses 3 API credits per click.")

    

    if st.button("🚀 SCAN TOP 3 NOW", type="primary"):

        all_results = []

        status = st.empty()

        

        for key in TOP_3_KEYS:

            status.text(f"Scanning {key}...")

            found = get_arbs(key, invest, my_bookies)

            all_results.extend(found)

            time.sleep(0.2)

            

        status.empty()

        

        if not all_results:

            st.info("Sniper scan complete. No arbs found.")

        else:

            st.balloons()

            st.success(f"Sniper Hit! Found {len(all_results)} opportunities.")

            for a in all_results:

                st.markdown(f"""

                <div style="background-color:#fff3e0; padding:10px; border-radius:5px; border:1px solid #ffe0b2; margin-bottom:10px;">

                    <h4 style="margin:0; color:#e65100;">Profit: £{a['money']:.2f}</h4>

                    <p style="font-size:0.9em;">{a['match']}</p>

                    <hr style="margin:5px 0;">

                    <b>{a['t1']}</b>: £{a['b1']} @ {a['o1']} ({a['bk1']})<br>

                    <b>{a['t2']}</b>: £{a['b2']} @ {a['o2']} ({a['bk2']})

                </div>

                """, unsafe_allow_html=True)

