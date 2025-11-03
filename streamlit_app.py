# web_app_futures.py - VERSION AVEC CACHE SYNCHRONISÉ
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json
import threading
import random
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import os
import pickle

# =============================================
# CONFIGURATION FUTURES
# =============================================
CONFIG = {
    "initial_capital": 100,
    "cryptos": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"],
    "check_interval": 10,
    "max_leverage": 10,
    "default_leverage": 3,
    "risk_per_trade": 0.02,
    "theme": {
        "bg_dark": "#0f172a",
        "bg_darker": "#0a1120", 
        "bg_card": "#1e293b",
        "bg_secondary": "#1a2436",
        "text_primary": "#ffffff",
        "text_secondary": "#e2e8f0",
        "text_white": "#ffffff",
        "accent_green": "#10b981",
        "accent_red": "#ef4444",
        "accent_blue": "#3b82f6",
        "accent_yellow": "#f59e0b",
        "accent_purple": "#8b5cf6"
    }
}

# =============================================
# SYSTÈME DE CACHE SYNCHRONISÉ
# =============================================
CACHE_FILE = "shared_bot_cache.pkl"
CACHE_LOCK = threading.Lock()

def load_shared_cache():
    """Charge le cache partagé avec verrouillage"""
    with CACHE_LOCK:
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'rb') as f:
                    return pickle.load(f)
            return None
        except Exception as e:
            print(f"❌ Erreur chargement cache: {e}")
            return None

def save_shared_cache(data):
    """Sauvegarde dans le cache partagé avec verrouillage"""
    with CACHE_LOCK:
        try:
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde cache: {e}")
            return False

def get_bot_state():
    """Récupère l'état ACTUEL du bot depuis le cache partagé"""
    return load_shared_cache()

def update_bot_state(bot_manager):
    """Met à jour l'état du bot dans le cache partagé"""
    if bot_manager:
        return save_shared_cache(bot_manager)
    return False

def sync_bot_state():
    """Synchronise l'état du bot entre toutes les sessions"""
    try:
        shared_state = get_bot_state()
        if shared_state and 'bot_manager' in st.session_state:
            # Mettre à jour notre session avec l'état partagé
            st.session_state.bot_manager = shared_state
            return True
        return False
    except Exception as e:
        print(f"❌ Erreur synchronisation: {e}")
        return False

# =============================================
# AI TRADER FUTURES (identique à avant)
# =============================================
class FuturesAITrader:
    def __init__(self, initial_capital=100):
        self.initial_capital = initial_capital
        self.available_balance = initial_capital
        self.positions = {}
        self.trade_history = []
        self.portfolio_history = [{"timestamp": datetime.now(), "value": initial_capital}]
        self.last_analysis = {}
        self.position_count = 0
        
    def get_price(self, symbol):
        """Récupère le prix FUTURES depuis Binance"""
        try:
            url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=5)
            data = response.json()
            return float(data['price'])
        except:
            base_prices = {
                "BTCUSDT": 40000 + random.uniform(-1000, 1000),
                "ETHUSDT": 2500 + random.uniform(-100, 100), 
                "SOLUSDT": 100 + random.uniform(-5, 5),
                "XRPUSDT": 0.6 + random.uniform(-0.1, 0.1),
                "ADAUSDT": 0.45 + random.uniform(-0.05, 0.05)
            }
            return base_prices.get(symbol, 100)
    
    def get_historical_data(self, symbol, limit=50):
        """Récupère les données FUTURES"""
        try:
            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                'symbol': symbol,
                'interval': '5m',
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=5)
            return response.json()
        except:
            return None
    
    def calculate_rsi(self, closes, period=14):
        """Calcule le RSI"""
        if len(closes) <= period:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_dynamic_leverage(self, volatility, confidence, market_condition):
        """Calcule le levier optimal selon l'analyse"""
        base_leverage = min(5, 1 + (confidence * 4))
        
        if volatility > 0.05:
            base_leverage *= 0.7
        elif volatility < 0.02:
            base_leverage *= 1.2
            
        if market_condition == "TRENDING":
            base_leverage *= 1.1
        elif market_condition == "RANGING":
            base_leverage *= 0.8
            
        return max(1, min(CONFIG['max_leverage'], round(base_leverage)))
    
    def calculate_position_size(self, leverage, entry_price, stop_loss_price):
        """Calcule la taille de position avec risk management"""
        risk_amount = self.available_balance * CONFIG['risk_per_trade']
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff == 0:
            return 0, 0
            
        quantity = (risk_amount * leverage) / price_diff
        margin = (quantity * entry_price) / leverage
        
        return quantity, margin
    
    def calculate_stop_loss_take_profit(self, entry_price, action, volatility):
        """Calcule SL/TP dynamiques"""
        if action == "BUY":
            stop_loss = entry_price * (1 - (2 * volatility))
            take_profit = entry_price * (1 + (3 * volatility))
        else:  # SELL
            stop_loss = entry_price * (1 + (2 * volatility))
            take_profit = entry_price * (1 - (3 * volatility))
            
        return stop_loss, take_profit
    
    def determine_margin_mode(self, symbol, leverage):
        """Détermine le mode marge (Cross/Isolated)"""
        if leverage <= 3:
            return "CROSS"
        else:
            return "ISOLATED"
    
    def advanced_analysis(self, data, current_price, symbol):
        """Analyse technique pour Futures"""
        try:
            if not data or len(data) < 10:
                return {'action': 'HOLD', 'confidence': 0.3, 'reason': 'Données insuffisantes'}
            
            closes = [float(candle[4]) for candle in data[-50:]]
            highs = [float(candle[2]) for candle in data[-20:]]
            lows = [float(candle[3]) for candle in data[-20:]]
            
            sma_20 = sum(closes[-20:]) / min(20, len(closes))
            sma_50 = sum(closes[-50:]) / min(50, len(closes))
            rsi = self.calculate_rsi(closes)
            
            volatility = (max(highs) - min(lows)) / current_price if highs and lows else 0.02
            price_trend = "TRENDING" if abs(sma_20 - sma_50) / sma_50 > 0.02 else "RANGING"
            
            buy_signals = 0
            sell_signals = 0
            reasons = []
            
            if rsi < 35:
                buy_signals += 2
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 65:
                sell_signals += 2
                reasons.append(f"RSI overbought ({rsi:.1f})")
            
            if sma_20 > sma_50 and current_price > sma_20:
                buy_signals += 1
                reasons.append("Trend haussier")
            elif sma_20 < sma_50 and current_price < sma_20:
                sell_signals += 1
                reasons.append("Trend baissier")
            
            recent_high = max(highs[-10:]) if len(highs) >= 10 else current_price * 1.02
            recent_low = min(lows[-10:]) if len(lows) >= 10 else current_price * 0.98
            
            if current_price > recent_high:
                buy_signals += 1
                reasons.append("Breakout résistance")
            elif current_price < recent_low:
                sell_signals += 1
                reasons.append("Breakout support")
            
            confidence = min(0.9, 0.3 + (max(buy_signals, sell_signals) * 0.15))
            leverage = self.calculate_dynamic_leverage(volatility, confidence, price_trend)
            
            if buy_signals >= 2:
                return {
                    'action': 'BUY', 
                    'confidence': confidence, 
                    'reason': ' | '.join(reasons),
                    'leverage': leverage,
                    'volatility': volatility,
                    'market_condition': price_trend
                }
            elif sell_signals >= 2:
                return {
                    'action': 'SELL', 
                    'confidence': confidence, 
                    'reason': ' | '.join(reasons),
                    'leverage': leverage,
                    'volatility': volatility,
                    'market_condition': price_trend
                }
            else:
                return {
                    'action': 'HOLD', 
                    'confidence': 0.4, 
                    'reason': 'Signaux insuffisants'
                }
                
        except Exception as e:
            return {'action': 'HOLD', 'confidence': 0.3, 'reason': f'Erreur analyse: {str(e)}'}
    
    def analyze_market(self, symbol):
        """Analyse le marché Futures"""
        try:
            price = self.get_price(symbol)
            if not price:
                return None
            
            historical_data = self.get_historical_data(symbol)
            if not historical_data:
                return None
            
            analysis = self.advanced_analysis(historical_data, price, symbol)
            if analysis:
                analysis['symbol'] = symbol
                analysis['price'] = price
            return analysis
            
        except Exception as e:
            return None
    
    def execute_trade(self, analysis):
        """Exécute un trade Futures avec SL/TP"""
        try:
            if not analysis or 'symbol' not in analysis:
                return False, "❌ Analyse invalide"
                
            symbol = analysis['symbol']
            
            if analysis['action'] in ['BUY', 'SELL'] and analysis['confidence'] > 0.5:
                if symbol not in [pos['symbol'] for pos in self.positions.values()]:
                    stop_loss, take_profit = self.calculate_stop_loss_take_profit(
                        analysis['price'], analysis['action'], analysis['volatility']
                    )
                    
                    quantity, margin = self.calculate_position_size(
                        analysis['leverage'], analysis['price'], stop_loss
                    )
                    
                    if margin > self.available_balance:
                        return False, "❌ Marge insuffisante"
                    
                    if quantity <= 0:
                        return False, "❌ Quantité invalide"
                    
                    margin_mode = self.determine_margin_mode(symbol, analysis['leverage'])
                    
                    self.position_count += 1
                    position_id = f"{symbol}_{self.position_count}"
                    
                    self.positions[position_id] = {
                        'symbol': symbol,
                        'action': analysis['action'],
                        'quantity': quantity,
                        'entry_price': analysis['price'],
                        'leverage': analysis['leverage'],
                        'margin': margin,
                        'margin_mode': margin_mode,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'entry_time': datetime.now(),
                        'liquidation_price': self.calculate_liquidation_price(
                            analysis['price'], analysis['action'], analysis['leverage'], margin_mode
                        )
                    }
                    
                    self.available_balance -= margin
                    
                    log_message = f"🎯 {analysis['action']} {symbol} | Lev: {analysis['leverage']}x | Marge: {margin:.2f}$ | SL: {stop_loss:.2f} | TP: {take_profit:.2f}"
                    
                    self.trade_history.append({
                        'position_id': position_id,
                        'action': analysis['action'],
                        'symbol': symbol,
                        'price': analysis['price'],
                        'quantity': quantity,
                        'leverage': analysis['leverage'],
                        'margin': margin,
                        'margin_mode': margin_mode,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'timestamp': datetime.now(),
                        'reason': analysis['reason']
                    })
                    return True, log_message
            
            self.check_positions_sl_tp()
            return False, None
            
        except Exception as e:
            return False, f"❌ Erreur execution: {str(e)}"
    
    def calculate_liquidation_price(self, entry_price, action, leverage, margin_mode):
        """Calcule le prix de liquidation"""
        if margin_mode == "ISOLATED":
            if action == "BUY":
                return entry_price * (1 - 0.9/leverage)
            else:
                return entry_price * (1 + 0.9/leverage)
        else:
            return entry_price * 0.5
    
    def check_positions_sl_tp(self):
        """Vérifie les Stop Loss et Take Profit"""
        try:
            positions_to_close = []
            
            for position_id, position in list(self.positions.items()):
                current_price = self.get_price(position['symbol'])
                if not current_price:
                    continue
                
                if (position['action'] == 'BUY' and 
                    (current_price <= position['stop_loss'] or current_price >= position['take_profit'])):
                    positions_to_close.append(position_id)
                elif (position['action'] == 'SELL' and 
                      (current_price >= position['stop_loss'] or current_price <= position['take_profit'])):
                    positions_to_close.append(position_id)
            
            for position_id in positions_to_close:
                self.close_position(position_id, "SL/TP")
                
        except Exception as e:
            print(f"❌ Erreur vérification SL/TP: {e}")
    
    def close_position(self, position_id, reason):
        """Ferme une position"""
        try:
            if position_id in self.positions:
                position = self.positions[position_id]
                current_price = self.get_price(position['symbol'])
                
                if current_price:
                    if position['action'] == 'BUY':
                        pnl = (current_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - current_price) * position['quantity']
                    
                    pnl_percent = (pnl / position['margin']) * 100
                    
                    self.available_balance += position['margin'] + pnl
                    
                    status = "✅ TP" if ((position['action'] == 'BUY' and current_price >= position['take_profit']) or 
                                       (position['action'] == 'SELL' and current_price <= position['take_profit'])) else "🛑 SL"
                    
                    log_message = f"{status} {position['symbol']} | PnL: {pnl:+.2f}$ ({pnl_percent:+.1f}%) | {reason}"
                    
                    self.trade_history.append({
                        'position_id': position_id,
                        'action': 'CLOSE',
                        'symbol': position['symbol'],
                        'price': current_price,
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'timestamp': datetime.now(),
                        'reason': reason
                    })
                    
                    del self.positions[position_id]
                    return True, log_message
            
            return False, "❌ Impossible de fermer la position"
            
        except Exception as e:
            return False, f"❌ Erreur fermeture: {str(e)}"
    
    def update_portfolio_value(self):
        """Met à jour la valeur du portefeuille"""
        try:
            total_value = self.available_balance
            
            for position_id, position in self.positions.items():
                current_price = self.get_price(position['symbol'])
                if current_price:
                    if position['action'] == 'BUY':
                        pnl = (current_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - current_price) * position['quantity']
                    
                    total_value += position['margin'] + pnl
            
            self.portfolio_history.append({
                'timestamp': datetime.now(),
                'value': total_value
            })
            
            if len(self.portfolio_history) > 100:
                self.portfolio_history = self.portfolio_history[-100:]
            
            return total_value
            
        except Exception as e:
            return self.available_balance
    
    def get_portfolio_info(self):
        """Retourne les infos du portefeuille"""
        try:
            total_value = self.update_portfolio_value()
            initial_capital = self.portfolio_history[0]['value']
            total_return = ((total_value - initial_capital) / initial_capital) * 100
            
            closed_trades = [t for t in self.trade_history if t['action'] == 'CLOSE']
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
            
            total_margin = sum(pos['margin'] for pos in self.positions.values())
            avg_leverage = sum(pos['leverage'] for pos in self.positions.values()) / len(self.positions) if self.positions else 0
            
            return {
                'current_value': total_value,
                'available_balance': self.available_balance,
                'total_return': total_return,
                'active_positions': len(self.positions),
                'total_trades': len(closed_trades),
                'win_rate': win_rate,
                'total_margin': total_margin,
                'avg_leverage': avg_leverage
            }
            
        except Exception as e:
            return {
                'current_value': self.available_balance,
                'available_balance': self.available_balance,
                'total_return': 0,
                'active_positions': 0,
                'total_trades': 0,
                'win_rate': 0,
                'total_margin': 0,
                'avg_leverage': 0
            }

# =============================================
# BOT MANAGER WEB AVEC SYNCHRONISATION
# =============================================
class WebBotManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.trader = FuturesAITrader(CONFIG['initial_capital'])
        self.logs = []
        self.iteration = 0
        self.last_sync = datetime.now()
        
    def start_bot(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_bot, daemon=True)
            self.thread.start()
            self._add_log("🚀 Bot Futures démarré")
            self._add_log("⚡ Trading avec SL/TP et levier dynamique")
            update_bot_state(self)  # ⬅️ SAUVEGARDE IMMÉDIATE
            return True, "Bot démarré"
        return False, "Bot déjà en cours"
    
    def stop_bot(self):
        if self.running:
            self.running = False
            self._add_log("🛑 Bot arrêté")
            update_bot_state(self)  # ⬅️ SAUVEGARDE IMMÉDIATE
            return True, "Bot arrêté"
        return False, "Bot déjà arrêté"
    
    def is_bot_running(self):
        return self.running
    
    def _add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        if len(self.logs) > 50:
            self.logs = self.logs[-50:]
        # Sauvegarde après chaque log important
        if any(keyword in message for keyword in ["🚀", "🛑", "🎯", "✅", "🛑"]):
            update_bot_state(self)
    
    def _run_bot(self):
        while self.running:
            try:
                self.iteration += 1
                self._add_log(f"--- Itération #{self.iteration} ---")
                
                trades_executed = 0
                for symbol in CONFIG['cryptos']:
                    analysis = self.trader.analyze_market(symbol)
                    
                    if (analysis and 
                        analysis.get('action') in ['BUY', 'SELL'] and 
                        analysis.get('confidence', 0) > 0.5 and
                        analysis.get('symbol') and
                        analysis.get('price')):
                        
                        executed, log_message = self.trader.execute_trade(analysis)
                        if executed:
                            self._add_log(log_message)
                            trades_executed += 1
                            update_bot_state(self)  # ⬅️ SAUVEGARDE APRÈS TRADE
                
                if trades_executed == 0:
                    self._add_log("⏸️ En attente de signaux")
                
                portfolio_info = self.trader.get_portfolio_info()
                self._add_log(f"💰 Portefeuille: {portfolio_info['current_value']:.2f}$ ({portfolio_info['total_return']:+.2f}%)")
                
                # Synchronisation périodique
                if (datetime.now() - self.last_sync).seconds > 30:  # Toutes les 30 secondes
                    update_bot_state(self)
                    self.last_sync = datetime.now()
                
                time.sleep(CONFIG['check_interval'])
                
            except Exception as e:
                self._add_log(f"❌ Erreur: {str(e)}")
                time.sleep(10)

# =============================================
# INTERFACE STREAMLIT AVEC SYNCHRO AUTOMATIQUE
# =============================================
st.set_page_config(
    page_title="🤖 DeepSeek AI Trader - Futures",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown(f"""
<style>
    .main, .stApp {{
        background-color: {CONFIG['theme']['bg_dark']};
        color: {CONFIG['theme']['text_white']} !important;
    }}
    .stSidebar {{
        background-color: {CONFIG['theme']['bg_card']};
        color: {CONFIG['theme']['text_white']} !important;
    }}
    h1, h2, h3, h4, h5, h6, p, div, span {{
        color: {CONFIG['theme']['text_white']} !important;
    }}
    .stDataFrame {{
        background-color: {CONFIG['theme']['bg_card']};
        color: {CONFIG['theme']['text_white']} !important;
    }}
    .metric-card {{ 
        background-color: {CONFIG['theme']['bg_card']}; 
        padding: 15px; 
        border-radius: 10px;
        border-left: 4px solid {CONFIG['theme']['accent_green']};
        margin: 5px 0;
        color: {CONFIG['theme']['text_white']} !important;
    }}
</style>
""", unsafe_allow_html=True)

# =============================================
# INITIALISATION AVEC SYNCHRONISATION
# =============================================
if 'bot_manager' not in st.session_state:
    # Charger depuis le cache partagé
    shared_bot = get_bot_state()
    
    if shared_bot is not None:
        st.session_state.bot_manager = shared_bot
        st.sidebar.success("🔄 Bot synchronisé depuis le cache partagé")
    else:
        # Nouveau bot si aucun cache existant
        st.session_state.bot_manager = WebBotManager()
        update_bot_state(st.session_state.bot_manager)
        st.sidebar.info("🆕 Nouveau bot créé")

# Synchronisation automatique au chargement
sync_bot_state()

def main():
    st.title("🤖 DeepSeek AI Trader - Futures")
    st.markdown(f"**💰 Capital:** {CONFIG['initial_capital']} USDT | **⚡ Levier max:** {CONFIG['max_leverage']}x | **🎯 Risk:** {CONFIG['risk_per_trade']*100}%")
    st.markdown("**🔄 Cache synchronisé entre tous les appareils**")
    st.markdown("---")
    
    bot_manager = st.session_state.bot_manager
    trader = bot_manager.trader
    
    # Sidebar avec contrôles de synchronisation
    with st.sidebar:
        st.header("🎮 Contrôles")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Démarrer", use_container_width=True, 
                        disabled=bot_manager.running, type="primary"):
                success, message = bot_manager.start_bot()
                if success:
                    st.success(message)
                st.rerun()
        
        with col2:
            if st.button("🛑 Arrêter", use_container_width=True,
                        disabled=not bot_manager.running, type="secondary"):
                success, message = bot_manager.stop_bot()
                if success:
                    st.warning(message)
                st.rerun()
        
        # Contrôles de synchronisation
        st.markdown("---")
        st.header("🔄 Synchronisation")
        
        col_sync, col_force = st.columns(2)
        with col_sync:
            if st.button("🔄 Synchro", use_container_width=True):
                if sync_bot_state():
                    st.success("Synchronisé!")
                else:
                    st.error("Erreur synchro")
                st.rerun()
                
        with col_force:
            if st.button("💾 Sauvegarder", use_container_width=True):
                if update_bot_state(bot_manager):
                    st.success("Sauvegardé!")
                else:
                    st.error("Erreur sauvegarde")
        
        st.markdown("---")
        status = "🟢 EN COURS" if bot_manager.running else "🔴 ARRÊTÉ"
        st.markdown(f"**Statut:** {status}")
        st.markdown(f"**Itération:** #{bot_manager.iteration}")
        st.markdown(f"**Dernière MAJ:** {datetime.now().strftime('%H:%M:%S')}")
        
        # Prix en direct
        st.markdown("---")
        st.header("💎 Prix Futures")
        for crypto in CONFIG['cryptos']:
            price = trader.get_price(crypto)
            if price:
                st.metric(crypto, f"{price:.2f}$")
    
    # Layout principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Graphique
        st.subheader("📈 Performance Futures")
        
        if trader.portfolio_history:
            df = pd.DataFrame(trader.portfolio_history)
            fig = px.line(df, x='timestamp', y='value', 
                         title=f"Valeur du Portefeuille - {df['value'].iloc[-1]:.2f}$")
            fig.update_layout(
                plot_bgcolor=CONFIG['theme']['bg_card'],
                paper_bgcolor=CONFIG['theme']['bg_dark'],
                font_color=CONFIG['theme']['text_white'],
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Le graphique s'affichera lorsque le bot sera actif")
        
        # Positions
        st.subheader("💰 Positions Futures")
        
        if trader.positions:
            positions_data = []
            
            positions_items = list(trader.positions.items())
            
            for pos_id, position in positions_items:
                current_price = trader.get_price(position['symbol'])
                if current_price:
                    if position['action'] == 'BUY':
                        pnl = (current_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - current_price) * position['quantity']
                    
                    pnl_percent = (pnl / position['margin']) * 100
                    
                    positions_data.append({
                        'Symbol': position['symbol'],
                        'Side': position['action'],
                        'Levier': f"{position['leverage']}x",
                        'Mode Marge': position['margin_mode'],
                        'Prix Entrée': f"{position['entry_price']:.2f}",
                        'Prix Actuel': f"{current_price:.2f}",
                        'SL': f"{position['stop_loss']:.2f}",
                        'TP': f"{position['take_profit']:.2f}",
                        'P&L': f"{pnl:+.2f}$",
                        'P&L %': f"{pnl_percent:+.1f}%"
                    })
            
            if positions_data:
                df_positions = pd.DataFrame(positions_data)
                st.dataframe(df_positions, use_container_width=True, height=300)
            else:
                st.info("💡 Calcul des positions en cours...")
        else:
            st.info("📭 Aucune position ouverte")
    
    with col2:
        # Statistiques
        st.subheader("📊 Statistiques Futures")
        
        portfolio_info = trader.get_portfolio_info()
        
        st.metric("Valeur Portefeuille", f"{portfolio_info['current_value']:.2f}$")
        st.metric("Performance", f"{portfolio_info['total_return']:+.2f}%")
        st.metric("Balance Disponible", f"{portfolio_info['available_balance']:.2f}$")
        st.metric("Marge Utilisée", f"{portfolio_info['total_margin']:.2f}$")
        st.metric("Positions Actives", portfolio_info['active_positions'])
        st.metric("Total Trades", portfolio_info['total_trades'])
        st.metric("Win Rate", f"{portfolio_info['win_rate']:.1f}%")
        st.metric("Levier Moyen", f"{portfolio_info['avg_leverage']:.1f}x")
        
        # Logs
        st.subheader("📝 Logs Trading")
        
        logs_container = st.container(height=400)
        with logs_container:
            for log in reversed(bot_manager.logs[-15:]):
                if "✅" in log or "🎯" in log:
                    st.success(log)
                elif "❌" in log or "🛑" in log:
                    st.error(log)
                elif "💰" in log or "📈" in log:
                    st.info(log)
                elif "⏸️" in log:
                    st.warning(log)
                else:
                    st.text(log)
    
    # Actualisation automatique avec synchronisation
    if bot_manager.running:
        # Synchronisation périodique pendant l'exécution
        if st.session_state.get('last_auto_sync', 0) == 0 or time.time() - st.session_state.last_auto_sync > 10:
            sync_bot_state()
            st.session_state.last_auto_sync = time.time()
        
        time.sleep(3)
        st.rerun()

if __name__ == "__main__":
    main()
