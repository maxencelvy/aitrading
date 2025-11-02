import streamlit as st

st.title("✅ TEST RÉUSSI")
st.success("L'application fonctionne !")

if st.button("Cliquez-moi"):
    st.balloons()
    st.info("🎉 Félicitations !")
