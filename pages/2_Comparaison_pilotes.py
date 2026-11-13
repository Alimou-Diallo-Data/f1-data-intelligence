"""Comparaison interactive de deux pilotes."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from api_jolpica import obtenir_resultats_historiques
from f1_theme import apply_f1_theme, styliser_figure


st.set_page_config(page_title="Comparaison pilotes", page_icon="⚔️", layout="wide")
apply_f1_theme()
st.title("⚔️ Comparaison de pilotes")


@st.cache_data(ttl=86400, show_spinner=False)
def charger_historique(debut: int, fin: int):
    return obtenir_resultats_historiques(debut, fin)


annee_actuelle = datetime.now().year
debut, fin = st.sidebar.slider(
    "Période",
    min_value=2000,
    max_value=annee_actuelle,
    value=(max(2000, annee_actuelle - 3), annee_actuelle),
)

try:
    with st.spinner("Téléchargement des saisons sélectionnées..."):
        resultats = charger_historique(debut, fin)
except Exception as erreur:
    st.error(f"Impossible de charger l'historique : {erreur}")
    st.stop()

if resultats.empty:
    st.warning("Aucun résultat disponible pour cette période.")
    st.stop()

pilotes = (
    resultats[["driver_id", "pilote"]]
    .drop_duplicates()
    .sort_values("pilote")
)
options = pilotes["driver_id"].tolist()
noms = pilotes.set_index("driver_id")["pilote"].to_dict()

col1, col2 = st.columns(2)
with col1:
    pilote_a = st.selectbox(
        "Pilote A",
        options,
        format_func=lambda identifiant: noms[identifiant],
        index=0,
    )
with col2:
    index_b = 1 if len(options) > 1 else 0
    pilote_b = st.selectbox(
        "Pilote B",
        options,
        format_func=lambda identifiant: noms[identifiant],
        index=index_b,
    )

if pilote_a == pilote_b:
    st.warning("Choisis deux pilotes différents.")
    st.stop()

selection = resultats[resultats["driver_id"].isin([pilote_a, pilote_b])].copy()


def statistiques(df: pd.DataFrame) -> dict[str, float]:
    return {
        "Courses": len(df),
        "Points": float(df["points"].sum()),
        "Victoires": int(df["victoire"].sum()),
        "Podiums": int(df["podium"].sum()),
        "Position moyenne": float(df["position"].mean()),
        "Abandons": int(df["abandon"].sum()),
    }


stats_a = statistiques(selection[selection["driver_id"] == pilote_a])
stats_b = statistiques(selection[selection["driver_id"] == pilote_b])

st.subheader("Face-à-face")
tableau_stats = pd.DataFrame(
    {
        noms[pilote_a]: stats_a,
        noms[pilote_b]: stats_b,
    }
)
st.dataframe(tableau_stats, width="stretch")

selection = selection.sort_values(["date", "saison", "manche"])
selection["points_cumules"] = selection.groupby("driver_id")["points"].cumsum()

figure_points = px.line(
    selection,
    x="date",
    y="points_cumules",
    color="pilote",
    markers=True,
    title="Évolution cumulative des points sur la période",
    labels={"date": "Date", "points_cumules": "Points cumulés"},
)
st.plotly_chart(styliser_figure(figure_points), width="stretch")

figure_positions = px.line(
    selection,
    x="date",
    y="position",
    color="pilote",
    markers=True,
    hover_data=["grand_prix", "grille", "statut"],
    title="Classements course par course",
)
figure_positions.update_yaxes(autorange="reversed", dtick=1)
st.plotly_chart(styliser_figure(figure_positions), width="stretch")

commun = selection.pivot_table(
    index=["saison", "manche", "grand_prix"],
    columns="driver_id",
    values="position",
    aggfunc="first",
).dropna(subset=[pilote_a, pilote_b])

if not commun.empty:
    victoires_a = int((commun[pilote_a] < commun[pilote_b]).sum())
    victoires_b = int((commun[pilote_b] < commun[pilote_a]).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Duels gagnés — {noms[pilote_a]}", victoires_a)
    c2.metric(f"Duels gagnés — {noms[pilote_b]}", victoires_b)
    c3.metric("Courses communes", len(commun))

