# suguru_solver.py
from typing import List, Tuple, Dict, Optional, Set
import random
import copy

Cell = Tuple[int,int]

class SuguruPuzzle:
    def __init__(self, rows:int, cols:int, regions:Dict[int, List[Cell]], givens:Dict[Cell,int]=None):
        """
        regions: mapping region_id -> list of (r,c)
        givens: mapping (r,c) -> value for prefilled cells (optional)
        """
        self.rows = rows
        self.cols = cols
        self.regions = regions
        # cell -> region id
        self.cell_region = {}
        for rid, cells in regions.items():
            for cell in cells:
                self.cell_region[cell] = rid
        self.region_size = {rid: len(cells) for rid,cells in regions.items()}
        self.givens = givens or {}
        # neighbors (8-direction)
        self.neighbors = {}
        for r in range(rows):
            for c in range(cols):
                neigh = []
                for dr in (-1,0,1):
                    for dc in (-1,0,1):
                        if dr==0 and dc==0: continue
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            neigh.append((nr,nc))
                self.neighbors[(r,c)] = neigh

    def solve(self, timeout_nodes:Optional[int]=None) -> Optional[Dict[Cell,int]]:
        """
        Returns a solution mapping cell->value or None if unsat.
        Uses backtracking with MRV + forward checking.
        """
        # domains
        domains: Dict[Cell, Set[int]] = {}
        for r in range(self.rows):
            for c in range(self.cols):
                cell = (r,c)
                rid = self.cell_region[cell]
                maxv = self.region_size[rid]
                if cell in self.givens:
                    domains[cell] = {self.givens[cell]}
                else:
                    domains[cell] = set(range(1, maxv+1))
        # enforce region all-different: we handle by constraints during assign

        assignment: Dict[Cell,int] = dict(self.givens)
        nodes = 0

        def select_unassigned():
            # MRV: choose cell with smallest domain >1 and unassigned
            mcell = None
            msize = 100000
            for r in range(self.rows):
                for c in range(self.cols):
                    cell = (r,c)
                    if cell in assignment: continue
                    d = domains[cell]
                    if len(d) < msize:
                        msize = len(d)
                        mcell = cell
            return mcell

        # helper to check region uniqueness
        def region_values(rid):
            vals = set()
            for cell in self.regions[rid]:
                if cell in assignment:
                    vals.add(assignment[cell])
            return vals

        def consistent(cell, val):
            # region uniqueness
            rid = self.cell_region[cell]
            if val in region_values(rid):
                return False
            # adjacency constraint: neighbors cannot have same value
            for nb in self.neighbors[cell]:
                if nb in assignment and assignment[nb] == val:
                    return False
            return True

        def forward_check(cell, val, removed):
            # removed is dict cell -> set(removed_values)
            # remove val from neighbors' domains if conflict allowed
            # also remove values already in region from other cells' domains
            rid = self.cell_region[cell]
            # remove from region mates
            for mate in self.regions[rid]:
                if mate in assignment or mate == cell: continue
                if val in domains[mate]:
                    domains[mate].remove(val)
                    removed.setdefault(mate, set()).add(val)
                    if not domains[mate]:
                        return False
            # adjacency: a neighbor cannot have this value
            for nb in self.neighbors[cell]:
                if nb in assignment: continue
                if val in domains[nb]:
                    domains[nb].remove(val)
                    removed.setdefault(nb, set()).add(val)
                    if not domains[nb]:
                        return False
            return True

        def restore(removed):
            for cell, vals in removed.items():
                domains[cell].update(vals)

        def backtrack():
            nonlocal nodes
            nodes += 1
            if timeout_nodes and nodes > timeout_nodes:
                return None
            if len(assignment) == self.rows*self.cols:
                return dict(assignment)
            cell = select_unassigned()
            if cell is None:
                return None
            # order domain - try random order to diversify generator
            for val in sorted(domains[cell], key=lambda x: random.random()):
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

        return backtrack()
