import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Stock Alert Dashboard",
    layout="wide"
)

st.title("📊 Stock Alert Dashboard")

df = pd.read_csv("signals.csv")

st.sidebar.header("Filtri")

min_score = st.sidebar.slider(
    "Score minimo",
    float(df["score"].min()),
    float(df["score"].max()),
    float(df["score"].min())
)

filtered = df[df["score"] >= min_score]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Titoli analizzati", len(df))
col2.metric("Top score", round(df["score"].max(), 1))
col3.metric("Max RelVol", round(df["relvol"].max(), 1))
col4.metric("Max Gap %", round(df["gap"].max(), 1))

st.subheader("🏆 Top Bullish Setup")
st.dataframe(
    df.sort_values("score", ascending=False).head(10),
    use_container_width=True
)

st.subheader("⚠️ Top Risk Setup")
st.dataframe(
    df.sort_values("score", ascending=True).head(10),
    use_container_width=True
)

st.subheader("🔥 Relative Volume Leaders")
st.dataframe(
    df.sort_values("relvol", ascending=False).head(10),
    use_container_width=True
)

st.subheader("📈 Score vs Relative Volume")
fig = px.scatter(
    filtered,
    x="relvol",
    y="score",
    size="relvol",
    hover_name="ticker",
    color="score",
    title="Momentum / Volume Map"
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Tutti i titoli")
st.dataframe(
    filtered.sort_values("score", ascending=False),
    use_container_width=True
)
