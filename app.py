import streamlit as st
from ui.dashboard import render_dashboard

st.set_page_config(page_title="College Football Rankings", page_icon="🏈", layout="wide")
render_dashboard()
