# app.py
import streamlit as st
import json
from suguru_generator import generate_puzzle
from suguru_solver import SuguruPuzzle, Cell

st.set_page_config(page_title="Suguru (Tectonic) - Jouable", layout="wide")

@st.cache_data
def make_puzzle(rows, cols, max_region_size, seed=None):
    result = generate_puzzle(rows, cols, max_region_size, seed=seed)
    if result is None:
        st.error("Impossible de générer une grille valide. Réessaie.")
        return None
    return result


def init_session(rows, cols):
    if "puzzle" not in st.session_state:
        st.session_state.puzzle = None
    if "user" not in st.session_state:
        # user entered values; dict (r,c)->int or empty string
        st.session_state.user = {}
    if "solution" not in st.session_state:
        st.session_state.solution = None
    if "regions" not in st.session_state:
        st.session_state.regions = None

def regions_to_grid_map(regions, rows, cols):
    """
    return map cell -> region id
    """
    crm = {}
    for rid,cells in regions.items():
        for cell in cells:
            crm[cell] = rid
    return crm

def display_grid(rows, cols, regions, givens):
    crm = regions_to_grid_map(regions, rows, cols)
    # draw using columns
    for r in range(rows):
        cols_row = st.columns(cols)
        for c in range(cols):
            with cols_row[c]:
                cell = (r,c)
                if st.session_state.solution and cell in st.session_state.solution:
                    # if solved and show solution toggle on, show it
                    pass
                # style: show region id and known value
                val = st.session_state.user.get(cell, "")
                is_given = cell in givens
                if is_given:
                    st.markdown(f"**R{crm[cell]}**")
                    st.write("")  # small spacer
                    st.number_input("", min_value=1, max_value=regions[crm[cell]].__len__(),
                                    step=1, key=f"given_{r}_{c}", value=givens[cell], disabled=True)
                else:
                    # user input
                    current = val if isinstance(val, int) else None
                    v = st.number_input(f"", min_value=0, max_value=regions[crm[cell]].__len__(),
                                        step=1, key=f"user_{r}_{c}", value=current if current else 0)
                    if v == 0:
                        if cell in st.session_state.user:
                            del st.session_state.user[cell]
                    else:
                        st.session_state.user[cell] = int(v)

def load_puzzle_from_json(s):
    obj = json.loads(s)
    rows = obj["rows"]; cols = obj["cols"]
    regions = {int(k): [tuple(x) for x in v] for k,v in obj["regions"].items()}
    givens = {tuple([int(x) for x in k.split(",")]): int(v) for k,v in obj["givens"].items()}
    return rows, cols, regions, givens

def dump_puzzle_to_json(rows, cols, regions, givens):
    obj = {
        "rows": rows,
        "cols": cols,
        "regions": {str(k): v for k,v in regions.items()},
        "givens": {f"{k[0]},{k[1]}": v for k,v in givens.items()}
    }
    return json.dumps(obj)

# --- UI ---
st.title("Suguru (Tectonic) — Jouable & Générateur")
st.write("Génère des grilles aléatoires et résous-les. (Interface gratuite via Streamlit)")

# options
with st.sidebar:
    st.header("Paramètres")
    rows = st.number_input("Lignes", min_value=5, max_value=12, value=8, step=1)
    cols = st.number_input("Colonnes", min_value=5, max_value=12, value=8, step=1)
    max_region = st.number_input("Taille max région", min_value=2, max_value=6, value=5, step=1)
    seed = st.text_input("Seed (optionnel) -- laisse vide pour aléatoire", value="")
    gen_btn = st.button("Générer une nouvelle grille")
    st.write("---")
    st.write("Actions")
    solve_btn = st.button("Résoudre la grille (automatique)")
    reset_btn = st.button("Réinitialiser saisies")
    export_btn = st.button("Exporter puzzle JSON")
    uploaded = st.file_uploader("Importer puzzle JSON", type=["json"])
    st.write("Astuce: la génération peut essayer plusieurs partitions pour trouver une grille valide.")

init_session(rows, cols)

# import
if uploaded is not None:
    text = uploaded.read().decode()
    rr, cc, regs, giv = load_puzzle_from_json(text)
    st.session_state.regions = regs
    st.session_state.solution = None
    st.session_state.user = dict(giv)  # show givens as user entries
    st.experimental_rerun()

# generate
if gen_btn:
    s = int(seed) if seed.strip().isdigit() else None
    result = make_puzzle(rows, cols, max_region, s)
    if result is not None:
        regions, solution, givens = result
        st.session_state.regions = regions
        st.session_state.solution = None
        st.session_state.user = dict(givens)
        st.session_state.givens = givens
        st.success("Grille générée avec succès !")
    else:
        st.error("Impossible de générer une grille valide. Réessaie.")

# ensure puzzle exists
if st.session_state.get("regions") is None:
    st.info("Génère une grille pour commencer (bouton à gauche).")
else:
    regions = st.session_state.regions
    givens = st.session_state.get("givens", {})
    # display grid
    display_grid(rows, cols, regions, givens)

    # actions
    if reset_btn:
        st.session_state.user = dict(givens)
        st.success("Saisies réinitialisées.")
        st.experimental_rerun()

    if solve_btn:
        puzzle = SuguruPuzzle(rows, cols, regions, givens=st.session_state.user)
        sol = puzzle.solve()
        if sol:
            st.session_state.solution = sol
            # fill user with solution (non-destructive for givens)
            st.session_state.user = dict(sol)
            st.success("Solution trouvée et affichée.")
            st.experimental_rerun()
        else:
            st.error("Pas de solution trouvée pour l'état actuel (vérifie tes saisies).")

    if export_btn:
        json_txt = dump_puzzle_to_json(rows, cols, regions, givens)
        st.download_button("Télécharger JSON", json_txt, file_name="suguru_puzzle.json", mime="application/json")
