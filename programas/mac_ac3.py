"""
=============================================================
  Vigilância de Partições Retangulares
  Passo 2b — Backtracking + MAC (AC-3)
  MAD 2025/2026
=============================================================

Implementa:
  - Representação CSP do problema de vigilância
  - AC-3 generalizado para restrições n-árias de cobertura
  - Backtracking com MAC (Maintaining Arc Consistency)
  - Heurísticas: MRV + Degree para selecção de variável
  - Branch-and-Bound para optimização (minimizar guardas)

Uso:
    python mac_ac3.py <ficheiro_resultado>
"""

import sys
import time
import copy
import math
from collections import deque


# =============================================================
#  1. LEITURA DO FICHEIRO  (mesmo formato do greedy_guards.py)
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
    from collections import defaultdict
    vertex_to_rects = defaultdict(set)
    rect_to_verts   = {}
    for r, verts in enumerate(rectangles):
        rect_to_verts[r] = set(verts)
        for v in verts:
            vertex_to_rects[v].add(r)
    return dict(vertex_to_rects), rect_to_verts


# =============================================================
#  2. REPRESENTAÇÃO DO CSP
# =============================================================
#
#  Variáveis : um inteiro por vértice  (índice 0..N-1)
#  Domínio   : {0, 1}  (0 = sem guarda, 1 = com guarda)
#  Restrições: para cada retângulo r,
#              sum_{v in corners(r)} x_v  >=  1
#              → restrição de cobertura n-ária
#
#  A restrição é satisfeita se pelo menos um canto tiver x=1.
#  É INCONSISTENTE se todos os cantos tiverem x=0 no domínio.
#  PROPAGA     se todos menos um canto já estiverem fixos a 0
#              → o último canto OBRIGATORIAMENTE tem x=1.

class CSP:
    """
    Representa o CSP de vigilância.

    Atributos:
        n_vars      : número de variáveis (vértices)
        vid         : dict (x,y) -> int   (coordenadas para índice)
        domains     : list[set]           (domínio de cada variável)
        constraints : list[list[int]]     (cada restrição = lista de índices)
        var_constrs : list[list[int]]     (para cada var, lista de restrições)
    """

    def __init__(self, vertex_to_rects, rect_to_verts, target_rects=None):
        if target_rects is None:
            target_rects = set(rect_to_verts.keys())

        # Mapeia coordenadas -> índice de variável
        all_verts    = sorted(vertex_to_rects.keys())
        self.vid     = {v: i for i, v in enumerate(all_verts)}
        self.vcoords = all_verts          # índice -> coordenadas
        self.n_vars  = len(all_verts)

        # Domínios iniciais: {0, 1} para todos
        self.domains = [set([0, 1]) for _ in range(self.n_vars)]

        # Restrições: uma por retângulo alvo
        # cada restrição é lista de índices dos cantos
        self.constraints  = []
        self.var_constrs  = [[] for _ in range(self.n_vars)]

        for r in target_rects:
            corners = [self.vid[v] for v in rect_to_verts[r]]
            cid     = len(self.constraints)
            self.constraints.append(corners)
            for vi in corners:
                self.var_constrs[vi].append(cid)

    def is_assigned(self, domains, vi):
        return len(domains[vi]) == 1

    def value(self, domains, vi):
        return next(iter(domains[vi]))

    def clone_domains(self, domains):
        return [set(d) for d in domains]


# =============================================================
#  3. AC-3 GENERALIZADO
# =============================================================
#
#  Para restrições de cobertura n-árias:
#    Propaga restrição C quando uma variável em C muda:
#      - Conta quantos cantos têm 0 no domínio (forçados a 0)
#        e quantos ainda têm {0,1}
#      - Se todos estão forçados a 0 → INCONSISTÊNCIA
#      - Se todos menos UM estão forçados a 0
#        → o restante é forçado a 1 (remover 0 do seu domínio)
#
#  A fila contém IDs de restrições a re-verificar.

def ac3(csp, domains, initial_constraints=None):
    """
    Executa AC-3 generalizado.

    Parâmetros:
        csp                : instância de CSP
        domains            : estado actual dos domínios (modificado in-place)
        initial_constraints: restrições a colocar na fila inicialmente;
                             None → todas as restrições

    Devolve:
        True  se os domínios são ainda consistentes
        False se foi detectada uma inconsistência
    """
    if initial_constraints is None:
        queue = deque(range(len(csp.constraints)))
    else:
        queue = deque(initial_constraints)

    in_queue = set(queue)

    while queue:
        cid     = queue.popleft()
        in_queue.discard(cid)
        corners = csp.constraints[cid]

        # Classifica cada canto
        forced_zero  = []   # domínio = {0}
        forced_one   = []   # domínio = {1}
        free         = []   # domínio = {0,1}

        for vi in corners:
            d = domains[vi]
            if d == {1}:
                forced_one.append(vi)
            elif d == {0}:
                forced_zero.append(vi)
            else:
                free.append(vi)

        # Se algum canto já tem 1 → restrição satisfeita, sem propagação
        if forced_one:
            continue

        n_free = len(free)
        n_zero = len(forced_zero)

        # Todos forçados a 0 → INCONSISTÊNCIA
        if n_free == 0 and not forced_one:
            return False

        # Exactamente um canto livre, todos os outros a 0
        # → esse canto TEM de ser 1
        if n_free == 1 and n_zero == len(corners) - 1:
            vi = free[0]
            if 0 in domains[vi]:
                domains[vi].discard(0)   # forçar a 1
                # Propagar: re-enfileirar restrições que envolvem vi
                for c2 in csp.var_constrs[vi]:
                    if c2 not in in_queue:
                        queue.append(c2)
                        in_queue.add(c2)

    return True


# =============================================================
#  4. HEURÍSTICAS DE SELECÇÃO DE VARIÁVEL
# =============================================================

def select_variable_mrv(domains, csp, assigned):
    """
    MRV (Minimum Remaining Values) + Degree como desempate.

    Escolhe a variável não atribuída com menor domínio.
    Em caso de empate, prefere a de maior grau (mais restrições).
    """
    best_v    = -1
    best_size =  3      # domínios são no máximo {0,1} → tamanho 2
    best_deg  = -1

    for vi in range(csp.n_vars):
        if vi in assigned:
            continue
        sz  = len(domains[vi])
        deg = len(csp.var_constrs[vi])
        if sz < best_size or (sz == best_size and deg > best_deg):
            best_v    = vi
            best_size = sz
            best_deg  = deg

    return best_v


# =============================================================
#  5. BACKTRACKING COM MAC
# =============================================================

class Solver:
    def __init__(self, csp):
        self.csp       = csp
        self.best      = None     # melhor solução encontrada (lista de vi=1)
        self.best_cost = float('inf')
        self.nodes     = 0        # nós explorados

    def solve(self):
        """
        Lança o backtracking com MAC sobre o CSP.
        Devolve a solução óptima (mínimo de guardas).
        """
        initial_domains = self.csp.clone_domains(self.csp.domains)

        # Propagação inicial
        if not ac3(self.csp, initial_domains):
            return None   # instância infactível

        self._backtrack(initial_domains, assigned={}, n_guards=0)
        return self.best

    def _backtrack(self, domains, assigned, n_guards):
        self.nodes += 1

        # --- Poda por bound ---
        # Lower bound: n_guards actuais + mínimo adicional estimado
        # (cada restrição não satisfeita precisa de pelo menos 1 guarda)
        lb = n_guards + self._lower_bound(domains, assigned)
        if lb >= self.best_cost:
            return

        # --- Verificar se todas as variáveis estão atribuídas ---
        if len(assigned) == self.csp.n_vars:
            cost = n_guards
            if cost < self.best_cost:
                self.best_cost = cost
                self.best = [vi for vi, val in assigned.items() if val == 1]
            return

        # --- Selecção de variável (MRV + Degree) ---
        vi = select_variable_mrv(domains, self.csp, assigned)
        if vi == -1:
            return

        # --- Ordenação de valores: tentar 0 primeiro (menos guardas) ---
        values = sorted(domains[vi], reverse=False)  # 0 antes de 1

        for val in values:
            # Criar cópia dos domínios
            new_domains = self.csp.clone_domains(domains)
            new_domains[vi] = {val}

            new_assigned  = dict(assigned)
            new_assigned[vi] = val
            new_guards    = n_guards + val

            # Propagação MAC (AC-3 com as restrições de vi)
            constrs_to_check = list(self.csp.var_constrs[vi])
            consistent = ac3(self.csp, new_domains, constrs_to_check)

            if consistent:
                # Atribuir as variáveis forçadas pelo AC-3
                new_assigned2, new_guards2 = self._collect_forced(
                    new_domains, new_assigned, new_guards)

                self._backtrack(new_domains, new_assigned2, new_guards2)

    def _collect_forced(self, domains, assigned, n_guards):
        """
        Após AC-3, algumas variáveis podem ter ficado com domínio
        singleton sem terem sido explicitamente atribuídas.
        Recolhe-as para o dicionário assigned.
        """
        new_assigned = dict(assigned)
        new_guards   = n_guards
        for vi in range(self.csp.n_vars):
            if vi not in new_assigned and len(domains[vi]) == 1:
                val = next(iter(domains[vi]))
                new_assigned[vi] = val
                new_guards += val
        return new_assigned, new_guards

    def _lower_bound(self, domains, assigned):
        """
        Bound fraccional: ceil(|restrições não satisfeitas| / cobertura_máx).

        Para cada restrição não satisfeita, conta as variáveis livres
        que a podem satisfazer. O bound = ceil(n_unsat / max_coverage)
        onde max_coverage é o máximo de restrições que qualquer variável
        livre pode satisfazer de uma só vez.
        """
        unsat_free = []  # para cada restrição não sat., conjunto de vars livres
        for corners in self.csp.constraints:
            # Satisfeita se algum canto tem valor 1 (forçado ou atribuído)
            if any(domains[vi] == {1} for vi in corners):
                continue
            # Inviável se nenhum canto pode ser 1
            free = [vi for vi in corners if 1 in domains[vi]]
            if not free:
                return math.inf   # inconsistência detectada
            unsat_free.append(set(free))

        if not unsat_free:
            return 0

        # Cobertura máxima de qualquer variável livre
        all_free = set()
        for s in unsat_free:
            all_free |= s
        if not all_free:
            return len(unsat_free)

        max_cov = max(
            sum(1 for s in unsat_free if vi in s)
            for vi in all_free
        )
        if max_cov == 0:
            return len(unsat_free)

        return math.ceil(len(unsat_free) / max_cov)


# =============================================================
#  6. COMPARAÇÃO: ILP via OR-Tools
# =============================================================

def solve_ilp(vertex_to_rects, rect_to_verts, target_rects=None):
    try:
        from ortools.linear_solver import pywraplp
    except ImportError:
        return None, 0

    if target_rects is None:
        target_rects = set(rect_to_verts.keys())

    solver = pywraplp.Solver.CreateSolver('SCIP')
    verts  = list(vertex_to_rects.keys())
    x      = {v: solver.IntVar(0, 1, str(v)) for v in verts}

    for r in target_rects:
        solver.Add(sum(x[v] for v in rect_to_verts[r]) >= 1)

    solver.Minimize(sum(x.values()))
    t0     = time.time()
    status = solver.Solve()
    elapsed = time.time() - t0

    if status == pywraplp.Solver.OPTIMAL:
        return [v for v in verts if x[v].solution_value() > 0.5], elapsed
    return None, elapsed


# =============================================================
#  7. PONTO DE ENTRADA
# =============================================================

def run(filename):
    instances = parse_partition_file(filename)
    print(f"\nFicheiro : {filename}")
    print(f"Instâncias: {len(instances)}\n")

    for i, rectangles in enumerate(instances):
        v2r, r2v = build_incidence(rectangles)
        n_rects   = len(rectangles)

        print(f"{'='*60}")
        print(f"  Instância {i+1}  |  {n_rects} retângulos  "
              f"|  {len(v2r)} vértices")
        print(f"{'='*60}")

        # --- MAC + AC-3 ---
        global csp
        csp    = CSP(v2r, r2v)
        solver = Solver(csp)

        t0       = time.time()
        solution = solver.solve()
        t_mac    = (time.time() - t0) * 1000

        if solution is not None:
            n_mac = len(solution)
            coords = sorted(csp.vcoords[vi] for vi in solution)
            print(f"\n  MAC + AC-3")
            print(f"    Guardas  : {n_mac}")
            print(f"    Posições : {coords}")
            print(f"    Nós BT   : {solver.nodes}")
            print(f"    Tempo    : {t_mac:.2f} ms")
        else:
            print("  MAC + AC-3: sem solução")

        # --- ILP ---
        g_ilp, t_ilp = solve_ilp(v2r, r2v)
        if g_ilp is not None:
            print(f"\n  ILP (SCIP)")
            print(f"    Guardas  : {len(g_ilp)}")
            print(f"    Tempo    : {t_ilp*1000:.2f} ms")

        # --- Gap ---
        if solution is not None and g_ilp is not None:
            gap = n_mac - len(g_ilp)
            print(f"\n  Gap MAC vs ILP : {gap:+d} guardas "
                  f"({'óptimo' if gap==0 else 'supra-óptimo'})")

        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python mac_ac3.py <ficheiro_resultado>")
        sys.exit(1)
    run(sys.argv[1])