"""
=============================================================
  Vigilância de Partições Retangulares
  Passo 3 — Programação Dinâmica
  MAD 2025/2026
=============================================================

Implementa três variantes de DP:

  DP-1D  : Caso degenerado — retângulos numa única fila ou
            coluna. Recorrência exacta em O(n).

  DP-COL : Profile DP sobre fronteiras de coluna.
            Processa o plano coluna a coluna (esq→dir).
            Estado = bitmask de guardas na fronteira actual
            + conjunto de retângulos ainda não cobertos.
            Exacto; complexidade exponencial no número de
            vértices por fronteira.

  DP-ROW : Simetria de DP-COL mas por linhas (baixo→cima).
            Útil quando a partição é mais larga que alta.

Uso:
    python dp_guards.py <ficheiro_resultado>
"""

import sys
import time
from collections import defaultdict
from itertools import product


# =============================================================
#  LEITURA E ESTRUTURAS BASE
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
            vs = []
            for _ in range(nv):
                x = int(tokens[idx]); idx += 1
                y = int(tokens[idx]); idx += 1
                vs.append((x, y))
            rects.append(vs)
        instances.append(rects)
    return instances


def build_structures(rectangles):
    """
    Devolve:
      all_verts  : lista ordenada de (x,y) únicas
      vid        : dict (x,y)->índice
      rect_corners: list[list[int]]  (índices dos cantos de cada rect)
      rect_bbox  : list[(xl,xr,yb,yt)]  (bounding box de cada rect)
      v2r        : dict índice -> set de IDs de rectângulos
    """
    vset = set()
    for vs in rectangles:
        vset.update(vs)
    all_verts = sorted(vset)
    vid       = {v: i for i, v in enumerate(all_verts)}

    rect_corners = []
    rect_bbox    = []
    v2r          = defaultdict(set)

    for r, vs in enumerate(rectangles):
        corners = [vid[v] for v in vs]
        rect_corners.append(corners)
        xs = [v[0] for v in vs]
        ys = [v[1] for v in vs]
        rect_bbox.append((min(xs), max(xs), min(ys), max(ys)))
        for vi in corners:
            v2r[vi].add(r)

    return all_verts, vid, rect_corners, rect_bbox, dict(v2r)


# =============================================================
#  DP-1D  —  partição linear (uma única fila ou coluna)
# =============================================================
#
#  Detecção:
#    Fila  horizontal → todos os retângulos têm o mesmo yb e yt
#    Coluna vertical  → todos os retângulos têm o mesmo xl e xr
#
#  Modelo 1D (exemplo para fila):
#    n retângulos R_0, R_1, …, R_{n-1} ordenados por xl
#    n+1 fronteiras verticais b_0 < b_1 < … < b_n
#    Um guarda em b_j cobre R_{j-1} (se j>0) e R_j (se j<n)
#
#  Recorrência:
#    dp[i] = mínimo de guardas para cobrir R_0 … R_{i-1}
#    dp[0] = 0
#    dp[i] = min(
#               dp[i-1] + 1,   # guarda em b_{i-1}  (cobre R_{i-1})
#               dp[i-2] + 1    # guarda em b_i      (cobre R_{i-1} e R_i, se i>=2)
#             )
#    -- Para garantir cobertura total, dp[n] é o óptimo.
#
#  Na prática usamos a versão de "cobertura ganância":
#    Percorre da esquerda para a direita; sempre que um
#    retângulo não está coberto, coloca guarda na fronteira
#    direita desse retângulo (cobre também o próximo).

def detect_1d(rect_bbox):
    """Devolve ('row', y_bottom, y_top) ou ('col', x_left, x_right) ou None."""
    ybs = set(b[2] for b in rect_bbox)
    yts = set(b[3] for b in rect_bbox)
    if len(ybs) == 1 and len(yts) == 1:
        return ('row', next(iter(ybs)), next(iter(yts)))

    xls = set(b[0] for b in rect_bbox)
    xrs = set(b[1] for b in rect_bbox)
    if len(xls) == 1 and len(xrs) == 1:
        return ('col', next(iter(xls)), next(iter(xrs)))

    return None


def dp_1d(rectangles, all_verts, vid, rect_corners, rect_bbox, v2r):
    """
    DP exacta para partições lineares (1D).

    Devolve (guards_coords, cost) ou None se não for 1D.
    """
    kind = detect_1d(rect_bbox)
    if kind is None:
        return None  # não é 1D

    dim = kind[0]  # 'row' ou 'col'

    # Ordena retângulos pelo seu limite inferior na direcção de corte
    if dim == 'row':
        # Ordena por xl (coordenada x crescente)
        order = sorted(range(len(rect_bbox)), key=lambda r: rect_bbox[r][0])
        # Fronteiras = valores únicos de xl e xr
        coords = sorted(set(
            c for r in range(len(rect_bbox))
            for c in (rect_bbox[r][0], rect_bbox[r][1])
        ))
        # Para cada retângulo, qual o índice da sua fronteira esquerda e direita
        coord_idx = {c: i for i, c in enumerate(coords)}
        left_idx  = [coord_idx[rect_bbox[r][0]] for r in range(len(rect_bbox))]
        right_idx = [coord_idx[rect_bbox[r][1]] for r in range(len(rect_bbox))]
        fixed_y   = (kind[1], kind[2])   # (yb, yt) — fixo para todos

    else:  # col
        order = sorted(range(len(rect_bbox)), key=lambda r: rect_bbox[r][2])
        coords = sorted(set(
            c for r in range(len(rect_bbox))
            for c in (rect_bbox[r][2], rect_bbox[r][3])
        ))
        coord_idx = {c: i for i, c in enumerate(coords)}
        left_idx  = [coord_idx[rect_bbox[r][2]] for r in range(len(rect_bbox))]
        right_idx = [coord_idx[rect_bbox[r][3]] for r in range(len(rect_bbox))]
        fixed_x   = (kind[1], kind[2])

    n      = len(rectangles)
    n_fron = len(coords)     # número de fronteiras

    # ----------------------------------------------------------
    #  Recorrência DP
    #  dp[j] = min guardas para cobrir todos os retângulos cuja
    #          fronteira direita ≤ coords[j]
    # ----------------------------------------------------------
    INF = float('inf')
    dp       = [INF] * n_fron
    choice   = [-1]  * n_fron   # fronteira onde foi colocado guarda

    dp[0] = 0   # fronteira 0: nenhum retângulo fechado ainda

    for j in range(1, n_fron):
        # Opção A: guarda na fronteira j-1 (cobre rect cuja right_idx=j e left_idx=j-1,
        #          e também o rect anterior se existir)
        if dp[j-1] < INF:
            candidate = dp[j-1] + 1
            if candidate < dp[j]:
                dp[j]     = candidate
                choice[j] = j - 1

        # Opção B: guarda na fronteira j (cobre rect cuja right_idx=j)
        # Necessário se há rect com right_idx=j e left_idx=j-1
        # (um guarda em j cobre os dois retângulos adjacentes à fronteira j)
        if j >= 2 and dp[j-2] < INF:
            candidate = dp[j-2] + 1
            if candidate < dp[j]:
                dp[j]     = candidate
                choice[j] = j

    # ----------------------------------------------------------
    #  Reconstrução da solução
    # ----------------------------------------------------------
    guards_coords = []
    j = n_fron - 1
    while j > 0:
        g = choice[j]
        if g < 0:
            break
        g_coord = coords[g]
        # Determinar coordenadas do vértice (qualquer vértice na fronteira g)
        if dim == 'row':
            yb, yt = fixed_y
            guards_coords.append((g_coord, yb))  # canto SW da fronteira
        else:
            xl, xr = fixed_x
            guards_coords.append((xl, g_coord))
        j = g - 1

    cost = dp[n_fron - 1]
    return guards_coords, cost


# =============================================================
#  DP-COL  —  Profile DP por colunas
# =============================================================
#
#  Processa as fronteiras verticais X[0] < X[1] < … < X[K]
#  da esquerda para a direita.
#
#  Estado em X[j]:
#    mask  — bitmask dos vértices em X[j] que têm guarda
#    uncov — frozenset dos retângulos ainda não cobertos
#            cujo xl ≤ X[j] (já foram "abertos")
#
#  Transição X[j] → X[j+1]:
#    1. Verificar que todos os retângulos com xr = X[j] estão
#       cobertos (senão é inviável).
#    2. Escolher mask para X[j+1] → adicionar guardas.
#    3. Actualizar uncov: remover retângulos cobertos por
#       qualquer guarda em X[j+1], adicionar retângulos com
#       xl = X[j+1].
#
#  Custo: número total de bits=1 em todos os masks escolhidos.
#
#  Complexidade: O(K · 2^W · R)  onde W = máx vértices por
#  fronteira, R = número de retângulos.

def dp_column_profile(all_verts, rect_corners, rect_bbox, v2r, timeout=5.0):
    """
    Profile DP exacta por fronteiras de coluna.

    Devolve (guards_vi, cost, optimal) onde:
      guards_vi : lista de índices de vértices com guarda
      cost      : número de guardas
      optimal   : True se solução óptima, False se timeout
    """
    n_rects = len(rect_bbox)

    # --- Fronteiras verticais ---
    X = sorted(set(b[0] for b in rect_bbox) | set(b[1] for b in rect_bbox))
    K = len(X)
    xi = {x: j for j, x in enumerate(X)}

    # --- Vértices por fronteira ---
    # fverts[j] = lista ordenada de índices de vértices em X[j]
    fverts = defaultdict(list)
    for vi, (x, y) in enumerate(all_verts):
        if x in xi:
            fverts[xi[x]].append(vi)
    fverts = {j: sorted(fverts[j]) for j in range(K)}

    # --- Retângulos por fronteira ---
    # rects_open[j]  = rects com xl = X[j]   (abrem nesta fronteira)
    # rects_close[j] = rects com xr = X[j]   (fecham nesta fronteira)
    # rects_touch[j] = rects com xl<=X[j]<=xr (têm vértices nesta fronteira)
    rects_open  = defaultdict(set)
    rects_close = defaultdict(set)
    rects_touch = defaultdict(set)   # rects cujos vértices estão em X[j]

    for r, (xl, xr, yb, yt) in enumerate(rect_bbox):
        rects_open[xi[xl]].add(r)
        rects_close[xi[xr]].add(r)
        for jx in range(xi[xl], xi[xr] + 1):
            rects_touch[jx].add(r)

    # Para cada (fronteira, rect), quais os vértices de rect em X[j]?
    # covered_by[j][vi] = set de rects que vi cobre (vi está em X[j] e é canto de rect)
    covered_by = {}
    for j in range(K):
        covered_by[j] = {}
        for vi in fverts[j]:
            covered_by[j][vi] = v2r.get(vi, set()) & rects_touch[j]

    # --- DP ---
    # dp_state: dict  frozenset(uncov) → (min_cost, list_of_(j,mask))
    INF = float('inf')

    # Estado inicial na fronteira 0: todos os rects que abrem em X[0] estão uncovered
    init_uncov = frozenset(rects_open[0])
    # Escolher mask em X[0]
    best      = {init_uncov: (INF, [])}
    t0        = time.time()
    optimal   = True

    for j in range(K):
        verts_j  = fverts[j]
        n_j      = len(verts_j)
        next_states = {}

        for uncov, (cost_so_far, history) in best.items():
            if time.time() - t0 > timeout:
                optimal = False
                break

            # Enumerar todos os subconjuntos de verts_j
            for mask in range(1 << n_j):
                guards_j = [verts_j[k] for k in range(n_j) if mask & (1 << k)]
                extra    = bin(mask).count('1')
                new_cost = cost_so_far + extra

                # Actualizar uncov: remover rects cobertos por guards_j
                new_uncov = set(uncov)
                for vi in guards_j:
                    new_uncov -= covered_by[j].get(vi, set())

                # Verificar viabilidade: rects que fecham em X[j]
                # devem estar cobertos agora
                closing = rects_close[j]
                if closing & new_uncov:
                    continue  # inviável

                # Abrir novos retângulos em X[j+1] (se existir)
                if j + 1 < K:
                    new_uncov |= rects_open[j + 1]

                key = frozenset(new_uncov)
                new_hist = history + [(j, mask)]

                if key not in next_states or new_cost < next_states[key][0]:
                    next_states[key] = (new_cost, new_hist)

        if not optimal:
            break
        best = next_states

    # --- Extrair solução óptima ---
    # Estado final: frozenset() (nenhum rect por cobrir)
    target = frozenset()
    if target not in best:
        return None, INF, False

    final_cost, history = best[target]

    # Reconstruir guardas
    guards_vi = []
    for j, mask in history:
        verts_j = fverts[j]
        for k in range(len(verts_j)):
            if mask & (1 << k):
                guards_vi.append(verts_j[k])

    return guards_vi, final_cost, optimal


# =============================================================
#  DP-ROW  —  Profile DP por linhas (simetria de DP-COL)
# =============================================================

def dp_row_profile(all_verts, rect_corners, rect_bbox, v2r, timeout=5.0):
    """
    Idem ao DP-COL mas processa fronteiras horizontais (Y).
    Útil quando a partição tem mais colunas do que linhas.
    """
    n_rects = len(rect_bbox)

    Y = sorted(set(b[2] for b in rect_bbox) | set(b[3] for b in rect_bbox))
    K = len(Y)
    yi = {y: j for j, y in enumerate(Y)}

    fverts = defaultdict(list)
    for vi, (x, y) in enumerate(all_verts):
        if y in yi:
            fverts[yi[y]].append(vi)
    fverts = {j: sorted(fverts[j]) for j in range(K)}

    rects_open  = defaultdict(set)
    rects_close = defaultdict(set)
    rects_touch = defaultdict(set)

    for r, (xl, xr, yb, yt) in enumerate(rect_bbox):
        rects_open[yi[yb]].add(r)
        rects_close[yi[yt]].add(r)
        for jy in range(yi[yb], yi[yt] + 1):
            rects_touch[jy].add(r)

    covered_by = {}
    for j in range(K):
        covered_by[j] = {}
        for vi in fverts[j]:
            covered_by[j][vi] = v2r.get(vi, set()) & rects_touch[j]

    INF = float('inf')
    init_uncov = frozenset(rects_open[0])
    best       = {init_uncov: (INF, [])}
    t0         = time.time()
    optimal    = True

    for j in range(K):
        verts_j     = fverts[j]
        n_j         = len(verts_j)
        next_states = {}

        for uncov, (cost_so_far, history) in best.items():
            if time.time() - t0 > timeout:
                optimal = False
                break

            for mask in range(1 << n_j):
                guards_j = [verts_j[k] for k in range(n_j) if mask & (1 << k)]
                new_cost = cost_so_far + bin(mask).count('1')
                new_uncov = set(uncov)
                for vi in guards_j:
                    new_uncov -= covered_by[j].get(vi, set())
                if rects_close[j] & new_uncov:
                    continue
                if j + 1 < K:
                    new_uncov |= rects_open[j + 1]
                key = frozenset(new_uncov)
                new_hist = history + [(j, mask)]
                if key not in next_states or new_cost < next_states[key][0]:
                    next_states[key] = (new_cost, new_hist)

        if not optimal:
            break
        best = next_states

    target = frozenset()
    if target not in best:
        return None, INF, False

    final_cost, history = best[target]
    guards_vi = []
    for j, mask in history:
        verts_j = fverts[j]
        for k in range(len(verts_j)):
            if mask & (1 << k):
                guards_vi.append(verts_j[k])

    return guards_vi, final_cost, optimal


# =============================================================
#  ESCOLHA AUTOMÁTICA DA MELHOR DP
# =============================================================

def dp_best(rectangles, all_verts, vid, rect_corners, rect_bbox, v2r,
            timeout=5.0):
    """
    Escolhe automaticamente a variante de DP mais adequada:
      1. Se 1D → dp_1d  (O(n), sempre óptima)
      2. Se mais colunas do que linhas → dp_row_profile
      3. Caso contrário → dp_column_profile
    Devolve (guards_coords, cost, method, optimal).
    """
    # --- Tentar 1D ---
    result_1d = dp_1d(rectangles, all_verts, vid, rect_corners, rect_bbox, v2r)
    if result_1d is not None:
        coords, cost = result_1d
        return coords, cost, 'DP-1D (exacta)', True

    # --- Escolher coluna vs linha ---
    X = sorted(set(b[0] for b in rect_bbox) | set(b[1] for b in rect_bbox))
    Y = sorted(set(b[2] for b in rect_bbox) | set(b[3] for b in rect_bbox))

    # Número de vértices por fronteira (estimativa do custo da DP)
    from collections import Counter
    xcount = Counter(v[0] for v in all_verts)
    ycount = Counter(v[1] for v in all_verts)
    max_col_width = max(xcount[x] for x in X)
    max_row_height = max(ycount[y] for y in Y)

    if max_row_height <= max_col_width:
        guards_vi, cost, opt = dp_row_profile(
            all_verts, rect_corners, rect_bbox, v2r, timeout)
        method = 'DP-ROW (profile)'
    else:
        guards_vi, cost, opt = dp_column_profile(
            all_verts, rect_corners, rect_bbox, v2r, timeout)
        method = 'DP-COL (profile)'

    if guards_vi is None:
        return None, float('inf'), method, False

    coords = [all_verts[vi] for vi in guards_vi]
    return coords, cost, method, opt


# =============================================================
#  COMPARAÇÃO COM ILP
# =============================================================

def solve_ilp(rect_corners, n_verts, v2r):
    try:
        from ortools.linear_solver import pywraplp
    except ImportError:
        return None, 0

    solver = pywraplp.Solver.CreateSolver('SCIP')
    x      = [solver.IntVar(0, 1, f'x{v}') for v in range(n_verts)]
    for corners in rect_corners:
        solver.Add(sum(x[vi] for vi in corners) >= 1)
    solver.Minimize(sum(x))
    t0 = time.time()
    status = solver.Solve()
    elapsed = time.time() - t0
    if status == pywraplp.Solver.OPTIMAL:
        return [v for v in range(n_verts) if x[v].solution_value() > 0.5], elapsed
    return None, elapsed


# =============================================================
#  ANÁLISE DA ESTRUTURA DA PARTIÇÃO
# =============================================================

def analyse_partition(all_verts, rect_bbox):
    """
    Imprime estatísticas estruturais da partição,
    relevantes para perceber qual DP é mais eficiente.
    """
    from collections import Counter

    X = sorted(set(b[0] for b in rect_bbox) | set(b[1] for b in rect_bbox))
    Y = sorted(set(b[2] for b in rect_bbox) | set(b[3] for b in rect_bbox))

    xcount = Counter(v[0] for v in all_verts)
    ycount = Counter(v[1] for v in all_verts)

    max_col = max(xcount[x] for x in X)
    max_row = max(ycount[y] for y in Y)

    print(f"    Fronteiras verticais  : {len(X)}   (máx. {max_col} vértices/fronteira)")
    print(f"    Fronteiras horizontais: {len(Y)}   (máx. {max_row} vértices/fronteira)")
    print(f"    Estados DP-COL (máx)  : 2^{max_col} = {2**max_col}")
    print(f"    Estados DP-ROW (máx)  : 2^{max_row} = {2**max_row}")
    kind = detect_1d(rect_bbox)
    if kind:
        print(f"    Estrutura 1D detectada: {kind[0]}")


# =============================================================
#  PONTO DE ENTRADA
# =============================================================

def run(filename):
    instances = parse_partition_file(filename)
    print(f"\nFicheiro  : {filename}")
    print(f"Instâncias: {len(instances)}\n")

    for i, rectangles in enumerate(instances):
        all_verts, vid, rect_corners, rect_bbox, v2r = build_structures(rectangles)
        n_rects = len(rectangles)
        n_verts = len(all_verts)

        print(f"{'='*62}")
        print(f"  Instância {i+1}  |  {n_rects} retângulos  |  {n_verts} vértices")
        print(f"{'='*62}")
        analyse_partition(all_verts, rect_bbox)

        # --- DP ---
        print()
        t0 = time.time()
        coords, cost, method, optimal = dp_best(
            rectangles, all_verts, vid, rect_corners, rect_bbox, v2r,
            timeout=10.0)
        t_dp = (time.time() - t0) * 1000

        opt_str = "óptima" if optimal else "heurística (timeout)"
        print(f"  {method}")
        print(f"    Guardas  : {cost}  [{opt_str}]")
        print(f"    Posições : {sorted(coords) if coords else '—'}")
        print(f"    Tempo    : {t_dp:.2f} ms")

        # --- ILP para comparação ---
        g_ilp, t_ilp = solve_ilp(rect_corners, n_verts, v2r)
        if g_ilp is not None:
            ilp_cost = len(g_ilp)
            gap      = cost - ilp_cost
            print(f"\n  ILP (SCIP) — referência")
            print(f"    Guardas  : {ilp_cost}")
            print(f"    Tempo    : {t_ilp*1000:.2f} ms")
            print(f"    Gap DP   : {gap:+d}  "
                  f"({'óptimo' if gap == 0 else 'supra-óptimo'})")
        print()


# =============================================================
#  DEMO EMBUTIDA — instância 1D e instância 2D pequena
# =============================================================

def demo():
    print("\n" + "="*62)
    print("  DEMONSTRAÇÃO — DP-1D e DP-COL")
    print("="*62)

    # --- Exemplo 1D: 5 retângulos em fila ---
    print("\n  [1D]  Fila de 5 retângulos")
    rects_1d = [
        [(0,0),(1,0),(1,1),(0,1)],
        [(1,0),(2,0),(2,1),(1,1)],
        [(2,0),(3,0),(3,1),(2,1)],
        [(3,0),(4,0),(4,1),(3,1)],
        [(4,0),(5,0),(5,1),(4,1)],
    ]
    av, vd, rc, rb, vr = build_structures(rects_1d)
    r1d = dp_1d(rects_1d, av, vd, rc, rb, vr)
    if r1d:
        coords, cost = r1d
        print(f"    Guardas : {cost}  em {sorted(coords)}")
        # ILP
        g, _ = solve_ilp(rc, len(av), vr)
        print(f"    ILP     : {len(g)}  (gap = {cost - len(g):+d})")

    # --- Exemplo 2D: 4 retângulos em grelha 2×2 ---
    print("\n  [2D]  Grelha 2x2 (4 retângulos)")
    rects_2d = [
        [(0,0),(1,0),(1,1),(0,1)],
        [(1,0),(2,0),(2,1),(1,1)],
        [(0,1),(1,1),(1,2),(0,2)],
        [(1,1),(2,1),(2,2),(1,2)],
    ]
    av2, vd2, rc2, rb2, vr2 = build_structures(rects_2d)
    guards_vi, cost2, opt2 = dp_column_profile(av2, rc2, rb2, vr2, timeout=5)
    if guards_vi is not None and cost2 < float('inf'):
        coords2 = [av2[vi] for vi in guards_vi]
        print(f"    Guardas : {cost2}  em {sorted(coords2)}")
        g2, _ = solve_ilp(rc2, len(av2), vr2)
        gap2   = int(cost2) - len(g2)
        print(f"    ILP     : {len(g2)}  (gap = {gap2:+d})")
    else:
        print("    Sem solução encontrada (verificar instância)")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        demo()
    else:
        run(sys.argv[1])