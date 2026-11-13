"""Thème visuel commun à toutes les pages Streamlit."""

from __future__ import annotations

import base64
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st


COULEURS_ECURIES = {
    "ferrari": "#E10600",
    "red_bull": "#1E5BC6",
    "mercedes": "#00D2BE",
    "mclaren": "#FF8000",
    "aston_martin": "#00665E",
    "alpine": "#0090FF",
    "williams": "#00A0DE",
    "haas": "#B6BABD",
    "sauber": "#00E701",
    "rb": "#6692FF",
    "audi": "#BB0A30",
    "cadillac": "#8A8D8F",
}

COULEUR_PAR_DEFAUT = "#9A9A9F"


def couleur_equipe(constructeur_id: str | None) -> str:
    return COULEURS_ECURIES.get(str(constructeur_id), COULEUR_PAR_DEFAUT)


def apply_f1_theme() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&display=swap');

            html, body, [class*="css"] {
                font-family: 'Titillium Web', sans-serif;
            }
            .stApp {
                background-color: #0c0c0e;
                background-image:
                    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
                background-size: 6px 6px;
            }
            h1 {
                font-weight: 900 !important;
                font-style: italic;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #ffffff !important;
                border-left: 6px solid #E10600;
                padding-left: 14px;
            }
            h2, h3 {
                color: #ffffff !important;
                font-weight: 700 !important;
            }
            section[data-testid="stSidebar"] {
                background-color: #131316;
                border-right: 2px solid #E10600;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 4px;
                border-bottom: 1px solid #2a2a2e;
            }
            .stTabs [data-baseweb="tab"] {
                color: #9a9a9f;
                font-weight: 700;
                text-transform: uppercase;
                font-size: 0.85rem;
                letter-spacing: 0.5px;
                padding: 10px 18px;
            }
            .stTabs [aria-selected="true"] {
                color: #ffffff !important;
                border-bottom: 3px solid #E10600 !important;
            }
            div[data-testid="stMetric"] {
                background: linear-gradient(145deg, #1a1a1d, #131315);
                border: 1px solid #2a2a2e;
                border-left: 4px solid #E10600;
                border-radius: 6px;
                padding: 16px 18px;
            }
            div[data-testid="stMetricLabel"] {
                color: #9a9a9f !important;
                text-transform: uppercase;
                font-size: 0.75rem !important;
                letter-spacing: 1px;
            }
            div[data-testid="stMetricValue"] {
                color: #ffffff !important;
                font-weight: 900 !important;
            }
            div[data-testid="stDataFrame"] {
                border: 1px solid #2a2a2e;
                border-radius: 6px;
                overflow: hidden;
            }
            div[data-baseweb="select"] > div,
            .stNumberInput input,
            .stTextInput input,
            .stTextArea textarea {
                background-color: #1a1a1d !important;
                border: 1px solid #3a3a3e !important;
                color: #ffffff !important;
            }
            .stButton button {
                border-radius: 4px !important;
                border: 1px solid #E10600 !important;
            }
            hr {
                border-color: #2a2a2e !important;
            }
            .source-note {
                color: #8f8f95;
                font-size: 0.82rem;
                border-left: 3px solid #E10600;
                padding-left: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def styliser_figure(figure: go.Figure, *, hauteur: int | None = None) -> go.Figure:
    """Applique le thème sombre aux graphiques Plotly."""

    figure.update_layout(
        plot_bgcolor="#0c0c0e",
        paper_bgcolor="#0c0c0e",
        font_color="#ffffff",
        title_font_color="#ffffff",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
        ),
        margin=dict(l=20, r=20, t=55, b=20),
    )
    if hauteur:
        figure.update_layout(height=hauteur)
    return figure


def afficher_banniere_hero(
    chemin_image: str | None,
    titre: str,
    sous_titre: str = "",
    chemin_logo: str | None = None,
) -> None:
    """Affiche une bannière; utilise un dégradé si l'image est absente."""

    image_css = (
        "linear-gradient(110deg, #101014 0%, #360706 65%, #E10600 130%)"
    )
    if chemin_image and Path(chemin_image).exists():
        chemin = Path(chemin_image)
        extension = chemin.suffix.lstrip(".").lower()
        encodage = base64.b64encode(chemin.read_bytes()).decode()
        image_css = (
            "linear-gradient(100deg, rgba(10,10,12,0.94) 20%, "
            "rgba(10,10,12,0.35) 70%),"
            f'url("data:image/{extension};base64,{encodage}")'
        )

    logo_html = ""
    if chemin_logo and Path(chemin_logo).exists():
        logo = Path(chemin_logo)
        extension = logo.suffix.lstrip(".").lower()
        encodage = base64.b64encode(logo.read_bytes()).decode()
        logo_html = (
            '<img class="hero-f1-logo" '
            f'src="data:image/{extension};base64,{encodage}" />'
        )

    st.markdown(
        f"""
        <style>
            .hero-f1 {{
                position: relative;
                height: 250px;
                border-radius: 9px;
                overflow: hidden;
                margin-bottom: 24px;
                background-image: {image_css};
                background-size: cover;
                background-position: center 40%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                padding: 0 36px;
                border-left: 6px solid #E10600;
            }}
            .hero-f1 h1 {{
                font-size: 2.5rem !important;
                margin: 0 !important;
                border: 0 !important;
                padding: 0 !important;
                text-shadow: 0 2px 12px rgba(0,0,0,0.6);
            }}
            .hero-f1 p {{
                color: #d8d8db;
                font-size: 1rem;
                margin-top: 8px;
            }}
            .hero-f1-logo {{
                position: absolute;
                top: 22px;
                right: 32px;
                height: 42px;
            }}
        </style>
        <div class="hero-f1">
            {logo_html}
            <h1>{titre}</h1>
            <p>{sous_titre}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Alias conservé pour rester compatible avec le code initial de l'utilisateur.
afficher_bannière_hero = afficher_banniere_hero
