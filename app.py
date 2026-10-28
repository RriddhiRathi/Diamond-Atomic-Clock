"""Run: python -m streamlit run app.py."""
import streamlit as st
from diamondclock.dashboard import render_dashboard

st.set_page_config(page_title='DiamondClock Lab', page_icon='💎', layout='wide')
render_dashboard()
