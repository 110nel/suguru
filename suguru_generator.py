# suguru_generator.py
from typing import List, Tuple, Dict
import random
from suguru_solver import SuguruPuzzle, Cell
from collections import defaultdict
from copy import deepcopy

class SuguruPuzzle:
    """Classe minimaliste pour gérer la grille Suguru et le solveur."""
    def __init__(self, rows, cols, regions, givens={}):
        self.rows = rows
        self.cols = cols
        self.regions = regions  # dict: region_id -> list of (r,c)
        self.givens = givens
        self.grid = [[0]*cols for _ in range(rows)]
        for (r,c), v in givens.items():
            self.grid[r][c] = v

    def is_valid(self, r, c, val):
        # Vérifie ligne, colonne et région
        for i in range(self.cols):
            if self.grid[r][i] == val:
                return False
        for i in range(self.rows):
            if self.grid[i][c] == val:
                return False
        # Vérifie la région
        for rid, cells in self.regions.items():
            if (r,c) in cells:
                for (rr,cc) in cells:
                    if self.grid[rr][cc] == val:
                        return False
        return True

    def solve_region(self, cells, idx=0):
        if idx >= len(cells):
            return True
        r,c = cells[idx]
        max_val = len(cells)
        for val in range(1, max_val+1):
            if self.is_valid(r, c, val):
                self.grid[r][c] = val
                if self.solve_region(cells, idx+1):
                    return True
                self.grid[r][c] = 0
        return False

    def solve(self, timeout_nodes=200000):
        # Remplit toutes les régions une par une
        for rid, cells in self.regions.items():
            if not self.solve_region(cells):
                return None
        solution = {}
        for r in range(self.rows):
            for c in range(self.cols):
                solution[(r,c)] = self.grid[r][c]
        return solution
        
        
def random_partition(rows, cols, max_region_size):
    """Génère une partition aléatoire simple en backtracking pour toutes les cellules"""
    cells = [(r,c) for r in range(rows) for c in range(cols)]
    random.shuffle(cells)
    regions = {}
    region_id = 0

    def neighbors(cell, taken):
        r,c = cell
        nbrs = [(r+dr,c+dc) for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]]
        return [n for n in nbrs if n in cells and n not in taken]

    while cells:
        start = cells.pop()
        group = [start]
        frontier = [start]
        while len(group) < max_region_size and frontier:
            f = frontier.pop()
            for n in neighbors(f, group):
                if n not in group:
                    group.append(n)
                    frontier.append(n)
                    if len(group) >= max_region_size:
                        break
        for g in group:
            if g in cells:
                cells.remove(g)
        regions[region_id] = group
        region_id += 1
    return regions

def generate_puzzle(rows:int=8, cols:int=8, max_region_size:int=5, max_tries:int=10000, seed=None):
    """
    Génère une grille Suguru valide en utilisant backtracking robuste.
    Retourne (regions, solution, givens) ou None si impossible.
    """
    if seed is not None:
        random.seed(seed)

    for attempt in range(max_tries):
        regions = random_partition(rows, cols, max_region_size)
        puzzle = SuguruPuzzle(rows, cols, regions, givens={})
        solution = puzzle.solve()
        if solution:
            # créer les "givens" : une case par région
            givens = {}
            for rid, cells in regions.items():
                cell = random.choice(cells)
                givens[cell] = solution[cell]
            return regions, solution, givens

    print(f"[Warning] Failed to generate puzzle after {max_tries} tries.")
    return None

# small CLI test
if __name__ == "__main__":
    r,c = 8,8
    regions, sol, givens = generate_puzzle(r,c, max_region_size=5, seed=42)
    print("Regions:", {k:len(v) for k,v in regions.items()})
    print("Givens count:", len(givens))
    # print solution grid
    grid = [[sol[(i,j)] for j in range(c)] for i in range(r)]
    for row in grid:
        print(" ".join(str(x) for x in row))
