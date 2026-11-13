"""Assistant Kimi K3 connecté aux données de course sélectionnées."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from openai import OpenAI

from api_jolpica import obtenir_courses, obtenir_resultats
from f1_theme import apply_f1_theme


st.set_page_config(page_title="Analyste Kimi K3", page_icon="🤖", layout="wide")
apply_f1_theme()
st.title("🤖 Analyste F1 avec Kimi K3")
st.write(
    "Choisis une course, puis demande à Kimi d'expliquer les résultats. "
    "Seules les données affichées sont envoyées au modèle."
)


def lire_cle_api() -> str:
    """Lit la clé Streamlit ou, à défaut, la variable Windows."""

    cle = ""
    try:
        cle = str(st.secrets.get("MOONSHOT_API_KEY", "")).strip()
    except Exception:
        # Streamlit lève aussi une erreur si aucun fichier secrets.toml n'existe.
        pass
    return cle or os.getenv("MOONSHOT_API_KEY", "").strip()


@st.cache_data(ttl=3600, show_spinner=False)
def charger_courses(saison: int) -> pd.DataFrame:
    return obtenir_courses(saison)


@st.cache_data(ttl=3600, show_spinner=False)
def charger_resultats(saison: int, manche: int) -> pd.DataFrame:
    return obtenir_resultats(saison, manche)


saison = st.sidebar.number_input(
    "Saison",
    min_value=1950,
    max_value=2100,
    value=2026,
    step=1,
)

try:
    courses = charger_courses(int(saison))
except Exception as erreur:
    st.error(f"Chargement du calendrier impossible : {erreur}")
    st.stop()

if courses.empty:
    st.warning("Aucune course disponible pour cette saison.")
    st.stop()

libelles = {
    int(ligne.manche): f"Manche {int(ligne.manche)} — {ligne.grand_prix}"
    for ligne in courses.itertuples()
}
manche = st.selectbox(
    "Grand Prix",
    options=list(libelles),
    format_func=lambda numero: libelles[numero],
)

try:
    resultats = charger_resultats(int(saison), int(manche))
except Exception as erreur:
    st.error(f"Chargement des résultats impossible : {erreur}")
    st.stop()

if resultats.empty:
    st.info(
        "Les résultats de cette course ne sont pas encore disponibles. "
        "Choisis une course déjà disputée."
    )
    st.stop()

colonnes = [
    "position",
    "pilote",
    "ecurie",
    "grille",
    "positions_gagnees",
    "points",
    "statut",
    "temps",
    "meilleur_tour",
]
st.dataframe(
    resultats.reindex(columns=colonnes),
    width="stretch",
    hide_index=True,
)

question = st.text_area(
    "Question pour Kimi",
    placeholder=(
        "Exemple : quels pilotes ont le plus progressé entre la grille "
        "et l'arrivée, et que peut-on conclure ?"
    ),
)

cle_api = lire_cle_api()
if not cle_api:
    st.warning(
        "Kimi est désactivé : ajoute MOONSHOT_API_KEY dans "
        "`.streamlit/secrets.toml` ou dans une variable d'environnement."
    )
    with st.expander("Voir la configuration"):
        st.code(
            'MOONSHOT_API_KEY = "colle_ta_cle_ici"',
            language="toml",
        )

if st.button("Demander à Kimi", type="primary", disabled=not cle_api):
    if not question.strip():
        st.warning("Écris une question avant de continuer.")
    else:
        contexte = resultats.reindex(columns=colonnes).to_json(
            orient="records",
            force_ascii=False,
        )
        client = OpenAI(
            api_key=cle_api,
            base_url="https://api.moonshot.ai/v1",
        )

        with st.spinner("Kimi analyse la course..."):
            try:
                reponse = client.chat.completions.create(
                    model="kimi-k3",
                    reasoning_effort="low",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un analyste de Formule 1. Réponds en "
                                "français, de façon claire et structurée. "
                                "Utilise uniquement les données JSON fournies. "
                                "N'invente aucune cause, météo ou statistique. "
                                "Distingue les faits des hypothèses et signale "
                                "toute information manquante."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Saison : {int(saison)}\n"
                                f"Course : {libelles[int(manche)]}\n"
                                f"Résultats JSON : {contexte}\n\n"
                                f"Question : {question.strip()}"
                            ),
                        },
                    ],
                )
                texte = reponse.choices[0].message.content
                st.subheader("Réponse de Kimi")
                st.markdown(texte or "Kimi n'a renvoyé aucun texte.")
            except Exception as erreur:
                message = str(erreur)
                if "401" in message:
                    st.error(
                        "Authentification refusée (401). Vérifie la clé "
                        "MOONSHOT_API_KEY puis redémarre Streamlit."
                    )
                elif "429" in message:
                    st.error(
                        "Quota Kimi indisponible (429). Vérifie le solde ou "
                        "le forfait du compte Moonshot. Le reste du tableau "
                        "de bord continue de fonctionner sans Kimi."
                    )
                else:
                    st.error(f"Erreur pendant l'appel à Kimi : {erreur}")
