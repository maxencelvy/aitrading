import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
import random
import requests

# Configuration
CONFIG = {
    "initial_capital": 100,
    "cryptos": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "theme": {
        "bg_dark": "#0f172a",
        "bg_card": "#1e293b", 
        "text_white": "#ffffff"
    }
}

# Classe de trading simplifiée
class SimpleTrader:
    def __init__(self):
        self.capital = 100
        self.positions = []
        self.portfolio_history = [{"timestamp": datetime.now(), "value": 100}]
        self.logs = []
        
    def get_price(self, symbol):
        """Récupère le prix ou simule"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=5)
            return float(response.json()['price'])
        except:
            # Simulation si API échoue
            base_prices = {"BTCUSDT": 42000, "ETHUSDT": 2850, "SOLUSDT": 105}
            variation = random.uniform(-0.02, 0.02)
            return base_prices.get(symbol, 100) * (1 + variation)
    
    def analyze_and_trade(self):
        """Logique de trading simplifiée"""
        if random.random() > 0.7:  # 30% de chance de trade
            symbol = random.choice(CONFIG["cryptos"])
            price = self.get_price(symbol)
            action = random.choice(["BUY", "SELL"])
            
            if action == "BUY" and self.capital > 10:
                # Achat
                investment = min(self.capital * 0.2, 20)  # 20% max
                self.capital -= investment
                self.positions.append({
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': price,
                    'investment': investment,
                    'time': datetime.now()
                })
                self.add_log(f"🟢 ACHAT {symbol} - {investment:.2f}$ @ {price:.2f}$")
                return True
                
        # Fermer positions aléatoirement
        if self.positions and random.random() > 0.8:
            position = self.positions.pop(0)
            current_price = self.get_price(position['symbol'])
            pnl = (current_price - position['price']) * (position['investment'] / position['price'])
            self.capital += position['investment'] + pnl
            
            status = "✅ PROFIT" if pnl > 0 else "🔴 PERTE"
            self.add_log(f"{status} {position['symbol']} - PnL: {pnl:+.2f}$")
            return True
            
        return False
    
    def add_log(self, message):
        """Ajoute un message de log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        if len(self.logs) > 10:
            self.logs = self.logs[-10:]
    
    def update_portfolio(self):
        """Met à jour la valeur du portefeuille"""
        total_value = self.capital
        for position in self.positions:
            current_price = self.get_price(position['symbol'])
            if position['action'] == 'BUY':
                pnl = (current_price - position['price']) * (position['investment'] / position['price'])
                total_value += position['investment'] + pnl
        
        self.portfolio_history.append({
            'timestamp': datetime.now(),
            'value': total_value
        })
        
        if len(self.portfolio_history) > 50:
            self.portfolio_history = self.portfolio_history[-50:]
        
        return total_value

# Initialisation
if 'trader' not in st.session_state:
    st.session_state.trader = SimpleTrader()
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'iteration' not in st.session_state:
    st.session_state.iteration = 0

# Interface
st.title("🤖 DeepSeek AI Trader")
st.markdown("**💰 Capital:** 100 USDT | **⚡ Trading Actif**")

trader = st.session_state.trader

# Sidebar
with st.sidebar:
    st.header("🎮 Contrôles")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Démarrer", use_container_width=True, type="primary"):
            st.session_state.bot_running = True
            trader.add_log("🚀 Bot démarré")
    with col2:
        if st.button("🛑 Arrêter", use_container_width=True, type="secondary"):
            st.session_state.bot_running = False
            trader.add_log("🛑 Bot arrêté")
    
    st.markdown("---")
    status = "🟢 EN COURS" if st.session_state.bot_running else "🔴 ARRÊTÉ"
    st.markdown(f"**Statut:** {status}")
    st.markdown(f"**Itération:** #{st.session_state.iteration}")
    
    # Prix en direct
    st.markdown("---")
    st.header("💎 Prix en Direct")
    for crypto in CONFIG["cryptos"]:
        price = trader.get_price(crypto)
        st.metric(crypto, f"{price:.2f}$")

# Layout principal
col1, col2 = st.columns([2, 1])

with col1:
    # Graphique
    st.subheader("📈 Performance en Temps Réel")
    if trader.portfolio_history:
        df = pd.DataFrame(trader.portfolio_history)
        current_value = df['value'].iloc[-1]
        fig = px.line(df, x='timestamp', y='value', 
                     title=f"Valeur du Portefeuille: {current_value:.2f}$")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Positions
    st.subheader("💰 Positions Actives")
    if trader.positions:
        positions_data = []
        for pos in trader.positions:
            current_price = trader.get_price(pos['symbol'])
            pnl = (current_price - pos['price']) * (pos['investment'] / pos['price'])
            positions_data.append({
                'Crypto': pos['symbol'],
                'Action': pos['action'],
                'Prix Entrée': f"{pos['price']:.2f}$",
                'Prix Actuel': f"{current_price:.2f}$",
                'Investissement': f"{pos['investment']:.2f}$",
                'P&L': f"{pnl:+.2f}$"
            })
        st.dataframe(pd.DataFrame(positions_data), use_container_width=True)
    else:
        st.info("📭 Aucune position ouverte")

with col2:
    # Statistiques
    st.subheader("📊 Statistiques")
    total_value = trader.update_portfolio()
    initial_capital = trader.portfolio_history[0]['value']
    performance = ((total_value - initial_capital) / initial_capital) * 100
    
    st.metric("Valeur Portefeuille", f"{total_value:.2f}$")
    st.metric("Performance", f"{performance:+.2f}%")
    st.metric("Capital Disponible", f"{trader.capital:.2f}$")
    st.metric("Positions Actives", len(trader.positions))
    
    # Logs
    st.subheader("📝 Logs Trading")
    logs_container = st.container(height=300)
    with logs_container:
        for log in reversed(trader.logs):
            if "🟢" in log:
                st.success(log)
            elif "✅" in log:
                st.success(log)
            elif "🔴" in log:
                st.error(log)
            else:
                st.info(log)

# Logique de trading automatique
if st.session_state.bot_running:
    st.session_state.iteration += 1
    trade_executed = trader.analyze_and_trade()
    
    if trade_executed:
        st.rerun()
    
    # Actualisation automatique
    time.sleep(3)
    st.rerun()

st.markdown(f"*Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}*")
