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
    # nouvelle UI interactive SVG + contrôles
    display_interactive_grid(rows, cols, regions, givens)

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


# --- UI améliorée : SVG + sélection + validateur en temps réel ---
import html
from typing import Dict, Tuple, List, Set

Cell = Tuple[int,int]

def compute_cell_borders(regions: Dict[int, List[Cell]], rows: int, cols: int):
    """
    Pour chaque case, calcule les côtés où il faut dessiner une bordure épaisse
    (quand la case voisine appartient à une région différente ou est hors grille).
    Retourne dict cell -> dict(top,right,bottom,left) boolean.
    """
    region_map = {}
    for rid, cells in regions.items():
        for cell in cells:
            region_map[cell] = rid

    borders = {}
    for r in range(rows):
        for c in range(cols):
            cell = (r,c)
            rid = region_map.get(cell, None)
            top = (r-1 < 0) or (region_map.get((r-1,c), None) != rid)
            bottom = (r+1 >= rows) or (region_map.get((r+1,c), None) != rid)
            left = (c-1 < 0) or (region_map.get((r,c-1), None) != rid)
            right = (c+1 >= cols) or (region_map.get((r,c+1), None) != rid)
            borders[cell] = {"top": top, "right": right, "bottom": bottom, "left": left}
    return borders

def find_conflicts(rows:int, cols:int, regions:Dict[int,List[Cell]], values:Dict[Cell,int]):
    """
    Retourne un set de cellules en conflit.
    Conflits :
      - même valeur dans la même région (deux cellules d'une région ont même nombre)
      - même valeur dans deux cellules adjacentes (y compris diagonales)
      - valeur hors plage pour la région (ex : 5 dans une région de taille 3)
    """
    region_map = {}
    region_size = {}
    for rid, cells in regions.items():
        for cell in cells:
            region_map[cell] = rid
        region_size[rid] = len(cells)

    conflicts = set()

    # check region duplicates and out-of-range
    for rid, cells in regions.items():
        seen = {}
        for cell in cells:
            val = values.get(cell, None)
            if val is None:
                continue
            if not (1 <= val <= region_size[rid]):
                conflicts.add(cell)
            else:
                if val in seen:
                    conflicts.add(cell)
                    conflicts.add(seen[val])
                else:
                    seen[val] = cell

    # adjacency (8 directions)
    for r in range(rows):
        for c in range(cols):
            cell = (r,c)
            val = values.get(cell, None)
            if val is None:
                continue
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0: continue
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nb = (nr,nc)
                        if values.get(nb, None) == val:
                            conflicts.add(cell)
                            conflicts.add(nb)
    return conflicts

def render_svg_grid(rows:int, cols:int, regions:Dict[int,List[Cell]],
                    values:Dict[Cell,int], givens:Dict[Cell,int], selected:Cell=None,
                    width_px:int=600, height_px:int=600):
    """
    Retourne une string SVG représentant la grille, remplie selon values,
    les givens, la sélection et les conflits (qui seront gérés en couleur par appelant).
    """
    cell_w = width_px / cols
    cell_h = height_px / rows
    borders = compute_cell_borders(regions, rows, cols)

    # calcule les conflits pour coloration
    conflicts = find_conflicts(rows, cols, regions, values)

    svg_parts = []
    svg_parts.append(f'<svg width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}" xmlns="http://www.w3.org/2000/svg">')
    svg_parts.append('<defs>')
    svg_parts.append('<style><![CDATA['
                     ' .cell-text { font-family: Arial, sans-serif; font-size: 14px; text-anchor: middle; dominant-baseline: central;}'
                     ']]></style>')
    svg_parts.append('</defs>')

    # background
    svg_parts.append(f'<rect width="100%" height="100%" fill="white" />')

    # draw cells (fill color depending on given/conflict/selected)
    for r in range(rows):
        for c in range(cols):
            x = c * cell_w
            y = r * cell_h
            cell = (r,c)
            val = values.get(cell, None)
            is_given = cell in givens
            is_selected = (selected == cell)
            is_conflict = (cell in conflicts)
            # choose fill
            if is_conflict:
                fill = "#ffd6d6"  # light red
            elif is_given:
                fill = "#e8e8e8"  # grey
            elif is_selected:
                fill = "#e6f7ff"  # light blue
            else:
                fill = "#ffffff"  # white

            svg_parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="{fill}" stroke="none"/>')

            # draw borders depending on region edge
            b = borders[cell]
            stroke_width = 3
            # top
            if b["top"]:
                svg_parts.append(f'<line x1="{x}" y1="{y}" x2="{x+cell_w}" y2="{y}" stroke="black" stroke-width="{stroke_width}"/>')
            # left
            if b["left"]:
                svg_parts.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y+cell_h}" stroke="black" stroke-width="{stroke_width}"/>')
            # right
            if b["right"]:
                svg_parts.append(f'<line x1="{x+cell_w}" y1="{y}" x2="{x+cell_w}" y2="{y+cell_h}" stroke="black" stroke-width="{stroke_width}"/>')
            # bottom
            if b["bottom"]:
                svg_parts.append(f'<line x1="{x}" y1="{y+cell_h}" x2="{x+cell_w}" y2="{y+cell_h}" stroke="black" stroke-width="{stroke_width}"/>')

            # draw thin grid lines inside region (subtle)
            svg_parts.append(f'<rect x="{x+1}" y="{y+1}" width="{cell_w-2}" height="{cell_h-2}" fill="none" stroke="#d9d9d9" stroke-width="0.5"/>')

            # draw value if present
            if val is not None and val != 0:
                cx = x + cell_w/2
                cy = y + cell_h/2
                # larger font for bigger cells
                font_size = int(min(cell_w, cell_h) * 0.45)
                svg_parts.append(f'<text x="{cx}" y="{cy}" class="cell-text" font-size="{font_size}px" fill="black">{html.escape(str(val))}</text>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def display_interactive_grid(rows:int, cols:int, regions:Dict[int,List[Cell]],
                             givens:Dict[Cell,int]):
    """
    Affiche SVG + controls pour sélectionner une case et entrer une valeur.
    - Utilise st.session_state['user'] comme valeurs en cours.
    - Gère validation en temps réel et surlignage.
    """
    if "user" not in st.session_state:
        st.session_state.user = dict(givens) if givens else {}
    if "selected_cell" not in st.session_state:
        st.session_state.selected_cell = None

    # prepare values (union of user and givens)
    values = dict(st.session_state.user)
    values.update(givens or {})

    # compute conflicts
    conflicts = find_conflicts(rows, cols, regions, values)

    # render svg and show
    svg = render_svg_grid(rows, cols, regions, values, givens or {}, st.session_state.selected_cell, width_px=600, height_px=600)
    st.markdown(svg, unsafe_allow_html=True)

    # interactive selection grid: a grid of small buttons below the SVG to pick a cell
    st.write("Sélectionne une case puis entre une valeur dans la barre latérale.")
    for r in range(rows):
        cols_row = st.columns(cols)
        for c in range(cols):
            cell = (r,c)
            display_val = values.get(cell, 0)
            label = f"{display_val}" if display_val else ""
            # indicate conflict/given by emoji in button label to help
            suffix = ""
            if cell in givens:
                suffix = " 🔒"
            elif cell in conflicts:
                suffix = " ⚠️"
            # the button key must be stable
            clicked = cols_row[c].button(label + suffix, key=f"sel_{r}_{c}")
            if clicked:
                st.session_state.selected_cell = cell
                # scroll to top? not necessary

    # sidebar controls for editing selected cell
    with st.sidebar:
        st.subheader("Édition")
        sel = st.session_state.get("selected_cell", None)
        if sel is None:
            st.write("Aucune case sélectionnée.")
        else:
            r,c = sel
            rid = None
            for rr, cells in regions.items():
                if sel in cells:
                    rid = rr
                    break
            region_max = len(regions[rid]) if rid is not None else max(1, rows)
            st.write(f"Case sélectionnée : {sel} (region {rid}, valeurs 1..{region_max})")
            current = st.session_state.user.get(sel, givens.get(sel, 0))
            # allow 0 to clear
            new_val = st.number_input("Valeur (0 = effacer)", min_value=0, max_value=region_max, value=int(current) if current else 0, step=1, key="input_value")
            if st.button("Appliquer la valeur"):
                if sel in givens:
                    st.warning("Case donnée (givens) : impossible de modifier.")
                else:
                    if new_val == 0:
                        st.session_state.user.pop(sel, None)
                    else:
                        st.session_state.user[sel] = int(new_val)
                    st.experimental_rerun() if hasattr(st, "experimental_rerun") else None

    # realtime summary / validator message
    values_after = dict(st.session_state.user)
    values_after.update(givens or {})
    conflicts_after = find_conflicts(rows, cols, regions, values_after)
    if conflicts_after:
        st.error(f"{len(conflicts_after)} case(s) en conflit. ⚠️")
    else:
        st.success("Aucune erreur détectée pour l'instant ✔️")
