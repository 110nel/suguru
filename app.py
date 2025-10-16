import streamlit as st
import random
import math
import time
from suguru_generator import generate_puzzle

# ==============================
# 🔧 CONFIG
# ==============================
st.set_page_config(page_title="Suguru", page_icon="🧩", layout="centered")

# ==============================
# ⚙️ PARAMÈTRES
# ==============================
rows, cols = 8, 8
max_region = 5

# ==============================
# 🧠 INIT SESSION
# ==============================
for key in ["user", "solution", "regions", "givens"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key != "solution" else None

# ==============================
# 🎲 GÉNÉRATION DE GRILLE
# ==============================
st.title("Jeu de logique Suguru")

seed = st.text_input("Seed (optionnel) :", "")

if st.button("Générer une nouvelle grille"):
    s = int(seed) if seed.strip().isdigit() else None
    result = generate_puzzle(rows, cols, max_region, seed=s)
    if result:
        regions, solution, givens = result
        st.session_state.regions = regions
        st.session_state.solution = solution
        st.session_state.givens = givens
        st.session_state.user = dict(givens)
        st.success("✅ Grille générée avec succès !")
    else:
        st.error("❌ Impossible de générer une grille valide.")

# ==============================
# 🎨 DESSIN DE LA GRILLE SVG
# ==============================
def render_suguru_svg(rows, cols, regions, user_values, givens):
    cell_size = 50
    svg = f'<svg width="{cols*cell_size}" height="{rows*cell_size}" xmlns="http://www.w3.org/2000/svg">'
    region_colors = {}
    palette = ["#ffe6e6", "#e6f7ff", "#e6ffe6", "#fff5e6", "#f2e6ff", "#fff0f5"]

    # Dessine les cellules
    for r in range(rows):
        for c in range(cols):
            cell_id = (r, c)
            region_id = None
            for rid, cells in regions.items():
                if cell_id in cells:
                    region_id = rid
                    break
            color = region_colors.setdefault(region_id, palette[len(region_colors) % len(palette)])
            x, y = c * cell_size, r * cell_size
            svg += f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" stroke="black" stroke-width="1"/>'

            # Texte (valeur)
            val = user_values.get(cell_id, "")
            color_text = "black" if cell_id not in givens else "darkblue"
            svg += f'<text x="{x + cell_size/2}" y="{y + cell_size/2 + 6}" text-anchor="middle" font-size="20" fill="{color_text}">{val}</text>'
    
    svg += "</svg>"
    return svg

# ==============================
# ✅ VALIDATION EN TEMPS RÉEL
# ==============================
def validate_grid(user, regions):
    errors = []

    # Règle 1 : pas de doublon dans une région
    for rid, cells in regions.items():
        vals = [user.get(c) for c in cells if user.get(c)]
        if len(vals) != len(set(vals)):
            errors.append(f"Doublon détecté dans la région {rid}")

    # Règle 2 : pas de doublon dans les cellules adjacentes
    for (r, c), v in user.items():
        if not v:
            continue
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == dc == 0:
                    continue
                n = (r + dr, c + dc)
                if n in user and user[n] == v:
                    errors.append(f"Conflit entre ({r+1},{c+1}) et ({n[0]+1},{n[1]+1})")

    return errors

# ==============================
# 🧩 AFFICHAGE GRILLE + VALIDATION
# ==============================
if st.session_state.regions:
    st.subheader("Grille actuelle :")

    # Affiche la grille SVG
    svg = render_suguru_svg(rows, cols, st.session_state.regions, st.session_state.user, st.session_state.givens)
    st.markdown(svg, unsafe_allow_html=True)

    # Entrée utilisateur (simple)
    r = st.number_input("Ligne (1-8)", min_value=1, max_value=rows, step=1)
    c = st.number_input("Colonne (1-8)", min_value=1, max_value=cols, step=1)
    v = st.number_input("Valeur (1-5 ou 0 pour vider)", min_value=0, max_value=max_region, step=1)

    if st.button("Entrer la valeur"):
        cell = (r-1, c-1)
        if cell in st.session_state.givens:
            st.warning("Cette case est une donnée initiale.")
        else:
            if v == 0:
                st.session_state.user.pop(cell, None)
            else:
                st.session_state.user[cell] = v
            st.success(f"Valeur {v} placée en ({r},{c})")

    # Validation en temps réel
    errors = validate_grid(st.session_state.user, st.session_state.regions)
    if errors:
        st.error("!️ " + "\n".join(errors))
    else:
        st.info(" Aucune erreur détectée pour le moment.")

    # Victoire ?
    if st.session_state.solution and st.session_state.user == st.session_state.solution:
        st.success(" Félicitations ! Vous avez complété la grille !")

else:
    st.info("Clique sur 'Générer une nouvelle grille' pour commencer.")
