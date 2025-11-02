import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

st.title("🤖 DeepSeek AI Trader")
st.markdown("**💰 Capital:** 100 USDT | **⚡ Mode:** Démonstration")

# Sidebar
with st.sidebar:
    st.header("🎮 Contrôles")
    if st.button("🚀 Démarrer le Bot", type="primary"):
        st.session_state.bot_running = True
        st.success("Bot démarré!")
    
    if st.button("🛑 Arrêter le Bot", type="secondary"):
        st.session_state.bot_running = False
        st.warning("Bot arrêté!")
    
    st.markdown("---")
    st.markdown(f"**Statut:** {'🟢 EN COURS' if st.session_state.get('bot_running') else '🔴 ARRÊTÉ'}")

# Graphique simulé
st.subheader("📈 Performance")
dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
values = [100 + i * (2 + i * 0.1) for i in range(100)]
df = pd.DataFrame({'Date': dates, 'Valeur': values})
fig = px.line(df, x='Date', y='Valeur', title="Évolution du Portefeuille")
st.plotly_chart(fig, use_container_width=True)

# Logs
st.subheader("📝 Logs")
st.info("🤖 Le bot analyse le marché...")
st.info("💎 Prix BTC: 42,150$ | ETH: 2,850$")
st.success("✅ App prête pour le trading!")

st.markdown(f"*Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}*")
