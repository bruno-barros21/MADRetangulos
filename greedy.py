"""
=============================================================
  Vigilância de Partições Retangulares — Estratégias Greedy
  MAD 2025/2026
=============================================================

Lê o ficheiro de saída do rectParts.c e aplica estratégias
greedy para colocação mínima de guardas.

Formato do ficheiro de entrada (saída do rectParts.c):
    s                              ← número de instâncias
    nr                             ← número de retângulos
    f nv x1 y1 x2 y2 x3 y3 x4 y4  ← face f com nv vértices
    ...

Uso:
    python greedy_guards.py <ficheiro_resultado> [cobertura_parcial_%]

Exemplo (cobertura total):
    python greedy_guards.py resultado.txt

Exemplo (cobrir apenas 70% dos retângulos):
    python greedy_guards.py resultado.txt 70
"""

import sys
import time
from collections import defaultdict


# =============================================================
#  1. LEITURA DO FICHEIRO
# =============================================================

def parse_partition_file(filename):
    """
    Lê o ficheiro de saída do rectParts.c.
    Devolve lista de instâncias; cada instância é uma lista de
    retângulos, onde cada retângulo é um conjunto de vértices (x,y).
    """
    instances = []
    with open(filename) as f:
        tokens = f.read().split()

    idx = 0
    n_instances = int(tokens[idx]); idx += 1

    for _ in range(n_instances):
        n_rects = int(tokens[idx]); idx += 1
        rectangles = []
        for _ in range(n_rects):
            face_id  = int(tokens[idx]); idx += 1
            nv       = int(tokens[idx]); idx += 1
            verts = []
            for _ in range(nv):
                x = int(tokens[idx]); idx += 1
                y = int(tokens[idx]); idx += 1
                verts.append((x, y))
            rectangles.append(verts)
        instances.append(rectangles)

    return instances


# =============================================================
#  2. GRAFO DE INCIDÊNCIA
# =============================================================

def build_incidence(rectangles):
    """
    Constrói o grafo de incidência bipartido:
      vertex_to_rects[v] = conjunto de índices de retângulos que v cobre
      rect_to_verts[r]   = conjunto de vértices do retângulo r
    """
    vertex_to_rects = defaultdict(set)  # (x,y) → {r0, r1, ...}
    rect_to_verts   = {}                # r → {(x,y), ...}

    for r_idx, verts in enumerate(rectangles):
        rect_to_verts[r_idx] = set(verts)
        for v in verts:
            vertex_to_rects[v].add(r_idx)

    return vertex_to_rects, rect_to_verts


# =============================================================
#  3. ESTRATÉGIAS GREEDY
# =============================================================

# -----------------------------------------------------------
#  3.1  Greedy por Cobertura Máxima  (Maximum Coverage Greedy)
# -----------------------------------------------------------
def greedy_max_coverage(vertex_to_rects, rect_to_verts,
                        target_rects=None):
    """
    A cada passo escolhe o vértice que cobre o MAIOR número de
    retângulos ainda não cobertos.

    target_rects: conjunto de IDs de retângulos a cobrir;
                  None → cobertura total.

    Devolve:
        guards   — lista de vértices com guarda (em ordem de escolha)
        n_steps  — número de iterações
        coverage — número de retângulos cobertos
    """
    if target_rects is None:
        target_rects = set(rect_to_verts.keys())

    uncovered = set(target_rects)
    guards    = []
    n_steps   = 0

    while uncovered:
        best_v     = None
        best_gain  = -1

        # Para cada vértice, conta quantos retângulos em uncovered cobre
        # Optimização: só considerar vértices adjacentes a retângulos
        # ainda não cobertos
        candidates = set()
        for r in uncovered:
            for v in rect_to_verts[r]:
                candidates.add(v)

        for v in candidates:
            gain = len(vertex_to_rects[v] & uncovered)
            if gain > best_gain:
                best_gain = gain
                best_v    = v

        if best_v is None or best_gain == 0:
            break  # não há mais progressos possíveis

        guards.append(best_v)
        uncovered -= vertex_to_rects[best_v]
        n_steps   += 1

    coverage = len(target_rects) - len(uncovered)
    return guards, n_steps, coverage


# -----------------------------------------------------------
#  3.2  Greedy por Grau  (Degree-Sorted Greedy)
# -----------------------------------------------------------
def greedy_by_degree(vertex_to_rects, rect_to_verts,
                     target_rects=None):
    """
    Ordena os vértices por grau (número de retângulos que cobrem)
    de forma decrescente — ordem ESTÁTICA, calculada uma só vez.
    Percorre a lista e coloca guarda onde ainda haja retângulos
    não cobertos.

    Devolve:
        guards   — lista de vértices com guarda (em ordem de escolha)
        n_steps  — número de iterações sobre a lista
        coverage — número de retângulos cobertos
    """
    if target_rects is None:
        target_rects = set(rect_to_verts.keys())

    # Ordena por grau total decrescente (ordem estática)
    sorted_verts = sorted(vertex_to_rects.keys(),
                          key=lambda v: len(vertex_to_rects[v]),
                          reverse=True)

    uncovered = set(target_rects)
    guards    = []
    n_steps   = 0

    for v in sorted_verts:
        if not uncovered:
            break
        gain = len(vertex_to_rects[v] & uncovered)
        n_steps += 1
        if gain > 0:
            guards.append(v)
            uncovered -= vertex_to_rects[v]

    coverage = len(target_rects) - len(uncovered)
    return guards, n_steps, coverage


# -----------------------------------------------------------
#  3.3  Greedy Aleatório com Reinícios  (Randomised Greedy)
# -----------------------------------------------------------
import random

def greedy_random_restarts(vertex_to_rects, rect_to_verts,
                           target_rects=None, n_restarts=20,
                           seed=42):
    """
    Executa n_restarts vezes uma versão aleatória do greedy de
    cobertura máxima: em caso de empate no ganho, escolhe
    aleatoriamente entre os melhores candidatos.

    Devolve a melhor solução encontrada.
    """
    if target_rects is None:
        target_rects = set(rect_to_verts.keys())

    rng      = random.Random(seed)
    best     = None
    best_len = float('inf')

    for _ in range(n_restarts):
        uncovered = set(target_rects)
        guards    = []

        while uncovered:
            candidates = set()
            for r in uncovered:
                for v in rect_to_verts[r]:
                    candidates.add(v)

            best_gain = max(len(vertex_to_rects[v] & uncovered)
                            for v in candidates)
            top = [v for v in candidates
                   if len(vertex_to_rects[v] & uncovered) == best_gain]

            chosen = rng.choice(top)
            guards.append(chosen)
            uncovered -= vertex_to_rects[chosen]

        if len(guards) < best_len:
            best_len = len(guards)
            best     = guards[:]

    coverage = len(target_rects)
    return best, n_restarts, coverage


# =============================================================
#  4.  VERIFICAÇÃO DA SOLUÇÃO
# =============================================================

def verify(guards, rect_to_verts, vertex_to_rects,
           target_rects=None):
    """
    Verifica que todos os retângulos alvo ficam cobertos
    pelos guardas escolhidos.
    """
    if target_rects is None:
        target_rects = set(rect_to_verts.keys())

    covered = set()
    for v in guards:
        covered |= vertex_to_rects[v]

    missing = target_rects - covered
    return len(missing) == 0, missing


# =============================================================
#  5.  ILP (OR-Tools) — para comparação com o óptimo
# =============================================================

def solve_ilp(vertex_to_rects, rect_to_verts, target_rects=None):
    """
    Resolve o problema exactamente via ILP com OR-Tools (SCIP).
    Usado para calcular o gap das soluções greedy.
    """
    try:
        from ortools.linear_solver import pywraplp
    except ImportError:
        return None, None

    if target_rects is None:
        target_rects = set(rect_to_verts.keys())

    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return None, None

    # Variáveis: x[v] ∈ {0,1}
    verts = list(vertex_to_rects.keys())
    x = {v: solver.IntVar(0, 1, f'x_{v}') for v in verts}

    # Restrições: para cada retângulo alvo, ≥1 canto tem guarda
    for r in target_rects:
        corners = list(rect_to_verts[r])
        solver.Add(sum(x[v] for v in corners) >= 1)

    # Objectivo: minimizar número de guardas
    solver.Minimize(sum(x.values()))

    t0     = time.time()
    status = solver.Solve()
    t_ilp  = time.time() - t0

    if status == pywraplp.Solver.OPTIMAL:
        opt_guards = [v for v in verts if x[v].solution_value() > 0.5]
        return opt_guards, t_ilp
    return None, t_ilp


# =============================================================
#  6.  RELATÓRIO
# =============================================================

def print_report(instance_id, n_rects, results, opt_size=None):
    """
    Imprime tabela comparativa dos algoritmos.
    """
    print(f"\n{'='*65}")
    print(f"  Instância {instance_id}  |  {n_rects} retângulos")
    if opt_size is not None:
        print(f"  Óptimo ILP: {opt_size} guardas")
    print(f"{'='*65}")
    print(f"  {'Algoritmo':<30} {'Guardas':>8} {'Gap':>8} {'Tempo(ms)':>12}")
    print(f"  {'-'*58}")
    for name, guards, elapsed_ms, coverage in results:
        gap_str = "—"
        if opt_size is not None and opt_size > 0:
            gap = (len(guards) - opt_size) / opt_size * 100
            gap_str = f"{gap:+.1f}%"
        print(f"  {name:<30} {len(guards):>8} {gap_str:>8} {elapsed_ms:>11.2f}")
    print(f"{'='*65}")


# =============================================================
#  7.  PONTO DE ENTRADA
# =============================================================

def run(filename, partial_pct=None):
    """
    Executa todos os algoritmos em todas as instâncias do ficheiro.

    partial_pct: percentagem de retângulos a cobrir (cobertura parcial).
                 None → cobertura total.
    """
    instances = parse_partition_file(filename)
    print(f"\nFicheiro: {filename}")
    print(f"Instâncias: {len(instances)}")
    if partial_pct is not None:
        print(f"Modo: cobertura parcial ({partial_pct}% dos retângulos)")
    else:
        print("Modo: cobertura total")

    total_results = {
        'greedy_max' : [],
        'greedy_deg' : [],
        'greedy_rnd' : [],
        'ilp'        : [],
    }

    for i, rectangles in enumerate(instances):
        vertex_to_rects, rect_to_verts = build_incidence(rectangles)
        n_rects = len(rectangles)

        # --- Selecção do subconjunto alvo (cobertura parcial) ---
        if partial_pct is not None:
            n_target = max(1, int(n_rects * partial_pct / 100))
            # Escolhe os n_target retângulos de maior grau (mais difíceis)
            rects_by_degree = sorted(
                rect_to_verts.keys(),
                key=lambda r: min(len(vertex_to_rects[v])
                                  for v in rect_to_verts[r])
            )
            target_rects = set(rects_by_degree[:n_target])
        else:
            target_rects = None  # todos

        # --- Greedy 1: Cobertura Máxima ---
        t0 = time.time()
        g1, _, cov1 = greedy_max_coverage(vertex_to_rects,
                                          rect_to_verts, target_rects)
        t1 = (time.time() - t0) * 1000

        ok1, miss1 = verify(g1, rect_to_verts, vertex_to_rects, target_rects)
        if not ok1:
            print(f"  [AVISO] Greedy Max: {len(miss1)} retângulos não cobertos!")

        # --- Greedy 2: Por Grau ---
        t0 = time.time()
        g2, _, cov2 = greedy_by_degree(vertex_to_rects,
                                       rect_to_verts, target_rects)
        t2 = (time.time() - t0) * 1000

        ok2, miss2 = verify(g2, rect_to_verts, vertex_to_rects, target_rects)
        if not ok2:
            print(f"  [AVISO] Greedy Grau: {len(miss2)} retângulos não cobertos!")

        # --- Greedy 3: Aleatório com reinícios ---
        t0 = time.time()
        g3, _, cov3 = greedy_random_restarts(vertex_to_rects,
                                             rect_to_verts, target_rects,
                                             n_restarts=30)
        t3 = (time.time() - t0) * 1000

        ok3, miss3 = verify(g3, rect_to_verts, vertex_to_rects, target_rects)
        if not ok3:
            print(f"  [AVISO] Greedy Aleat.: {len(miss3)} retângulos não cobertos!")

        # --- ILP (opcional) ---
        t0 = time.time()
        g_ilp, t_ilp = solve_ilp(vertex_to_rects, rect_to_verts, target_rects)
        t_ilp_ms = (t_ilp or 0) * 1000
        opt_size = len(g_ilp) if g_ilp is not None else None

        results = [
            ("Greedy Cobertura Máxima",   g1, t1,      cov1),
            ("Greedy Por Grau (estático)", g2, t2,      cov2),
            ("Greedy Aleatório (×30)",     g3, t3,      cov3),
        ]
        if g_ilp is not None:
            results.append(("ILP (SCIP — óptimo)", g_ilp, t_ilp_ms,
                             len(target_rects or rect_to_verts)))

        print_report(i+1, n_rects, results, opt_size)

        # Acumular para estatísticas globais
        total_results['greedy_max'].append(len(g1))
        total_results['greedy_deg'].append(len(g2))
        total_results['greedy_rnd'].append(len(g3))
        if opt_size is not None:
            total_results['ilp'].append(opt_size)

    # --- Resumo global ---
    if len(instances) > 1:
        print(f"\n{'='*65}")
        print("  RESUMO GLOBAL")
        print(f"{'='*65}")
        for key, name in [('greedy_max', 'Greedy Cobertura Máxima'),
                           ('greedy_deg', 'Greedy Por Grau'),
                           ('greedy_rnd', 'Greedy Aleatório (×30)'),
                           ('ilp',        'ILP (óptimo)')]:
            vals = total_results[key]
            if vals:
                avg = sum(vals) / len(vals)
                print(f"  {name:<30}  média guardas: {avg:.2f}")
        print(f"{'='*65}\n")


# =============================================================
#  8.  DEMONSTRAÇÃO SEM FICHEIRO (instância embutida)
# =============================================================

def demo_embedded():
    """
    Demonstração com a instância do partsRects.py original,
    representada directamente como lista de retângulos (vértices).

    A instância tem 8 retângulos e 10 restrições no ILP original.
    Reconstruímos uma geometria plausível manualmente.
    """
    print("\n" + "="*65)
    print("  DEMONSTRAÇÃO — instância embutida (8 retângulos)")
    print("="*65)

    # Geometria:
    #  +-------+---+------+
    #  |       | 2 |  3   |
    #  |   1   +---+------+
    #  |       | 4 |  5   |
    #  +---+---+---+--+---+
    #  | 6 |   7   |  8   |
    #  +---+-------+------+
    #
    # Coordenadas dos vértices (col, linha):
    #   x: 0  2  3  5  7
    #   y: 0  1  3  4

    rectangles = [
        # (face_id não usado aqui — lista de vértices)
        [(0,1),(2,1),(2,4),(0,4)],  # r0: retângulo 1
        [(2,3),(3,3),(3,4),(2,4)],  # r1: retângulo 2
        [(3,3),(7,3),(7,4),(3,4)],  # r2: retângulo 3
        [(2,1),(3,1),(3,3),(2,3)],  # r3: retângulo 4
        [(3,1),(7,1),(7,3),(3,3)],  # r4: retângulo 5
        [(0,0),(2,0),(2,1),(0,1)],  # r5: retângulo 6
        [(2,0),(5,0),(5,1),(2,1)],  # r6: retângulo 7
        [(5,0),(7,0),(7,1),(5,1)],  # r7: retângulo 8
    ]

    vertex_to_rects, rect_to_verts = build_incidence(rectangles)

    print(f"\n  Vértices: {len(vertex_to_rects)}")
    print(f"  Retângulos: {len(rect_to_verts)}")
    print("\n  Grau de cada vértice (nº de retângulos cobertos):")
    for v, rects in sorted(vertex_to_rects.items(),
                            key=lambda kv: -len(kv[1])):
        print(f"    {str(v):>10}  →  {sorted(r+1 for r in rects)}")

    # === Cobertura Total ===
    print("\n--- Cobertura Total ---")
    for name, fn in [("Greedy Cobertura Máxima", greedy_max_coverage),
                     ("Greedy Por Grau",         greedy_by_degree)]:
        guards, steps, cov = fn(vertex_to_rects, rect_to_verts)
        ok, _ = verify(guards, rect_to_verts, vertex_to_rects)
        guard_coords = sorted(guards)
        print(f"\n  {name}")
        print(f"    Guardas ({len(guards)}): {guard_coords}")
        print(f"    Iterações: {steps}  |  Cobertura: {cov}/8  |  Válido: {ok}")

    g_rnd, _, _ = greedy_random_restarts(vertex_to_rects, rect_to_verts,
                                         n_restarts=50)
    ok_rnd, _ = verify(g_rnd, rect_to_verts, vertex_to_rects)
    print(f"\n  Greedy Aleatório (×50)")
    print(f"    Guardas ({len(g_rnd)}): {sorted(g_rnd)}")
    print(f"    Válido: {ok_rnd}")

    g_ilp, _ = solve_ilp(vertex_to_rects, rect_to_verts)
    if g_ilp is not None:
        print(f"\n  ILP (óptimo): {len(g_ilp)} guardas → {sorted(g_ilp)}")

    # === Cobertura Parcial (75%) ===
    print("\n--- Cobertura Parcial (75% = 6 retângulos) ---")
    n_target = 6
    target = set(range(n_target))  # cobre os primeiros 6
    for name, fn in [("Greedy Cobertura Máxima", greedy_max_coverage),
                     ("Greedy Por Grau",         greedy_by_degree)]:
        guards, steps, cov = fn(vertex_to_rects, rect_to_verts, target)
        ok, _ = verify(guards, rect_to_verts, vertex_to_rects, target)
        print(f"\n  {name}")
        print(f"    Guardas ({len(guards)}): {sorted(guards)}")
        print(f"    Cobertura: {cov}/{n_target}  |  Válido: {ok}")


# =============================================================
#  MAIN
# =============================================================

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Modo demo sem ficheiro
        demo_embedded()
    else:
        filename    = sys.argv[1]
        partial_pct = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        run(filename, partial_pct)