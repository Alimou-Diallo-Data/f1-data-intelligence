# F1 Data Intelligence

> Prototype réalisé avant le projet de maîtrise. La version complète (PostgreSQL, validation chronologique, explications SHAP) se trouve dans [f1-prediction-podium](https://github.com/Alimou-Diallo-Data/f1-prediction-podium).

Projet pédagogique Python + Streamlit pour apprendre à collecter, nettoyer,
visualiser et modéliser des données de Formule 1.

## Fonctionnalités

- calendrier, pilotes et classements depuis l'API Jolpica ;
- carte et tracé des circuits ;
- résultats détaillés, qualifications et arrêts aux stands ;
- comparaison de deux pilotes sur plusieurs saisons ;
- télémétrie OpenF1 : météo, tours, arrêts et pneumatiques ;
- prédiction éducative d'un podium avec deux modèles de machine learning ;
- séparation chronologique entraînement/test et comparaison à une référence ;
- importance des variables et simulateur de position sur la grille ;
- export CSV et téléchargement du modèle entraîné ;
- assistant Kimi K3 facultatif, limité aux données de la course sélectionnée.

## Structure

```text
F1_Data_Intelligence_Complete/
├── app.py
├── api_jolpica.py
├── api_openf1.py
├── f1_theme.py
├── ml_pipeline.py
├── pages/
│   ├── 1_Analyse_course.py
│   ├── 2_Comparaison_pilotes.py
│   ├── 3_Prediction_podium.py
│   ├── 4_Analyste_Kimi.py
│   └── 5_Telemetrie_OpenF1.py
├── tests/
├── .streamlit/
├── requirements.txt
├── installer_windows.bat
└── lancer_dashboard.bat
```

## Installation la plus simple sous Windows

1. Décompresse le projet.
2. Ouvre le dossier `F1_Data_Intelligence_Complete`.
3. Double-clique sur `installer_windows.bat`.
4. Quand l'installation est terminée, double-clique sur
   `lancer_dashboard.bat`.
5. Ouvre l'adresse indiquée, normalement `http://localhost:8501`.

Le script utilise directement le Python de l'environnement virtuel. Il n'est
donc pas nécessaire d'activer l'environnement dans PowerShell.

## Installation manuelle dans PowerShell

Les guillemets sont importants parce que le chemin contient des espaces.

```powershell
cd "C:\Users\User\Downloads\F1_Data_Intelligence_Complete"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Pour arrêter Streamlit, appuie réellement sur les touches `Ctrl` et `C` en
même temps dans le terminal. N'écris pas `Ctrl + C` comme une commande.

## Configurer Kimi K3

Le tableau de bord fonctionne entièrement sans Kimi. Pour activer la page
Kimi :

1. copie `.streamlit/secrets.toml.example` ;
2. renomme la copie en `.streamlit/secrets.toml` ;
3. remplace la valeur par ta clé Moonshot :

```toml
MOONSHOT_API_KEY = "ta_cle_moonshot"
```

Redémarre ensuite Streamlit. Ne mets jamais `secrets.toml` sur GitHub et ne
colle jamais la clé directement dans un fichier Python.

Autre possibilité dans PowerShell :

```powershell
$env:MOONSHOT_API_KEY = "ta_cle_moonshot"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Une erreur `401` indique généralement une clé incorrecte. Une erreur `429`
avec « solde insuffisant » vient du compte Moonshot : le code ne peut pas
contourner ce quota. Toutes les autres pages restent utilisables.

## Méthode de prédiction

La cible vaut `1` lorsqu'un pilote termine sur le podium. Les variables
principales sont :

- position sur la grille ;
- points, victoires et podiums obtenus avant la course ;
- forme récente du pilote et de son écurie ;
- taux d'abandon récent ;
- pilote, constructeur et circuit.

Chaque statistique historique applique un décalage d'une course (`shift(1)`).
Le résultat à prédire n'entre donc pas dans ses propres variables.

La dernière saison choisie sert entièrement de jeu de test. Deux modèles sont
comparés :

- régression logistique ;
- forêt aléatoire.

Une règle simple « top 3 sur la grille » sert de référence. Les métriques
affichées sont l'exactitude, la précision, le rappel, le score F1, le score de
Brier et l'aire sous la courbe ROC.

## Limites importantes

- Une prédiction est une probabilité, jamais une certitude.
- Les incidents, pénalités et changements météo sont difficiles à anticiper.
- Le simulateur utilise la position sur la grille renseignée par l'utilisateur.
- Les résultats futurs n'existent pas encore dans Jolpica.
- OpenF1 fournit gratuitement les données historiques à partir de 2023 ; son
  accès temps réel dépend de son offre actuelle.
- Kimi explique les données fournies, mais ne remplace pas la validation des
  chiffres et peut être indisponible si le quota du compte est épuisé.

## Tests

Depuis la racine du projet :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Les tests utilisent des données synthétiques et n'appellent pas Internet.

## Sources de données

- Jolpica F1 : <https://api.jolpi.ca/ergast/f1/>
- Documentation Jolpica : <https://github.com/jolpica/jolpica-f1/tree/main/docs>
- OpenF1 : <https://openf1.org/>
- Documentation Kimi K3 : <https://platform.kimi.ai/docs/guide/kimi-k3-quickstart>

Ce projet est éducatif et n'est pas affilié à la Formule 1, à Jolpica,
à OpenF1 ou à Moonshot AI.
