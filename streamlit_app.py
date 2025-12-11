import streamlit as st
import requests

st.set_page_config(page_title="Albatross Pro", page_icon="🦅", layout="wide")

# --- 1. SETUP & KEYS ---
try:
    API_KEY = st.secrets["ODDS_API_KEY"]
except:
    st.error("API Key missing. Please set it in Streamlit Secrets.")
    st.stop()

REGION = 'uk'
MARKET = 'h2h'

# --- 2. FETCH DATA FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_active_sports():
    url = f'https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}'
    try:
        res = requests.get(url)
        return {s['title']: s['key'] for s in res.json() if s['active']}
    except:
        return {}

# --- 3. ARBITRAGE ENGINE ---
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

        # FILTER: Only use bookies the user selected
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
            
            # STAKES (Rounded to 0.50)
            stake1 = round(((investment * ip1) / total_ip) * 2) / 2
            stake2 = round(((investment * ip2) / total_ip) * 2) / 2
            
            # PROFIT MONEY
            return1 = stake1 * best_odds[teams[0]]['price']
            return2 = stake2 * best_odds[teams[1]]['price']
            profit_money = min(return1, return2) - (stake1 + stake2)

            found_arbs.append({
                "match": f"{teams[0]} vs {teams[1]}",
                "profit": roi,
                "money": profit_money,
                "t1": teams[0], "b1": stake1, "o1": best_odds[teams[0]]['price'], "bk1": best_odds[teams[0]]['bookie'],
                "t2": teams[1], "b2": stake2, "o2": best_odds[teams[1]]['price'], "bk2": best_odds[teams[1]]['bookie']
            })
            
    return found_arbs

# --- 4. THE PRO INTERFACE ---
st.title("🦅 Albatross Pro")

# SIDEBAR SETTINGS
st.sidebar.header("⚙️ Settings")
st.sidebar.caption("Filter your Bookmakers")
all_uk_bookies = ["William Hill", "Bet365", "Betfair", "Unibet", "Betway", "Ladbrokes", "Coral", "Paddy Power", "Sky Bet", "888sport", "BoyleSports", "BetVictor"]
my_bookies = st.sidebar.multiselect("Select your Accounts:", all_uk_bookies, default=["William Hill", "Bet365", "Unibet", "Betfair"])
st.sidebar.markdown("---")
invest = st.sidebar.number_input("Total Bankroll (£)", value=100)

# MAIN SCREEN
sports = get_active_sports()
choice = st.selectbox("Select Sport", list(sports.keys()) if sports else [])

if st.button("Scan Markets", type="primary"):
    if not my_bookies:
        st.error("Please select at least 2 bookmakers in the sidebar (arrow at top left).")
    elif not sports:
        st.error("No sports found.")
    else:
        with st.spinner(f"Scanning {choice}..."):
            arbs = get_arbs(sports[choice], invest, my_bookies)
            
            if not arbs:
                st.info("No sure bets found with your selected bookies.")
            else:
                st.success(f"Found {len(arbs)} opportunities!")
                for a in arbs:
                    st.markdown(f"""
                    <div style="border-left: 5px solid #4CAF50; background-color: #f1f8e9; padding: 15px; margin-bottom: 10px; border-radius: 5px;">
                        <h3 style="margin:0; color: #2e7d32;">Profit: £{a['money']:.2f} <small>({a['profit']:.2f}%)</small></h3>
                        <p style="color: #555; margin-bottom: 10px;">{a['match']}</p>
                        <div style="display:flex; justify-content:space-between; background: white; padding: 10px; border-radius: 5px;">
                            <div style="width:48%;">
                                <b>{a['t1']}</b><br>
                                <span style="color:blue; font-size:1.1em;">Bet £{a['b1']:.2f}</span><br>
                                @ {a['o1']} <small>({a['bk1']})</small>
                            </div>
                            <div style="width:48%;">
                                <b>{a['t2']}</b><br>
                                <span style="color:blue; font-size:1.1em;">Bet £{a['b2']:.2f}</span><br>
                                @ {a['o2']} <small>({a['bk2']})</small>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
