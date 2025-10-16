import streamlit as st
import random
import json
from suguru_generator import generate_puzzle
from suguru_solver import solve_puzzle
import streamlit.components.v1 as components

st.set_page_config(page_title="Suguru Interactif", page_icon="🧩", layout="centered")

# ==============================
# INIT SESSION
# ==============================
for key in ["user", "solution", "regions", "givens", "rows", "cols"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "user" else {}

# ==============================
# GÉNÉRATION AUTO (5x5 → 12x12)
# ==============================
st.title("🧩 Suguru Interactif")

if st.button("🔁 Générer une grille aléatoire (5×5 → 12×12)"):
    st.info("Génération en cours...")
    found = False
    for size in range(5, 13):
        for _ in range(150):
            result = generate_puzzle(size, size, max_region_size=8)
            if result:
                regions, solution, givens = result
                if len(givens) > 0:
                    st.session_state.rows = size
                    st.session_state.cols = size
                    st.session_state.regions = regions
                    st.session_state.solution = solution
                    st.session_state.givens = givens
                    st.session_state.user = dict(givens)
                    found = True
                    break
        if found:
            break
    if found:
        st.success(f"✅ Grille {st.session_state.rows}×{st.session_state.cols} générée avec succès !")
    else:
        st.error("❌ Impossible de générer une grille valide.")

# ==============================
# VALIDATION
# ==============================
def validate_grid(user, regions):
    errors = []

    # Règle 1 : doublons dans régions
    for rid, cells in regions.items():
        vals = [user.get(c) for c in cells if user.get(c)]
        if len(vals) != len(set(vals)):
            errors.append(f"Doublon dans la région {rid}")

    # Règle 2 : valeurs adjacentes identiques
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
# SVG INTERACTIF + JS
# ==============================
def render_interactive_svg(rows, cols, regions, user_values, givens):
    cell_size = 50
    palette = ["#e6f7ff", "#fff5e6", "#e6ffe6", "#ffe6f2", "#f2e6ff", "#f0fff0", "#fff0f5"]
    region_colors = {}
    svg_parts = [f'<svg id="suguru" width="{cols*cell_size}" height="{rows*cell_size}" xmlns="http://www.w3.org/2000/svg">']

    for r in range(rows):
        for c in range(cols):
            cell_id = (r, c)
            rid = None
            for rid_, cells in regions.items():
                if cell_id in cells:
                    rid = rid_
                    break
            color = region_colors.setdefault(rid, palette[len(region_colors) % len(palette)])
            x, y = c * cell_size, r * cell_size
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" stroke="black" stroke-width="1" data-row="{r}" data-col="{c}" class="cell"/>')
            val = user_values.get(cell_id, "")
            color_text = "black" if cell_id not in givens else "darkblue"
            svg_parts.append(f'<text x="{x + cell_size/2}" y="{y + cell_size/2 + 6}" text-anchor="middle" font-size="20" fill="{color_text}">{val}</text>')

    svg_parts.append("</svg>")
    svg_code = "".join(svg_parts)

    html_code = f"""
    <html>
    <body>
    {svg_code}
    <script>
    const cells = document.querySelectorAll('.cell');
    cells.forEach(cell => {{
        cell.addEventListener('click', () => {{
            const r = cell.getAttribute('data-row');
            const c = cell.getAttribute('data-col');
            const val = prompt(`Entrer la valeur pour la case [${{parseInt(r)+1}},${{parseInt(c)+1}}] (0 pour vider)`);
            if (val !== null) {{
                window.parent.postMessage({{"type": "cell_update", "row": parseInt(r), "col": parseInt(c), "val": parseInt(val)}}, "*");
            }}
        }});
    }});
    </script>
    </body>
    </html>
    """
    return html_code

# ==============================
# GESTION DES ÉVÉNEMENTS (JS → Python)
# ==============================
msg = st.experimental_get_query_params().get("msg")

if st.session_state.regions:
    rows, cols = st.session_state.rows, st.session_state.cols
    st.subheader(f"🎯 Grille {rows}×{cols}")

    html = render_interactive_svg(rows, cols, st.session_state.regions, st.session_state.user, st.session_state.givens)
    components.html(html, height=rows * 55, scrolling=False)

    # Petit hack : écoute les messages du navigateur (Streamlit ne supporte pas les events JS nativement)
    msg_json = st.experimental_get_query_params().get("cell_update")
    if msg_json:
        try:
            data = json.loads(msg_json[0])
            r, c, v = data["row"], data["col"], data["val"]
            cell = (r, c)
            if cell in st.session_state.givens:
                st.warning("⛔ Case initiale non modifiable.")
            else:
                if v == 0:
                    st.session_state.user.pop(cell, None)
                else:
                    st.session_state.user[cell] = v
            st.experimental_set_query_params()  # efface le paramètre
            st.rerun()
        except Exception:
            pass

    errors = validate_grid(st.session_state.user, st.session_state.regions)
    if errors:
        st.error("⚠️ " + "\n".join(errors))
    else:
        st.info("✅ Pas de conflit détecté.")

    if st.button("🧮 Générer la solution complète"):
        try:
            sol = solve_puzzle(st.session_state.regions, st.session_state.givens)
            if sol:
                st.session_state.solution = sol
                st.session_state.user = dict(sol)
                st.success("✅ Solution générée et affichée.")
                st.rerun()
            else:
                st.error("❌ Échec de la résolution automatique.")
        except Exception as e:
            st.error(f"Erreur solveur : {e}")

    if st.session_state.solution and st.session_state.user == st.session_state.solution:
        st.success("🏆 Bravo ! Grille complétée correctement !")
else:
    st.info("Clique sur “Générer une grille aléatoire” pour commencer.")
