"""
=============================================================
  Vigilância de Partições Retangulares
  Passo 4 — Extensões
  MAD 2025/2026
=============================================================

4a. Guardas com cores
    — Dois guardas que vêem o mesmo retângulo devem ter cores
      distintas. Modela como coloração do grafo de conflito.
    — Para o número mínimo de guardas, qual o mínimo de cores?
    — ILP + CP-SAT + algoritmo de coloração greedy.

4b. Guardas com alcance D
    — Um guarda em v cobre todos os retângulos a distância
      (no grafo de incidência) ≤ D.
    — D=0: só os retângulos incidentes em v (comportamento base).
    — Resolve com ILP para qualquer D.

Uso:
    python extensions.py <ficheiro_resultado> [D]

Exemplo (alcance D=2):
    python extensions.py resultado.txt 2
"""

import sys
import time
from collections import defaultdict, deque
from itertools import combinations


# =============================================================
#  LEITURA E ESTRUTURAS BASE  (reutilizadas de passos anteriores)
# =============================================================

def parse_partition_file(filename):
    with open(filename) as f:
        tokens = f.read().split()
    idx = 0
    n_inst = int(tokens[idx]); idx += 1
    instances = []
    for _ in range(n_inst):
        n_rects = int(tokens[idx]); idx += 1
        rects = []
        for _ in range(n_rects):
            _fid = int(tokens[idx]); idx += 1
            nv   = int(tokens[idx]); idx += 1
            vs   = []
            for _ in range(nv):
                x = int(tokens[idx]); idx += 1
                y = int(tokens[idx]); idx += 1
                vs.append((x, y))
            rects.append(vs)
        instances.append(rects)
    return instances


def build_incidence(rectangles):
    """
    Constrói o grafo de incidência.
    Devolve:
      all_verts   : lista ordenada de coordenadas (índice → coords)
      vid         : dict coords → índice
      v2r         : dict vi → set de IDs de retângulos (alcance base D=0)
      r2v         : dict r  → list de índices de vértices
    """
    vset = set()
    for vs in rectangles:
        vset.update(vs)
    all_verts = sorted(vset)
    vid       = {v: i for i, v in enumerate(all_verts)}

    v2r = defaultdict(set)
    r2v = {}
    for r, vs in enumerate(rectangles):
        corners = [vid[v] for v in vs]
        r2v[r]  = corners
        for vi in corners:
            v2r[vi].add(r)

    return all_verts, vid, dict(v2r), r2v


# =============================================================
#  PASSO 4b — GRAFO DE INCIDÊNCIA COM ALCANCE D
# =============================================================

def build_incidence_graph(v2r, r2v):
    """
    Constrói o grafo de incidência bipartido completo como
    estrutura de adjacência, para permitir BFS de profundidade D.

    Nós do grafo:
      - Vértices da partição: nó tipo 'v', índice vi
      - Retângulos: nó tipo 'r', índice r

    Arestas: (v, r) se vi é canto de r.

    Devolve adj_v[vi] = list de r adjacentes
             adj_r[r] = list de vi adjacentes
    """
    n_verts = max(v2r.keys()) + 1 if v2r else 0
    n_rects = max(r2v.keys()) + 1 if r2v else 0

    adj_v = {vi: list(v2r[vi]) for vi in v2r}
    adj_r = {r:  list(r2v[r])  for r in r2v}

    return adj_v, adj_r


def coverage_at_distance(vi, D, adj_v, adj_r):
    """
    BFS no grafo de incidência bipartido.
    Devolve o conjunto de retângulos alcançáveis a partir do
    vértice vi percorrendo no máximo D arestas.

    Distância 1: retângulos incidentes em vi  (= comportamento base)
    Distância 2: vértices dos retângulos de dist 1 → rects desses vértices
    Distância k: alterna vértice ↔ retângulo

    Parâmetro D refere-se a distância no grafo:
      D=0 → apenas os retângulos directamente incidentes (sem BFS extra)
      D=1 → idem (1 aresta v→r)
      D=2 → rects incidentes + rects dos vértices vizinhos
    """
    if D <= 0:
        return set(adj_v.get(vi, []))

    visited_v = {vi}
    visited_r = set()
    queue     = deque()

    # Inicializar com os retângulos directamente incidentes
    for r in adj_v.get(vi, []):
        if r not in visited_r:
            visited_r.add(r)
            queue.append(('r', r, 1))  # (tipo, id, distância)

    while queue:
        kind, node_id, dist = queue.popleft()

        if kind == 'r':
            # Expandir para vértices adjacentes ao retângulo
            if dist < D:
                for vj in adj_r.get(node_id, []):
                    if vj not in visited_v:
                        visited_v.add(vj)
                        queue.append(('v', vj, dist))
        else:
            # kind == 'v': expandir para retângulos adjacentes ao vértice
            for r in adj_v.get(node_id, []):
                if r not in visited_r:
                    visited_r.add(r)
                    if dist + 1 <= D:
                        queue.append(('r', r, dist + 1))

    return visited_r


def build_extended_v2r(v2r, r2v, D):
    """
    Constrói v2r_D[vi] = conjunto de retângulos cobertos por vi
    com alcance D.
    """
    adj_v, adj_r = build_incidence_graph(v2r, r2v)
    v2r_D = {}
    for vi in v2r:
        v2r_D[vi] = coverage_at_distance(vi, D, adj_v, adj_r)
    return v2r_D


# =============================================================
#  ILP GERAL  (usado por 4a e 4b)
# =============================================================

def solve_ilp_coverage(v2r_extended, r2v, target_rects=None):
    """
    ILP de cobertura com v2r_extended (pode ter alcance D>0).

    min  sum_v x_v
    s.t. sum_{v: r in v2r_extended[v]} x_v >= 1   para r em target
         x_v in {0,1}
    """
    from ortools.linear_solver import pywraplp

    if target_rects is None:
        target_rects = set(r2v.keys())

    solver = pywraplp.Solver.CreateSolver('SCIP')
    verts  = list(v2r_extended.keys())
    x      = {vi: solver.IntVar(0, 1, f'x{vi}') for vi in verts}

    # Para cada retângulo, quais os guardas que o cobrem?
    r_covered_by = defaultdict(list)
    for vi, rects in v2r_extended.items():
        for r in rects:
            r_covered_by[r].append(vi)

    for r in target_rects:
        coverers = r_covered_by.get(r, [])
        if not coverers:
            print(f"    AVISO: retângulo {r} não tem cobertura possível!")
            return None, 0
        solver.Add(sum(x[vi] for vi in coverers) >= 1)

    solver.Minimize(sum(x.values()))
    t0     = time.time()
    status = solver.Solve()
    elapsed = time.time() - t0

    if status == pywraplp.Solver.OPTIMAL:
        guards = [vi for vi in verts if x[vi].solution_value() > 0.5]
        return guards, elapsed
    return None, elapsed


# =============================================================
#  PASSO 4a — GUARDAS COM CORES
# =============================================================

# -----------------------------------------------------------
#  4a-1. Grafo de conflito
# -----------------------------------------------------------

def build_conflict_graph(guards, v2r_extended):
    """
    Dois guardas conflituam se cobrem pelo menos um retângulo
    em comum.

    Devolve:
      conflict_edges : set de pares (vi, vj) ordenados
      adj            : dict vi → set de vj em conflito
    """
    conflict_edges = set()
    adj            = defaultdict(set)

    guard_set = set(guards)
    for vi in guards:
        for vj in guards:
            if vi >= vj:
                continue
            # conflito se partilham pelo menos um retângulo coberto
            if v2r_extended[vi] & v2r_extended[vj]:
                conflict_edges.add((vi, vj))
                adj[vi].add(vj)
                adj[vj].add(vi)

    return conflict_edges, dict(adj)


# -----------------------------------------------------------
#  4a-2. Coloração Greedy (DSATUR)
# -----------------------------------------------------------

def color_dsatur(guards, adj):
    """
    Algoritmo DSATUR para coloração do grafo de conflito.
    A cada passo escolhe o vértice com maior grau de saturação
    (número de cores distintas nos vizinhos).

    Devolve:
      coloring : dict vi → cor (inteiro 0-based)
      n_colors : número de cores usadas
    """
    if not guards:
        return {}, 0

    coloring   = {}
    saturation = defaultdict(set)   # vi → conjunto de cores dos vizinhos
    degree     = {vi: len(adj.get(vi, set())) for vi in guards}

    uncolored = set(guards)

    while uncolored:
        # Escolher vértice com maior saturação; desempate por grau
        vi = max(uncolored,
                 key=lambda v: (len(saturation[v]), degree[v]))

        # Menor cor disponível
        used_by_neighbors = saturation[vi]
        color = 0
        while color in used_by_neighbors:
            color += 1

        coloring[vi] = color
        uncolored.discard(vi)

        # Actualizar saturação dos vizinhos
        for vj in adj.get(vi, set()):
            saturation[vj].add(color)

    n_colors = max(coloring.values()) + 1 if coloring else 0
    return coloring, n_colors


# -----------------------------------------------------------
#  4a-3. Coloração exacta por ILP
# -----------------------------------------------------------

def solve_coloring_ilp(guards, adj, n_colors_ub):
    """
    ILP para coloração mínima do grafo de conflito.

    Variáveis:
      x[vi][c] = 1 se guarda vi tem cor c
      y[c]     = 1 se cor c é usada

    min  sum_c y[c]
    s.t. sum_c x[vi][c] = 1          ∀ vi
         x[vi][c] + x[vj][c] <= 1   ∀ (vi,vj) em conflito, ∀ c
         x[vi][c] <= y[c]            ∀ vi, c
         y[c] in {0,1}, x[vi][c] in {0,1}
    """
    from ortools.linear_solver import pywraplp

    if not guards:
        return {}, 0, 0

    C      = list(range(n_colors_ub))   # cores possíveis
    solver = pywraplp.Solver.CreateSolver('SCIP')

    x = {(vi, c): solver.IntVar(0, 1, f'x{vi}_{c}')
         for vi in guards for c in C}
    y = {c: solver.IntVar(0, 1, f'y{c}') for c in C}

    # Cada guarda tem exactamente uma cor
    for vi in guards:
        solver.Add(sum(x[vi, c] for c in C) == 1)

    # Guardas em conflito têm cores distintas
    for vi in guards:
        for vj in adj.get(vi, set()):
            if vi < vj:
                for c in C:
                    solver.Add(x[vi, c] + x[vj, c] <= 1)

    # y[c] = 1 se algum guarda usa cor c
    for vi in guards:
        for c in C:
            solver.Add(x[vi, c] <= y[c])

    solver.Minimize(sum(y.values()))

    t0     = time.time()
    status = solver.Solve()
    elapsed = time.time() - t0

    if status == pywraplp.Solver.OPTIMAL:
        coloring = {}
        for vi in guards:
            for c in C:
                if x[vi, c].solution_value() > 0.5:
                    coloring[vi] = c
                    break
        n_colors = int(sum(y[c].solution_value() for c in C))
        return coloring, n_colors, elapsed

    return {}, n_colors_ub, elapsed


# -----------------------------------------------------------
#  4a-4. Análise completa: mínimo guardas → mínimo cores
# -----------------------------------------------------------

def analyse_coloring(guards, v2r_extended, all_verts, label=""):
    """
    Para um conjunto de guardas dado:
      1. Constrói o grafo de conflito
      2. Aplica DSATUR (heurístico)
      3. Aplica ILP de coloração (exacto)
      4. Imprime resumo
    """
    print(f"\n  {label}")
    print(f"    Guardas       : {len(guards)}")

    if not guards:
        print("    (sem guardas)")
        return

    edges, adj = build_conflict_graph(guards, v2r_extended)
    print(f"    Arestas conflito: {len(edges)}")

    # DSATUR
    col_ds, nc_ds = color_dsatur(guards, adj)
    print(f"    Cores DSATUR  : {nc_ds}")

    # ILP de coloração (upper bound = nc_ds)
    col_ilp, nc_ilp, t_col = solve_coloring_ilp(guards, adj, nc_ds + 1)
    print(f"    Cores ILP     : {nc_ilp}  (tempo: {t_col*1000:.1f} ms)")

    # Mostrar atribuição
    coloring = col_ilp if col_ilp else col_ds
    by_color = defaultdict(list)
    for vi, c in coloring.items():
        by_color[c].append(all_verts[vi])
    for c in sorted(by_color):
        print(f"      Cor {c}: {sorted(by_color[c])}")

    return nc_ilp


# =============================================================
#  PASSO 4b — GUARDAS COM ALCANCE D
# =============================================================

def analyse_range(rectangles, all_verts, v2r, r2v, D_values,
                  target_rects=None):
    """
    Para cada valor de D em D_values:
      1. Constrói v2r_D com alcance D
      2. Resolve o ILP de cobertura
      3. Imprime número de guardas necessários

    Permite observar como o número de guardas diminui com D.
    """
    if target_rects is None:
        target_rects = set(r2v.keys())

    print(f"\n  Impacto do alcance D no número de guardas")
    print(f"  {'D':>5}  {'Guardas':>8}  {'Tempo(ms)':>12}  {'Redução':>10}")
    print(f"  {'-'*42}")

    base_cost = None
    results   = []

    for D in D_values:
        v2r_D      = build_extended_v2r(v2r, r2v, D)
        guards, elapsed = solve_ilp_coverage(v2r_D, r2v, target_rects)
        cost = len(guards) if guards is not None else float('inf')

        if base_cost is None:
            base_cost = cost
            red_str = "—"
        else:
            reduction = base_cost - cost
            red_str   = f"-{reduction}" if reduction > 0 else "0"

        print(f"  {D:>5}  {cost:>8}  {elapsed*1000:>11.1f}  {red_str:>10}")
        results.append((D, guards, cost, elapsed))

    return results


# =============================================================
#  PONTO DE ENTRADA
# =============================================================

def run(filename, D_max=3):
    instances = parse_partition_file(filename)
    print(f"\nFicheiro  : {filename}")
    print(f"Instâncias: {len(instances)}\n")

    for i, rectangles in enumerate(instances):
        all_verts, vid, v2r, r2v = build_incidence(rectangles)
        n_rects = len(rectangles)
        n_verts = len(all_verts)

        print(f"{'='*62}")
        print(f"  Instância {i+1}  |  {n_rects} retângulos  |  {n_verts} vértices")
        print(f"{'='*62}")

        # -------------------------------------------------------
        #  4a — Guardas com Cores
        # -------------------------------------------------------
        print("\n  ── EXTENSÃO 4a: GUARDAS COM CORES ──")

        # Solução de referência: ILP sem cores (D=0, cobertura base)
        guards_base, t_base = solve_ilp_coverage(v2r, r2v)

        if guards_base is not None:
            print(f"\n  Solução base (sem cores): {len(guards_base)} guardas")

            # Análise de coloração para a solução mínima
            nc = analyse_coloring(guards_base, v2r, all_verts,
                                  label="Coloração da solução mínima")

            # Verificar se existe solução com mesmo número de guardas
            # mas que necessita de menos cores
            print(f"\n  → Para {len(guards_base)} guardas, "
                  f"são necessárias pelo menos {nc} cores.")

        # -------------------------------------------------------
        #  4b — Guardas com Alcance D
        # -------------------------------------------------------
        print(f"\n  ── EXTENSÃO 4b: GUARDAS COM ALCANCE D ──")

        D_values = list(range(0, D_max + 1))
        results_D = analyse_range(rectangles, all_verts, v2r, r2v, D_values)

        # Mostrar as posições para o maior D testado
        D_best, guards_D, cost_D, _ = results_D[-1]
        if guards_D:
            coords_D = sorted(all_verts[vi] for vi in guards_D)
            print(f"\n  Guardas com D={D_best}: {coords_D}")

            # Coloração para a solução com maior alcance
            v2r_Dmax = build_extended_v2r(v2r, r2v, D_best)
            print()
            analyse_coloring(guards_D, v2r_Dmax, all_verts,
                             label=f"Coloração com alcance D={D_best}")

        print()


# =============================================================
#  DEMO EMBUTIDA
# =============================================================

def demo():
    print("\n" + "="*62)
    print("  DEMONSTRAÇÃO — Extensões 4a e 4b")
    print("  Partição 3x3 (9 retângulos)")
    print("="*62)

    # Grelha 3×3
    rects = []
    for row in range(3):
        for col in range(3):
            rects.append([
                (col,   row),
                (col+1, row),
                (col+1, row+1),
                (col,   row+1),
            ])

    all_verts, vid, v2r, r2v = build_incidence(rects)

    print(f"\n  {len(rects)} retângulos  |  {len(all_verts)} vértices")

    # --- 4a ---
    print("\n  ── 4a: GUARDAS COM CORES ──")
    guards_base, _ = solve_ilp_coverage(v2r, r2v)
    if guards_base:
        print(f"\n  Solução mínima: {len(guards_base)} guardas")
        coords_b = sorted(all_verts[vi] for vi in guards_base)
        print(f"  Posições: {coords_b}")
        nc = analyse_coloring(guards_base, v2r, all_verts,
                              label="Coloração")
        print(f"\n  → {len(guards_base)} guardas precisam de {nc} cores.")

    # --- 4b ---
    print("\n  ── 4b: ALCANCE D ──")
    results = analyse_range(rects, all_verts, v2r, r2v,
                            D_values=[0, 1, 2, 3])

    # Detalhar D=2
    print("\n  Detalhe de cobertura com D=2:")
    v2r_2 = build_extended_v2r(v2r, r2v, 2)
    for vi in sorted(v2r_2)[:5]:
        print(f"    Vértice {all_verts[vi]}: cobre retângulos {sorted(v2r_2[vi])}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        demo()
    else:
        filename = sys.argv[1]
        D_max    = int(sys.argv[2]) if len(sys.argv) >= 3 else 3
        run(filename, D_max)