# Suguru (Tectonic) — Jouable & Solveur (Python / Streamlit)

Jeu Suguru + solveur + générateur aléatoire en Python 3. Interface web via Streamlit.

## Contenu
- `app.py` : interface Streamlit (jouer / générer / résoudre).
- `suguru_solver.py` : solveur (backtracking, MRV, forward-checking).
- `suguru_generator.py` : générateur aléatoire de partitions + solutions.
- `requirements.txt`.

## Installation locale
1. `git clone <ton-repo>`
2. `python -m venv venv && source venv/bin/activate` (ou `venv\Scripts\activate` sur Windows)
3. `pip install -r requirements.txt`
4. `streamlit run app.py`

## Déployer gratuitement (Streamlit Community)
1. Pousser le repo sur GitHub.
2. Aller sur https://streamlit.io/cloud et connecter ton dépôt GitHub.
3. Créer une nouvelle app en sélectionnant `app.py` dans la branche appropriée.
4. Lancer — ton app est en ligne gratuitement.

## Notes & améliorations futures
- Améliorer l'UI (SVG + surbrillance des régions).
- Ajouter niveau de difficulté en ajustant le nombre de givens.
- Ajouter sauvegarde/partage automatique des puzzles.
