"""
=============================================================
  Vigilância de Partições Retangulares
  Passo 2c — OR-Tools (generalizado) + exportação para Prolog
  MAD 2025/2026
=============================================================

Funcionalidades:
  1. Resolve o problema exactamente com OR-Tools (ILP/CP-SAT)
  2. Exporta instâncias para ficheiro .pl legível pelo SWI-Prolog
  3. Compara ILP, CP-SAT e MAC+AC-3 para as mesmas instâncias

Uso:
    python ortools_prolog.py <ficheiro_resultado>
"""

import sys
import time
from collections import defaultdict


# =============================================================
#  LEITURA E GRAFO DE INCIDÊNCIA
# =============================================================

def parse_partition_file(filename):
    with open(filename) as f:
        tokens = f.read().split()
    idx = 0
    n_instances = int(tokens[idx]); idx += 1
    instances = []
    for _ in range(n_instances):
        n_rects = int(tokens[idx]); idx += 1
        rectangles = []
        for _ in range(n_rects):
            _fid = int(tokens[idx]); idx += 1
            nv   = int(tokens[idx]); idx += 1
            verts = []
            for _ in range(nv):
                x = int(tokens[idx]); idx += 1
                y = int(tokens[idx]); idx += 1
                verts.append((x, y))
            rectangles.append(verts)
        instances.append(rectangles)
    return instances


def build_incidence(rectangles):
    """
    Constrói grafo de incidência e numera vértices 0-based
    (necessário para Prolog e CP-SAT).

    Devolve:
        all_verts     : lista ordenada de coordenadas (índice → coords)
        vid           : dict coords → índice
        rect_corners  : list[list[int]]  (índices dos cantos de cada rect)
        vertex_to_rects: dict índice → set de rect IDs
    """
    all_verts_set = set()
    for verts in rectangles:
        all_verts_set.update(verts)
    all_verts = sorted(all_verts_set)
    vid       = {v: i for i, v in enumerate(all_verts)}

    rect_corners    = []
    vertex_to_rects = defaultdict(set)
    for r, verts in enumerate(rectangles):
        corners = [vid[v] for v in verts]
        rect_corners.append(corners)
        for vi in corners:
            vertex_to_rects[vi].add(r)

    return all_verts, vid, rect_corners, dict(vertex_to_rects)


# =============================================================
#  2c-A: OR-Tools ILP  (via pywraplp / SCIP)
# =============================================================

def solve_ilp(rect_corners, n_verts, target_rects=None):
    """
    Modelo ILP:
        min  sum_v x_v
        s.t. sum_{v in corners(r)} x_v >= 1   para cada r em target
             x_v in {0,1}
    """
    from ortools.linear_solver import pywraplp

    if target_rects is None:
        target_rects = list(range(len(rect_corners)))

    solver = pywraplp.Solver.CreateSolver('SCIP')
    x = [solver.IntVar(0, 1, f'x{v}') for v in range(n_verts)]

    for r in target_rects:
        solver.Add(sum(x[vi] for vi in rect_corners[r]) >= 1)

    solver.Minimize(sum(x))

    t0     = time.time()
    status = solver.Solve()
    elapsed = time.time() - t0

    if status == pywraplp.Solver.OPTIMAL:
        guards = [v for v in range(n_verts) if x[v].solution_value() > 0.5]
        return guards, elapsed
    return None, elapsed


# =============================================================
#  2c-B: OR-Tools CP-SAT  (Constraint Programming)
# =============================================================

def solve_cpsat(rect_corners, n_verts, target_rects=None):
    """
    Modelo CP-SAT:
        min  sum_v x_v
        s.t. sum_{v in corners(r)} x_v >= 1   para cada r em target
             x_v in {0,1}  (BoolVar)

    CP-SAT usa propagação de restrições internamente,
    sendo conceptualmente próximo do MAC+AC-3.
    """
    from ortools.sat.python import cp_model

    if target_rects is None:
        target_rects = list(range(len(rect_corners)))

    model = cp_model.CpModel()
    x     = [model.NewBoolVar(f'x{v}') for v in range(n_verts)]

    for r in target_rects:
        model.Add(sum(x[vi] for vi in rect_corners[r]) >= 1)

    model.Minimize(sum(x))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0

    t0     = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - t0

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        guards = [v for v in range(n_verts) if solver.Value(x[v]) == 1]
        opt    = (status == cp_model.OPTIMAL)
        return guards, elapsed, opt
    return None, elapsed, False


# =============================================================
#  EXPORTAÇÃO PARA PROLOG
# =============================================================

def export_to_prolog(rectangles, instance_id, filename=None):
    """
    Gera um ficheiro .pl com factos rect/1 e nverts/1
    legíveis pelo guards_clpfd.pl.

    Formato:
        nverts(N).
        rect([v0,v1,v2,v3]).
        ...
    """
    all_verts, vid, rect_corners, _ = build_incidence(rectangles)
    n_verts = len(all_verts)

    if filename is None:
        filename = f"instancia_{instance_id}.pl"

    lines = [
        f"%% Instancia {instance_id}  gerada automaticamente",
        f"%% {len(rectangles)} retangulos, {n_verts} vertices",
        f"",
        f"nverts({n_verts}).",
        f"",
    ]
    for corners in rect_corners:
        lines.append(f"rect({corners}).")

    with open(filename, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    return filename, n_verts


# =============================================================
#  RELATÓRIO COMPARATIVO
# =============================================================

def print_report(i, n_rects, n_verts, results):
    print(f"\n{'='*62}")
    print(f"  Instancia {i}  |  {n_rects} retangulos  |  {n_verts} vertices")
    print(f"{'='*62}")
    print(f"  {'Metodo':<22} {'Guardas':>8} {'Óptimo':>8} {'Tempo(ms)':>12}")
    print(f"  {'-'*56}")
    for name, guards, optimal, elapsed_ms in results:
        g_str = str(len(guards)) if guards is not None else "—"
        o_str = "✓" if optimal else "?"
        print(f"  {name:<22} {g_str:>8} {o_str:>8} {elapsed_ms:>11.2f}")
    print(f"{'='*62}")


# =============================================================
#  PONTO DE ENTRADA
# =============================================================

def run(filename):
    instances = parse_partition_file(filename)
    print(f"\nFicheiro  : {filename}")
    print(f"Instâncias: {len(instances)}")

    for i, rectangles in enumerate(instances):
        all_verts, vid, rect_corners, v2r = build_incidence(rectangles)
        n_verts = len(all_verts)
        n_rects = len(rectangles)

        # --- ILP (SCIP) ---
        t0 = time.time()
        g_ilp, t_ilp = solve_ilp(rect_corners, n_verts)
        ilp_ok = g_ilp is not None

        # --- CP-SAT ---
        g_cp, t_cp, cp_opt = solve_cpsat(rect_corners, n_verts)

        results = [
            ("ILP  (SCIP)",    g_ilp, ilp_ok,  t_ilp * 1000),
            ("CP-SAT",         g_cp,  cp_opt,   t_cp  * 1000),
        ]

        print_report(i+1, n_rects, n_verts, results)

        # --- Exportar para Prolog ---
        pl_file, _ = export_to_prolog(rectangles, i+1)
        print(f"  Exportado para Prolog: {pl_file}")

        # --- Mostrar solução ---
        if g_ilp:
            coords = sorted(all_verts[vi] for vi in g_ilp)
            print(f"  Guardas ILP : {coords}")
        if g_cp:
            coords_cp = sorted(all_verts[vi] for vi in g_cp)
            print(f"  Guardas CP  : {coords_cp}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ortools_prolog.py <ficheiro_resultado>")
        sys.exit(1)
    run(sys.argv[1])