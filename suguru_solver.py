# suguru_solver.py
"""
Solveur Suguru (Tectonic / Kemaru)

Fournit :
- class SuguruPuzzle : utilitaire interne
- function solve_puzzle(regions, givens, rows=None, cols=None, timeout_nodes=None)
    => renvoie dict {(r,c): value} ou None si insolvable / timeout

Paramètres :
- regions : dict region_id -> list of (r,c) tuples
- givens  : dict (r,c) -> int (peuvent être vides)
- rows, cols : optionnels ; si omis, déduits depuis les cellules dans regions
- timeout_nodes : optionnel, coupe la recherche après ce nombre de noeuds explorés
"""

from typing import Dict, Tuple, List, Optional, Set
import random
import time
import sys

Cell = Tuple[int, int]

class SuguruPuzzle:
    def __init__(self, regions: Dict[int, List[Cell]], givens: Optional[Dict[Cell,int]] = None, rows: Optional[int]=None, cols: Optional[int]=None):
        self.regions = regions
        self.givens = dict(givens or {})
        # compute grid size if not provided
        max_r = -1
        max_c = -1
        for cells in regions.values():
            for (r,c) in cells:
                if r > max_r: max_r = r
                if c > max_c: max_c = c
        if rows is None:
            self.rows = max_r + 1
        else:
            self.rows = rows
        if cols is None:
            self.cols = max_c + 1
        else:
            self.cols = cols

        # map cell -> region id
        self.cell_region: Dict[Cell,int] = {}
        for rid, cells in regions.items():
            for cell in cells:
                self.cell_region[cell] = rid

        # region sizes
        self.region_size: Dict[int,int] = {rid: len(cells) for rid,cells in regions.items()}

        # neighbors (8 directions)
        self.neighbors: Dict[Cell, List[Cell]] = {}
        for r in range(self.rows):
            for c in range(self.cols):
                nbs = []
                for dr in (-1,0,1):
                    for dc in (-1,0,1):
                        if dr==0 and dc==0:
                            continue
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            nbs.append((nr,nc))
                self.neighbors[(r,c)] = nbs

    def solve(self, timeout_nodes: Optional[int]=None, randomize: bool=False) -> Optional[Dict[Cell,int]]:
        """
        Solve with backtracking + MRV + forward checking.
        Returns dict cell->value or None if unsatisfiable or timeout.
        """
        # initialize domains
        domains: Dict[Cell, Set[int]] = {}
        for r in range(self.rows):
            for c in range(self.cols):
                cell = (r,c)
                if cell not in self.cell_region:
                    # cell not part of any region (shouldn't happen) -> domain {0}
                    domains[cell] = set()
                    continue
                rid = self.cell_region[cell]
                maxv = self.region_size[rid]
                if cell in self.givens:
                    domains[cell] = {self.givens[cell]}
                else:
                    domains[cell] = set(range(1, maxv+1))

        # apply initial forward reductions from givens
        assignment: Dict[Cell,int] = dict(self.givens)
        # remove conflicting values from domains caused by givens
        for cell, val in list(self.givens.items()):
            # neighbors cannot have same val
            for nb in self.neighbors[cell]:
                if val in domains.get(nb, set()):
                    domains[nb].discard(val)
            # region mates cannot have same val
            rid = self.cell_region[cell]
            for mate in self.regions[rid]:
                if mate != cell and val in domains.get(mate, set()):
                    domains[mate].discard(val)

        nodes = 0
        start_time = time.time()

        # helper functions
        def unassigned_cells():
            return [cell for r in range(self.rows) for c in range(self.cols)
                    if (r,c) in self.cell_region and (r,c) not in assignment]

        def select_unassigned_mrv():
            # MRV: smallest domain size (>0), tie-breaker degree (most neighbors unassigned)
            best = None
            best_size = 10**9
            best_deg = -1
            for cell in unassigned_cells():
                d = domains[cell]
                if len(d) < best_size:
                    best_size = len(d)
                    best = cell
                    # compute degree
                    deg = sum(1 for nb in self.neighbors[cell] if nb in self.cell_region and nb not in assignment)
                    best_deg = deg
                elif len(d) == best_size:
                    deg = sum(1 for nb in self.neighbors[cell] if nb in self.cell_region and nb not in assignment)
                    if deg > best_deg:
                        best = cell
                        best_deg = deg
            return best

        def region_assigned_values(rid: int):
            vals = set()
            for cell in self.regions[rid]:
                if cell in assignment:
                    vals.add(assignment[cell])
            return vals

        def consistent(cell: Cell, value: int) -> bool:
            # region uniqueness
            rid = self.cell_region[cell]
            if value in region_assigned_values(rid):
                return False
            # adjacency (incl. diagonal)
            for nb in self.neighbors[cell]:
                if nb in assignment and assignment[nb] == value:
                    return False
            return True

        def forward_check(cell: Cell, value: int, removed: Dict[Cell, Set[int]]) -> bool:
            # remove value from domains of region mates and neighbors
            rid = self.cell_region[cell]
            # region mates
            for mate in self.regions[rid]:
                if mate == cell or mate in assignment: continue
                if value in domains[mate]:
                    domains[mate].remove(value)
                    removed.setdefault(mate, set()).add(value)
                    if not domains[mate]:
                        return False
            # neighbors
            for nb in self.neighbors[cell]:
                if nb in assignment: continue
                if value in domains.get(nb, set()):
                    domains[nb].remove(value)
                    removed.setdefault(nb, set()).add(value)
                    if not domains[nb]:
                        return False
            return True

        def restore(removed: Dict[Cell, Set[int]]):
            for cell, vals in removed.items():
                domains[cell].update(vals)

        sys.setrecursionlimit(10000)

        # order domain values: try smaller values first, optionally randomize tie order
        def order_domain(cell):
            vals = list(domains[cell])
            if randomize:
                random.shuffle(vals)
            else:
                vals.sort()
            return vals

        def backtrack():
            nonlocal nodes
            # timeout by node count
            nodes += 1
            if timeout_nodes and nodes > timeout_nodes:
                return None
            # optional time cutoff (safe guard)
            if time.time() - start_time > 30.0:  # 30s hard limit
                return None
            if len(assignment) == len([c for c in self.cell_region.keys()]):
                return dict(assignment)

            cell = select_unassigned_mrv()
            if cell is None:
                return None

            for val in order_domain(cell):
                if not consistent(cell, val):
                    continue
                assignment[cell] = val
                removed = {}
                ok = forward_check(cell, val, removed)
                if ok:
                    result = backtrack()
                    if result is not None:
                        return result
                restore(removed)
                del assignment[cell]
            return None

        result = backtrack()
        return result

def solve_puzzle(regions: Dict[int, List[Cell]], givens: Optional[Dict[Cell,int]] = None,
                 rows: Optional[int]=None, cols: Optional[int]=None, timeout_nodes: Optional[int]=None,
                 randomize: bool=False) -> Optional[Dict[Cell,int]]:
    """
    Wrapper utilitaire attendu par l'app.

    - regions: dict region_id -> list of (r,c)
    - givens: dict (r,c)->int (optionnel)
    - rows, cols: dimensions optionnelles
    - timeout_nodes: stop après N noeuds explorés (optionnel)
    - randomize: si True, ordre des valeurs aléatoire (utile pour générateur)

    Retour: dict (r,c)->value ou None si impossible / timeout
    """
    puzzle = SuguruPuzzle(regions, givens=givens, rows=rows, cols=cols)
    return puzzle.solve(timeout_nodes=timeout_nodes, randomize=randomize)

# quick CLI test when run directly
if __name__ == "__main__":
    # petit test 3x3 trivial
    regions = {
        0: [(0,0),(0,1)],
        1: [(0,2),(1,2)],
        2: [(1,0),(1,1),(2,0)],
        3: [(2,1),(2,2)]
    }
    givens = {}
    sol = solve_puzzle(regions, givens)
    print("Solution:", sol)
