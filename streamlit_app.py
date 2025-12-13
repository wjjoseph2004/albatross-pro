import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# --- CONFIG & DARK THEME ---
st.set_page_config(page_title="Albatross Diamond", page_icon="🦅", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTextInput>div>div>input, .stSelectbox>div>div>div { background-color: #262730; color: #FAFAFA; }
    [data-testid="stMetricValue"] { color: #00FF00; }
</style>
""", unsafe_allow_html=True)

# --- SETUP ---
API_KEY = "ccc71cee1188b0ff21fe42e9a7d174cd"
REGION = 'uk'
MARKET = 'h2h'
SPORT_LABELS = {
    "soccer_epl":"🇬🇧 Premier League", "soccer_uefa_champs_league":"🇪🇺 Champions League",
    "basketball_nba":"🇺🇸 NBA", "americanfootball_nfl":"🇺🇸 NFL", "tennis_atp":"🎾 Tennis (ATP)"
}
TOP_3 = ['soccer_epl', 'basketball_nba', 'tennis_atp']

if 'quota' not in st.session_state: st.session_state.quota = "Checking..."
if 'ledger' not in st.session_state: st.session_state.ledger = pd.DataFrame(columns=["Date","Match","Profit","Bk1","Bk2"])

# --- DATA FUNCTIONS ---
def update_quota(res):
    if 'x-requests-remaining' in res.headers:
        st.session_state.quota = res.headers['x-requests-remaining']

@st.cache_data(ttl=3600)
def get_sports():
    try:
        res = requests.get(f'https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}')
        update_quota(res)
        return {s['title']:s['key'] for s in res.json() if s['active']}
    except: return {}

def get_odds(sport, invest, bookies, ghost, test):
    try:
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds',
                           params={'apiKey':API_KEY, 'regions':REGION, 'markets':MARKET, 'oddsFormat':'decimal'})
        update_quota(res)
        data = res.json()
    except: return []
    
    out = []
    for e in data:
        if 'bookmakers' not in e: continue
        try: time_str = datetime.strptime(e['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M")
        except: time_str = "Soon"
        
        best = {}
        for b in e['bookmakers']:
            if b['title'] not in bookies: continue
            for m in b['markets']:
                if m['key'] == MARKET:
                    for o in m['outcomes']:
                        if o['name'] not in best or o['price'] > best[o['name']]['price']:
                            best[o['name']] = {'price': o['price'], 'bookie': b['title']}
        
        if len(best) != 2: continue
        teams = list(best.keys())
        ip = (1/best[teams[0]]['price']) + (1/best[teams[1]]['price'])
        
        if ip < 1.0 or test:
            stake1 = (invest * (1/best[teams[0]]['price'])) / ip
            stake2 = (invest * (1/best[teams[1]]['price'])) / ip
            if not ghost: stake1, stake2 = round(stake1*2)/2, round(stake2*2)/2
            else: stake1, stake2 = round(stake1), round(stake2)
            
            profit = (stake1 * best[teams[0]]['price']) - (stake1 + stake2)
            roi = ((1/ip)-1)*100
            
            out.append({
                "match": f"{teams[0]} vs {teams[1]}", "time": time_str, "roi": roi, "profit": profit,
                "t1": teams[0], "o1": best[teams[0]]['price'], "b1": best[teams[0]]['bookie'],
                "t2": teams[1], "o2": best[teams[1]]['price'], "b2": best[teams[1]]['bookie']
            })
    return out



# --- INTERFACE ---
st.title("🦅 Albatross Diamond")
c1, c2 = st.columns([3,1])
h = datetime.utcnow().hour
adv = "🎾 Tennis" if h<11 else "🇬🇧 EPL" if h<17 else "🇺🇸 NBA"
c1.info(f"Target: {adv}")

# Initial Load for Credits
sports_map = get_sports()
c2.metric("Credits", st.session_state.quota)

st.sidebar.header("Settings")
all_b = ["William Hill", "Bet365", "Unibet", "Betfair", "Ladbrokes", "Paddy Power", "Sky Bet"]
my_b = st.sidebar.multiselect("Bookies", all_b, default=all_b[:3])
bank = st.sidebar.number_input("Bankroll", 100)
min_p = st.sidebar.slider("Min Profit", 0.0, 10.0, 0.5)
ghost = st.sidebar.checkbox("Ghost Mode")
test = st.checkbox("🛠️ Test Mode (Show All)", value=True)

tab1, tab2, tab3, tab4 = st.tabs(["Scanner", "🚀 Rocket 3", "Ledger", "Help"])

def show_results(res):
    if not res: st.warning("No odds found.")
    for r in sorted(res, key=lambda x: x['roi'], reverse=True):
        if not test and r['profit'] < min_p: continue
        color = "#1B2E1E" if r['roi'] > 0 else "#262730"
        border = "#00FF7F" if r['roi'] > 0 else "#444"
        st.markdown(f"""
        <div style="background:{color}; padding:10px; border:1px solid {border}; border-radius:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between;">
                <b style="color:#FFF">{r['match']}</b> <span style="color:#CCC">🕒 {r['time']}</span>
            </div>
            <div style="color:{'#00FF7F' if r['roi']>0 else '#FFF'}">
                {'WIN' if r['roi']>0 else 'NO ARB'}: £{r['profit']:.2f} ({r['roi']:.2f}%)
            </div>
            <hr style="margin:5px 0; border-color:#555">
            <div style="font-size:0.9em; display:flex; justify-content:space-between; color:#CCC">
                <div>{r['t1']}<br>{r['o1']} ({r['b1']})</div>
                <div>{r['t2']}<br>{r['o2']} ({r['b2']})</div>
            </div>
        </div>""", unsafe_allow_html=True)

with tab1:
    prio = ["Premier League", "NBA", "ATP Tennis"]
    s_list = sorted(list(sports_map.keys()), key=lambda x: (0 if any(p in x for p in prio) else 1, x))
    target = st.selectbox("Sport", s_list)
    if st.button("Scan"):
        show_results(get_odds(sports_map[target], bank, my_b, ghost, test))

with tab2:
    if st.button("🚀 Launch Rocket 3"):
        st.write("Scanning Top 3 Markets...")
        combined = []
        for k in TOP_3:
            combined.extend(get_odds(k, bank, my_b, ghost, test))
        show_results(combined)

with tab3:
    with st.form("log"):
        c1,c2 = st.columns(2)
        m = c1.text_input("Match"); p = c2.number_input("Profit")
        if st.form_submit_button("Save"):
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([{"Match":m, "Profit":p}])], ignore_index=True)
    st.dataframe(st.session_state.ledger)

with tab4: st.markdown("### Guide\n* **Test Mode:** Check box to see all matches.")
