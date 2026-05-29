"""
=============================================================
  Benchmark Unificado -- Vigilancia de Particoes Retangulares
  MAD 2025/2026
=============================================================

Corre todos os algoritmos em todas as instancias e guarda
resultados em CSV + tabelas para o relatorio.

Algoritmos testados:
  - Greedy Cobertura Maxima
  - Greedy Por Grau (estatico)
  - Greedy Aleatorio (x30 reinicio)
  - MAC + AC-3 (backtracking com propagacao)
  - DP (melhor variante automatica)
  - ILP via OR-Tools (SCIP)  -- optimo de referencia
  - CP-SAT via OR-Tools      -- programacao por restricoes
  - Prolog CLP(FD)           -- via subprocess (se SWI-Prolog instalado)

Uso:
    python benchmark.py                        # todas as instancias
    python benchmark.py inst_small.txt         # ficheiro especifico
    python benchmark.py inst_small.txt --mac   # inclui MAC (lento)
    python benchmark.py --all                  # todos os ficheiros padrao

Resultados:
    results/benchmark_<data>.csv
    results/benchmark_<data>_summary.txt
"""

import sys
import os
import time
import csv
import subprocess
import shutil
from datetime import datetime
from collections import defaultdict

# ── Directorio de resultados ──────────────────────────────────
RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)


# =============================================================
#  LEITURA DO FICHEIRO (formato identico ao 'res' / a.exe)
# =============================================================

def parse_file(filename):
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


# =============================================================
#  ESTRUTURAS BASE
# =============================================================

def build_incidence(rectangles):
    """Constroi grafo de incidencia. Devolve (v2r_coords, r2v_coords, all_verts, vid, rect_corners)."""
    vset = set()
    for vs in rectangles:
        vset.update(vs)
    all_verts = sorted(vset)
    vid = {v: i for i, v in enumerate(all_verts)}

    v2r = defaultdict(set)   # coords -> set de r
    r2v = {}                  # r -> list de coords

    rect_corners = []        # list of list of vertex indices
    for r, vs in enumerate(rectangles):
        corners_idx = [vid[v] for v in vs]
        rect_corners.append(corners_idx)
        r2v[r] = list(vs)
        for v in vs:
            v2r[v].add(r)

    return dict(v2r), r2v, all_verts, vid, rect_corners


# =============================================================
#  GREEDY (importa de greedy.py)
# =============================================================

def run_greedy(v2r_coords, r2v_coords, target_rects=None):
    """Corre as 3 estrategias greedy. Devolve dict {nome: (n_guardas, tempo_ms)}."""
    from greedy import (build_incidence as gi_build,
                        greedy_max_coverage, greedy_by_degree,
                        greedy_random_restarts, verify)

    # Re-constroi no formato de greedy.py (coords como chaves)
    rectangles_list = [list(r2v_coords[r]) for r in sorted(r2v_coords)]
    v2r_g, r2v_g = gi_build(rectangles_list)

    if target_rects is not None:
        tgt = set(target_rects)
    else:
        tgt = None

    results = {}

    t0 = time.perf_counter()
    g1, _, _ = greedy_max_coverage(v2r_g, r2v_g, tgt)
    results['Greedy_MaxCov'] = (len(g1), (time.perf_counter()-t0)*1000)

    t0 = time.perf_counter()
    g2, _, _ = greedy_by_degree(v2r_g, r2v_g, tgt)
    results['Greedy_Grau'] = (len(g2), (time.perf_counter()-t0)*1000)

    t0 = time.perf_counter()
    g3, _, _ = greedy_random_restarts(v2r_g, r2v_g, tgt, n_restarts=30)
    results['Greedy_Aleat'] = (len(g3), (time.perf_counter()-t0)*1000)

    return results


# =============================================================
#  MAC + AC-3 (importa de mac_ac3.py)
# =============================================================

def run_mac(v2r_coords, r2v_coords, timeout_s=60):
    """
    Corre MAC+AC-3.
    Devolve (n_guardas, tempo_ms, nos_bt) ou (None, elapsed_ms, None) se timeout.
    Usa subprocess para impor timeout sem depender de threading.
    """
    # Construir lista de rectangulos no formato correcto
    rectangles_list = [list(r2v_coords[r]) for r in sorted(r2v_coords)]

    # Script inline para correr em sub-processo separado
    script = (
        "import sys, time\n"
        "sys.path.insert(0, r'" + os.path.dirname(os.path.abspath(__file__)) + "')\n"
        "from mac_ac3 import build_incidence, CSP, Solver\n"
        f"rects = {rectangles_list!r}\n"
        "v2r, r2v = build_incidence(rects)\n"
        "csp = CSP(v2r, r2v)\n"
        "s = Solver(csp)\n"
        "t0 = time.perf_counter()\n"
        "sol = s.solve()\n"
        "elapsed = (time.perf_counter()-t0)*1000\n"
        "n = len(sol) if sol is not None else -1\n"
        "print(f'RESULT:{n}:{s.nodes}:{elapsed:.3f}')\n"
    )

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True, text=True, timeout=timeout_s
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        for line in proc.stdout.splitlines():
            if line.startswith('RESULT:'):
                parts = line.split(':')
                n_g   = int(parts[1])
                nodes = int(parts[2])
                if n_g == -1:
                    return None, elapsed_ms, nodes
                return n_g, elapsed_ms, nodes
        # Sem linha RESULT: -- pode ter dado erro interno
        if proc.stderr:
            print(f'    [MAC subprocess stderr]: {proc.stderr[:200]}')
        return None, elapsed_ms, None
    except subprocess.TimeoutExpired:
        elapsed_ms = timeout_s * 1000
        return None, elapsed_ms, None
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f'    [MAC subprocess error]: {e}')
        return None, elapsed_ms, None


# =============================================================
#  DP (importa de dp_guards.py)
# =============================================================

def run_dp(rectangles, timeout_s=30):
    """Corre a melhor variante DP. Devolve (n_guardas, tempo_ms, metodo, optimo)."""
    from dp_guards import build_structures, dp_best

    all_verts, vid, rect_corners, rect_bbox, v2r = build_structures(rectangles)
    t0 = time.perf_counter()
    coords, cost, method, optimal = dp_best(
        rectangles, all_verts, vid, rect_corners, rect_bbox, v2r,
        timeout=timeout_s)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if coords is None:
        return None, elapsed_ms, method, False
    return int(cost) if cost < float('inf') else None, elapsed_ms, method, optimal


# =============================================================
#  ILP + CP-SAT (importa de Ortools.py)
# =============================================================

def run_ortools(rectangles):
    """Corre ILP (SCIP) e CP-SAT. Devolve (ilp_g, ilp_ms, cpsat_g, cpsat_ms)."""
    from Ortools import build_incidence as ot_build, solve_ilp, solve_cpsat

    all_verts, vid, rect_corners, v2r = ot_build(rectangles)
    n_verts = len(all_verts)

    t0 = time.perf_counter()
    g_ilp, _ = solve_ilp(rect_corners, n_verts)
    ilp_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    g_cp, _, cp_opt = solve_cpsat(rect_corners, n_verts)
    cp_ms = (time.perf_counter() - t0) * 1000

    ilp_n = len(g_ilp) if g_ilp is not None else None
    cp_n  = len(g_cp)  if g_cp  is not None else None

    return ilp_n, ilp_ms, cp_n, cp_ms


# =============================================================
#  PROLOG via subprocess
# =============================================================

def _find_swipl():
    """Procura o executavel swipl no PATH e localizacoes comuns."""
    for candidate in ['swipl', 'swipl.exe']:
        if shutil.which(candidate):
            return candidate
    common = [
        r'C:\Program Files\swipl\bin\swipl.exe',
        r'C:\Program Files (x86)\swipl\bin\swipl.exe',
        '/usr/bin/swipl',
        '/usr/local/bin/swipl',
    ]
    for p in common:
        if os.path.isfile(p):
            return p
    return None


def run_prolog(rectangles, instance_id, timeout_s=60):
    """
    Corre SWI-Prolog com CLP(FD) para resolver a instancia.
    Usa caminhos absolutos (obrigatório em Windows).
    """
    swipl = _find_swipl()
    if swipl is None:
        return None, 0.0, 'SWI-Prolog nao instalado'

    from Ortools import build_incidence as ot_build, export_to_prolog
    ot_build(rectangles)   # apenas para validar

    # Caminhos absolutos — SWI-Prolog precisa de forward-slashes em Windows
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    pl_file      = os.path.join(script_dir, f'_tmp_bench_{instance_id}.pl')
    guards_pl    = os.path.join(script_dir, 'guards.pl')
    pl_file_pl   = pl_file.replace('\\', '/')
    guards_pl_pl = guards_pl.replace('\\', '/')

    export_to_prolog(rectangles, instance_id, filename=pl_file)

    goal = (
        f"consult('{pl_file_pl}'), "
        f"consult('{guards_pl_pl}'), "
        f"findall(R, rect(R), Rects), "
        f"nverts(NV), "
        f"statistics(runtime,[T0|_]), "
        f"solve(Rects, NV, Guards, Cost), "
        f"statistics(runtime,[T1|_]), "
        f"Elapsed is T1 - T0, "
        f"format('COST:~w~n',[Cost]), "
        f"format('TIME:~w~n',[Elapsed]), "
        f"halt."
    )

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [swipl, '-q', '-g', goal],
            capture_output=True, text=True, timeout=timeout_s,
            cwd=script_dir
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        output = proc.stdout

        cost  = None
        pl_ms = None
        for line in output.splitlines():
            if line.startswith('COST:'):
                try:
                    cost = int(line.split(':')[1])
                except ValueError:
                    pass
            if line.startswith('TIME:'):
                try:
                    pl_ms = float(line.split(':')[1])
                except ValueError:
                    pass

        if pl_ms is None:
            pl_ms = elapsed_ms

        if cost is not None:
            status = 'ok'
        else:
            err = proc.stderr[:120].replace('\n', ' ')
            status = f'erro: {err}'
        return cost, pl_ms, status

    except subprocess.TimeoutExpired:
        return None, timeout_s * 1000, 'timeout'
    except Exception as e:
        return None, 0.0, f'erro: {e}'
    finally:
        if os.path.exists(pl_file):
            os.remove(pl_file)


# =============================================================
#  BENCHMARK PRINCIPAL
# =============================================================

def run_benchmark(filename, run_mac_flag=True, run_prolog_flag=True,
                  mac_timeout=30, dp_timeout=15, prolog_timeout=60):
    """
    Corre todos os algoritmos em todas as instancias do ficheiro.
    Devolve lista de dicts de resultados.
    """
    instances = parse_file(filename)
    basename = os.path.basename(filename)
    print(f'\n{"="*62}')
    print(f'  Ficheiro: {basename}  ({len(instances)} instancias)')
    print(f'{"="*62}')

    rows = []   # para o CSV

    for i, rectangles in enumerate(instances):
        n_rects = len(rectangles)
        v2r, r2v, all_verts, vid, rect_corners = build_incidence(rectangles)
        n_verts = len(all_verts)

        print(f'\n  Inst {i+1}/{len(instances)} | {n_rects} rect | {n_verts} vert')

        row = {
            'ficheiro'   : basename,
            'instancia'  : i + 1,
            'n_rects'    : n_rects,
            'n_verts'    : n_verts,
        }

        # ── Greedy ───────────────────────────────────────────
        try:
            g_res = run_greedy(v2r, r2v)
            for k, (ng, ms) in g_res.items():
                row[f'{k}_n'] = ng
                row[f'{k}_ms'] = round(ms, 3)
                print(f'    {k:<20} {ng:>4} guardas  {ms:8.2f} ms')
        except Exception as e:
            print(f'    ERRO Greedy: {e}')
            for k in ('Greedy_MaxCov', 'Greedy_Grau', 'Greedy_Aleat'):
                row[f'{k}_n'] = None; row[f'{k}_ms'] = None

        # ── ILP + CP-SAT ─────────────────────────────────────
        try:
            ilp_n, ilp_ms, cp_n, cp_ms = run_ortools(rectangles)
            row['ILP_n']   = ilp_n;  row['ILP_ms']   = round(ilp_ms, 3)
            row['CPSAT_n'] = cp_n;   row['CPSAT_ms']  = round(cp_ms, 3)
            opt = ilp_n  # referencia para gaps
            print(f'    {"ILP_SCIP":<20} {ilp_n or "?":>4} guardas  {ilp_ms:8.2f} ms  [optimo]')
            print(f'    {"CP_SAT":<20} {cp_n  or "?":>4} guardas  {cp_ms:8.2f} ms')
        except Exception as e:
            print(f'    ERRO OR-Tools: {e}')
            ilp_n = None; opt = None
            row['ILP_n'] = row['ILP_ms'] = row['CPSAT_n'] = row['CPSAT_ms'] = None

        # ── DP ───────────────────────────────────────────────
        try:
            dp_n, dp_ms, dp_method, dp_opt = run_dp(rectangles, timeout_s=dp_timeout)
            row['DP_n']      = dp_n
            row['DP_ms']     = round(dp_ms, 3)
            row['DP_method'] = dp_method
            row['DP_optimo'] = dp_opt
            if dp_n is None:
                row['DP_status'] = 'timeout'
            elif dp_opt:
                row['DP_status'] = 'opt'
            else:
                row['DP_status'] = 'heur'
            opt_str = row['DP_status']
            print(f'    {"DP":<20} {dp_n or "timeout":>8} guardas  {dp_ms:8.2f} ms  [{dp_method}/{opt_str}]')
        except Exception as e:
            print(f'    ERRO DP: {e}')
            row['DP_n'] = row['DP_ms'] = row['DP_method'] = row['DP_optimo'] = None
            row['DP_status'] = 'erro'

        # ── MAC + AC-3 (opcional -- lento para inst. grandes) ─
        if run_mac_flag and n_rects <= 20:
            mac_n, mac_ms, mac_nodes = run_mac(v2r, r2v, timeout_s=mac_timeout)
            row['MAC_n']     = mac_n
            row['MAC_ms']    = round(mac_ms, 3) if mac_ms else None
            row['MAC_nodes'] = mac_nodes
            n_str = str(mac_n) if mac_n is not None else 'timeout'
            print(f'    {"MAC+AC3":<20} {n_str:>4} guardas  {mac_ms:8.2f} ms  (nos={mac_nodes})')
        else:
            row['MAC_n'] = row['MAC_ms'] = row['MAC_nodes'] = (
                'skip' if n_rects > 20 else None)

        # ── Prolog CLP(FD) ────────────────────────────────────
        if run_prolog_flag and n_rects <= 20:
            pl_n, pl_ms, pl_status = run_prolog(rectangles, f'{basename}_{i+1}',
                                                 timeout_s=prolog_timeout)
            row['Prolog_n']      = pl_n
            row['Prolog_ms']     = round(pl_ms, 3) if pl_ms else None
            row['Prolog_status'] = pl_status
            n_str = str(pl_n) if pl_n is not None else pl_status
            print(f'    {"Prolog CLP(FD)":<20} {n_str:>20}  {pl_ms or 0:8.2f} ms')
        else:
            row['Prolog_n'] = None
            row['Prolog_ms'] = None
            row['Prolog_status'] = 'skip (n>20)'

        # ── Gaps relativos ao optimo ILP ──────────────────────
        if opt is not None:
            for alg in ('Greedy_MaxCov', 'Greedy_Grau', 'Greedy_Aleat',
                        'MAC', 'DP', 'CPSAT'):
                k = f'{alg}_n'
                if row.get(k) and isinstance(row[k], int):
                    row[f'{alg}_gap'] = row[k] - opt
                else:
                    row[f'{alg}_gap'] = None
            row['opt_ILP'] = opt

        rows.append(row)

    return rows


# =============================================================
#  ESCRITA DE RESULTADOS
# =============================================================

# Colunas do CSV (ordem para o relatorio)
CSV_COLS = [
    'ficheiro', 'instancia', 'n_rects', 'n_verts',
    'opt_ILP',
    'Greedy_MaxCov_n', 'Greedy_MaxCov_ms', 'Greedy_MaxCov_gap',
    'Greedy_Grau_n',   'Greedy_Grau_ms',   'Greedy_Grau_gap',
    'Greedy_Aleat_n',  'Greedy_Aleat_ms',  'Greedy_Aleat_gap',
    'MAC_n', 'MAC_ms', 'MAC_nodes', 'MAC_gap',
    'DP_n',  'DP_ms',  'DP_method', 'DP_optimo', 'DP_status', 'DP_gap',
    'ILP_n', 'ILP_ms',
    'CPSAT_n', 'CPSAT_ms', 'CPSAT_gap',
    'Prolog_n', 'Prolog_ms', 'Prolog_status',
]


def save_csv(rows, tag=''):
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    fname = os.path.join(RESULTS_DIR, f'benchmark_{date_str}{tag}.csv')
    with open(fname, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in CSV_COLS})
    print(f'\n  CSV guardado: {fname}')
    return fname


def print_summary_table(rows):
    """Imprime tabela resumo para copiar para o relatorio."""
    print(f'\n{"="*90}')
    print(f'  {"Inst":<6} {"Rects":>5} {"Verts":>5} {"OPT":>4} '
          f'{"GMaxCov":>8} {"GGrau":>7} {"GAleat":>7} '
          f'{"MAC":>5} {"DP":>5} {"CPSAT":>6} {"Prolog":>7}')
    print(f'  {"-"*85}')
    for row in rows:
        opt  = row.get('opt_ILP', '?')
        g1   = row.get('Greedy_MaxCov_n', '?')
        g2   = row.get('Greedy_Grau_n', '?')
        g3   = row.get('Greedy_Aleat_n', '?')
        mac  = row.get('MAC_n', '-')
        dp   = row.get('DP_n', '?')
        cp   = row.get('CPSAT_n', '?')
        pl   = row.get('Prolog_n', '-')

        def fmt(v):
            if v is None or v == 'timeout' or v == 'skip':
                return '-'
            if isinstance(v, str):
                return '-'
            return str(v)

        print(f'  {row["instancia"]:<6} {row["n_rects"]:>5} {row["n_verts"]:>5} '
              f'{fmt(opt):>4} '
              f'{fmt(g1):>8} {fmt(g2):>7} {fmt(g3):>7} '
              f'{fmt(mac):>5} {fmt(dp):>5} {fmt(cp):>6} {fmt(pl):>7}')
    print(f'{"="*90}')


def save_summary(rows, tag=''):
    """Guarda sumario legivel por humanos."""
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    fname = os.path.join(RESULTS_DIR, f'summary_{date_str}{tag}.txt')

    # Agrupar por ficheiro
    by_file = defaultdict(list)
    for r in rows:
        by_file[r['ficheiro']].append(r)

    lines = [f'Benchmark MAD 2025/2026 -- {date_str}\n']

    alg_keys = [
        ('Greedy_MaxCov', 'Greedy Cobertura Maxima'),
        ('Greedy_Grau',   'Greedy Por Grau'),
        ('Greedy_Aleat',  'Greedy Aleatorio x30'),
        ('MAC',           'MAC + AC-3'),
        ('DP',            'Programacao Dinamica'),
        ('CPSAT',         'CP-SAT (OR-Tools)'),
    ]

    for fname_key, file_rows in by_file.items():
        lines.append(f'\n{"="*60}')
        lines.append(f'Ficheiro: {fname_key}')
        lines.append(f'{"="*60}')

        for alg_k, alg_name in alg_keys:
            gaps = [r.get(f'{alg_k}_gap') for r in file_rows
                    if isinstance(r.get(f'{alg_k}_gap'), int)]
            times = [r.get(f'{alg_k}_ms') for r in file_rows
                     if isinstance(r.get(f'{alg_k}_ms'), float)]
            counts = [r.get(f'{alg_k}_n') for r in file_rows
                      if isinstance(r.get(f'{alg_k}_n'), int)]

            if not counts:
                continue

            avg_g = sum(counts)/len(counts)
            avg_t = sum(times)/len(times) if times else 0
            avg_gap = sum(gaps)/len(gaps) if gaps else None

            gap_str = f'gap medio: +{avg_gap:.2f}' if avg_gap is not None else ''
            lines.append(f'  {alg_name:<30}  '
                         f'guardas: {avg_g:.1f}  '
                         f'tempo: {avg_t:.1f}ms  {gap_str}')

    with open(fname, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'  Sumario guardado: {fname}')
    return fname


# =============================================================
#  MAIN
# =============================================================

# =============================================================
#  BENCHMARK DE COBERTURA PARCIAL
# =============================================================

def run_partial_benchmark(filename, coverages=(70, 80),
                          mac_timeout=30, dp_timeout=15):
    """
    Corre greedy + ILP em modo de cobertura parcial.
    coverages: lista de percentagens de retangulos a cobrir.
    Devolve lista de rows para CSV.
    """
    from greedy import (build_incidence as gi_build,
                        greedy_max_coverage, greedy_by_degree,
                        greedy_random_restarts)
    from Ortools import build_incidence as ot_build, solve_ilp

    instances = parse_file(filename)
    basename  = os.path.basename(filename)
    rows = []

    print(f'\n{"="*62}')
    print(f'  Cobertura Parcial: {basename}')
    print(f'{"="*62}')

    for pct in coverages:
        for i, rectangles in enumerate(instances):
            n_rects = len(rectangles)
            n_target = max(1, int(n_rects * pct / 100))

            # Escolhe os retangulos de menor grau (mais dificeis)
            from collections import defaultdict
            v2r_tmp = defaultdict(set)
            r2v_tmp = {}
            for r, vs in enumerate(rectangles):
                r2v_tmp[r] = list(vs)
                for v in vs:
                    v2r_tmp[v].add(r)

            rects_by_difficulty = sorted(
                r2v_tmp.keys(),
                key=lambda r: min(len(v2r_tmp[v]) for v in r2v_tmp[r])
            )
            target_rects = set(rects_by_difficulty[:n_target])

            row = {
                'ficheiro'  : basename,
                'instancia' : i + 1,
                'n_rects'   : n_rects,
                'cobertura' : pct,
                'n_target'  : n_target,
            }

            # Greedy
            rects_list = [list(r2v_tmp[r]) for r in sorted(r2v_tmp)]
            v2r_g, r2v_g = gi_build(rects_list)
            tgt = set(target_rects)

            t0 = time.perf_counter()
            g1, _, _ = greedy_max_coverage(v2r_g, r2v_g, tgt)
            row['Greedy_MaxCov_n'] = len(g1)
            row['Greedy_MaxCov_ms'] = round((time.perf_counter()-t0)*1000, 3)

            t0 = time.perf_counter()
            g2, _, _ = greedy_by_degree(v2r_g, r2v_g, tgt)
            row['Greedy_Grau_n'] = len(g2)
            row['Greedy_Grau_ms'] = round((time.perf_counter()-t0)*1000, 3)

            t0 = time.perf_counter()
            g3, _, _ = greedy_random_restarts(v2r_g, r2v_g, tgt, n_restarts=30)
            row['Greedy_Aleat_n'] = len(g3)
            row['Greedy_Aleat_ms'] = round((time.perf_counter()-t0)*1000, 3)

            # ILP parcial
            all_verts, vid, rect_corners, _ = ot_build(rectangles)
            target_list = [list(target_rects)]
            t0 = time.perf_counter()
            g_ilp, _ = solve_ilp(rect_corners, len(all_verts),
                                  list(target_rects))
            row['ILP_partial_n']  = len(g_ilp) if g_ilp else None
            row['ILP_partial_ms'] = round((time.perf_counter()-t0)*1000, 3)

            if g_ilp:
                opt = len(g_ilp)
                row['Greedy_MaxCov_gap'] = len(g1) - opt
                row['Greedy_Grau_gap']   = len(g2) - opt
                row['Greedy_Aleat_gap']  = len(g3) - opt

            rows.append(row)
            print(f'  Inst {i+1} ({pct}%) | target={n_target}/{n_rects} | '
                  f'GMax={len(g1)} GGrau={len(g2)} GAleat={len(g3)} '
                  f'ILP={len(g_ilp) if g_ilp else "?"}'
            )

    return rows


CSV_COLS_PARTIAL = [
    'ficheiro', 'instancia', 'n_rects', 'cobertura', 'n_target',
    'ILP_partial_n', 'ILP_partial_ms',
    'Greedy_MaxCov_n', 'Greedy_MaxCov_ms', 'Greedy_MaxCov_gap',
    'Greedy_Grau_n',   'Greedy_Grau_ms',   'Greedy_Grau_gap',
    'Greedy_Aleat_n',  'Greedy_Aleat_ms',  'Greedy_Aleat_gap',
]


# =============================================================
#  MAIN
# =============================================================

DEFAULT_FILES = [
    '../casos_de_teste/inst_small.txt',
    '../casos_de_teste/inst_medium.txt',
    '../casos_de_teste/inst_large.txt',
    '../casos_de_teste/inst_1d.txt',
    '../casos_de_teste/inst_grid.txt',
    '../casos_de_teste/inst_adversarial.txt',
    '../casos_de_teste/inst_original.txt',
]

if __name__ == '__main__':
    args = sys.argv[1:]
    use_mac  = '--mac'     in args or '--all' in args
    run_all  = '--all'     in args
    no_mac   = '--no-mac'  in args
    do_part  = '--partial' in args

    # Determinar ficheiros a processar
    files_to_run = [a for a in args
                    if not a.startswith('--') and os.path.isfile(a)]

    if run_all or not files_to_run:
        files_to_run = [f for f in DEFAULT_FILES if os.path.isfile(f)]
        if not files_to_run:
            print('Nao foram encontrados ficheiros de instancias.')
            print('Execute primeiro:  python generate_instances.py')
            sys.exit(1)

    # Se use_mac nao foi pedido explicitamente, perguntar
    if not use_mac and not no_mac and not run_all:
        ans = input('\nIncluir MAC+AC-3? (lento para >8 rect) [s/N]: ').strip().lower()
        use_mac = ans in ('s', 'y', 'sim', 'yes')

    print(f'\nFicheiros a processar: {files_to_run}')
    print(f'MAC+AC-3: {"SIM (ate 20 rect)" if use_mac else "NAO"}')
    print(f'Prolog:   auto-detectado')
    print(f'Parcial:  {"SIM (70%%, 80%%)" if do_part else "NAO (use --partial)"}')

    all_rows = []
    for fpath in files_to_run:
        rows = run_benchmark(fpath,
                             run_mac_flag=use_mac,
                             run_prolog_flag=True,
                             mac_timeout=60,
                             dp_timeout=20)
        all_rows.extend(rows)

    # Guardar resultados principais
    print_summary_table(all_rows)
    save_csv(all_rows)
    save_summary(all_rows)

    # Cobertura parcial (opcional)
    if do_part:
        partial_rows = []
        for fpath in [f for f in files_to_run
                      if 'large' not in f]:   # large demora muito
            partial_rows.extend(
                run_partial_benchmark(fpath, coverages=(70, 80))
            )
        if partial_rows:
            date_str = datetime.now().strftime('%Y%m%d_%H%M')
            pfname = os.path.join(RESULTS_DIR,
                                  f'partial_{date_str}.csv')
            with open(pfname, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f, fieldnames=CSV_COLS_PARTIAL, extrasaction='ignore')
                writer.writeheader()
                for row in partial_rows:
                    writer.writerow({k: row.get(k, '') for k in CSV_COLS_PARTIAL})
            print(f'\n  Parcial CSV: {pfname}')

    print('\nBenchmark concluido!')
