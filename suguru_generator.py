# suguru_generator.py
from typing import List, Tuple, Dict
import random
from suguru_solver import SuguruPuzzle, Cell

def random_partition(rows:int, cols:int, max_region_size:int=5, seed=None):
    """
    Greedy random partition: create regions by growing blobs of random sizes.
    Returns dict region_id -> list of cells
    """
    if seed is not None:
        random.seed(seed)
    cells = [(r,c) for r in range(rows) for c in range(cols)]
    unassigned = set(cells)
    regions = {}
    rid = 0
    # Pre-generate target sizes until we fill grid
    while unassigned:
        start = random.choice(list(unassigned))
        # pick a size based on remaining cells
        max_size = min(max_region_size, len(unassigned))
        size = random.choice([1,2,3,4,5][:max_size])
        # BFS-like grow
        region = [start]
        frontier = [start]
        unassigned.remove(start)
        while len(region) < size and frontier:
            cell = random.choice(frontier)
            r,c = cell
            neighbors = []
            for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]: # 4-way expand for nicer shapes
                nr, nc = r+dr, c+dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if (nr,nc) in unassigned and (nr,nc) not in region:
                        neighbors.append((nr,nc))
            if not neighbors:
                frontier.remove(cell)
                continue
            nxt = random.choice(neighbors)
            region.append(nxt)
            frontier.append(nxt)
            unassigned.remove(nxt)
        regions[rid] = region
        rid += 1
    return regions

def generate_puzzle(rows:int=8, cols:int=8, max_region_size:int=5, max_tries:int=1000, seed=None):
    """
    Génère une grille Suguru valide aléatoire.
    Retourne (regions, solution, givens).
    En cas d'échec, retourne None au lieu de lever une exception.
    """
    if seed is not None:
        random.seed(seed)

    for attempt in range(max_tries):
        regions = random_partition(rows, cols, max_region_size)
        puzzle = SuguruPuzzle(rows, cols, regions, givens={})
        solution = puzzle.solve(timeout_nodes=200000)
        if solution:
            # créer les "givens" : une case révélée par région
            givens = {}
            for rid, cells in regions.items():
                cell = random.choice(cells)
                givens[cell] = solution[cell]
            return regions, solution, givens

    # si aucune grille valide n’a été générée après max_tries
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
