"""
=============================================================
  Gerador de Particoes Retangulares -- Python puro
  MAD 2025/2026
=============================================================

Replica a logica do rectParts.c sem necessitar de compilar C.
Usa uma representacao simples baseada em linhas de grade (grid lines)
e cortes aleatorios (horizontal/vertical) com distribuicao geometrica.

Gera varios grupos de instancias para teste sistematico:
  - inst_small.txt   :  4-8  retangulos  (10 instancias)
  - inst_medium.txt  : 10-20 retangulos  (10 instancias)
  - inst_large.txt   : 25-60 retangulos  ( 5 instancias)
  - inst_1d.txt      : fila 1D, 5-20     ( 5 instancias)
  - inst_grid.txt    : grelha NxM        ( 6 instancias)

Formato de saida (identico ao ficheiro 'res' do a.exe):
    <n_instancias>
    <n_retangulos>
    <face_id> <n_verts> x1 y1 x2 y2 ... xn yn
    ...
    <n_retangulos>
    ...

Uso:
    python generate_instances.py          # gera todos os grupos
    python generate_instances.py --demo   # mostra exemplo
"""

import random
import math
import sys
import os


# =============================================================
#  1. REPRESENTACAO DA PARTICAO COMO GRELHA DE LINHAS
# =============================================================
#
#  Mantemos a particao como um conjunto de rectangulos axis-aligned,
#  cada um definido por (xl, xr, yb, yt) -- coordenadas inteiras.
#  A cada corte (horizontal ou vertical) subdivide-se um ou mais
#  rectangulos existentes ao longo dessa linha.

class Partition:
    """
    Representa uma particao retangular como lista de rectangulos.
    Cada rectangulo: (xl, xr, yb, yt)  com xl<xr, yb<yt.
    """

    def __init__(self, W=1000, H=1000):
        self.W = W
        self.H = H
        self.rects = [(0, W, 0, H)]

    def n_rects(self):
        return len(self.rects)

    def cut_vertical(self, x):
        """Corte vertical em x: divide todos os rects que cruzam x."""
        new_rects = []
        changed = False
        for (xl, xr, yb, yt) in self.rects:
            if xl < x < xr:
                new_rects.append((xl, x, yb, yt))
                new_rects.append((x, xr, yb, yt))
                changed = True
            else:
                new_rects.append((xl, xr, yb, yt))
        if changed:
            self.rects = new_rects
        return changed

    def cut_horizontal(self, y):
        """Corte horizontal em y: divide todos os rects que cruzam y."""
        new_rects = []
        changed = False
        for (xl, xr, yb, yt) in self.rects:
            if yb < y < yt:
                new_rects.append((xl, xr, yb, y))
                new_rects.append((xl, xr, y, yt))
                changed = True
            else:
                new_rects.append((xl, xr, yb, yt))
        if changed:
            self.rects = new_rects
        return changed


# =============================================================
#  2. GERACAO ALEATORIA  (replica rectParts.c)
# =============================================================

TAU = 0.75   # parametro da distribuicao geometrica (igual ao C)


def geom_sample(n, tau=TAU, rng=None):
    """
    Amostra de distribuicao geometrica truncada em [1..n].
    Formula do rectParts.c:
        k = 1 + floor(log(1 - p + p^n) / log(tau))
    onde p ~ U(0,1).
    """
    if rng is None:
        rng = random
    if n <= 0:
        return 1
    p = rng.random()
    if p == 0:
        return 1
    val = math.log(max(1e-15, 1.0 - p + p ** n)) / math.log(tau)
    k = 1 + int(val)
    return max(1, min(k, n))


def generate_random_partition(n_rects_target, rng=None, W=None, H=None,
                               max_attempts=5000):
    """
    Gera uma particao retangular aleatoria com aproximadamente
    n_rects_target rectangulos.

    Estrategia:
      - Comeca com 1 rectangulo [0,W]x[0,H]
      - A cada passo escolhe aleatoriamente H ou V
      - Escolhe aleatoriamente uma posicao de corte
      - Para quando tiver n_rects_target rectangulos

    Usa coordenadas inteiras para garantir vertices inteiros.
    Para ter suficientes posicoes de corte, usa W=H = 10 * n_rects_target.
    """
    if rng is None:
        rng = random.Random()

    if W is None:
        W = max(20, n_rects_target * 5)
    if H is None:
        H = max(20, n_rects_target * 5)

    part = Partition(W, H)

    attempts = 0
    while part.n_rects() < n_rects_target and attempts < max_attempts:
        attempts += 1
        direction = rng.randint(0, 1)   # 0=vertical, 1=horizontal

        if direction == 0:
            # Obter todas as coordenadas x existentes
            xs = sorted(set(r[0] for r in part.rects) |
                        set(r[1] for r in part.rects))
            # Intervalos disponiveis (pares consecutivos com largura > 1)
            intervals = [(xs[i], xs[i+1]) for i in range(len(xs)-1)
                         if xs[i+1] - xs[i] > 1]
            if not intervals:
                continue
            # Escolher intervalo com distribuicao geometrica
            k = geom_sample(len(intervals), rng=rng)
            xl_z, xr_z = intervals[k - 1]
            x_cut = rng.randint(xl_z + 1, xr_z - 1)
            part.cut_vertical(x_cut)
        else:
            ys = sorted(set(r[2] for r in part.rects) |
                        set(r[3] for r in part.rects))
            intervals = [(ys[i], ys[i+1]) for i in range(len(ys)-1)
                         if ys[i+1] - ys[i] > 1]
            if not intervals:
                continue
            k = geom_sample(len(intervals), rng=rng)
            yb_z, yt_z = intervals[k - 1]
            y_cut = rng.randint(yb_z + 1, yt_z - 1)
            part.cut_horizontal(y_cut)

    return part


def _normalise_coords(rects):
    """
    Remapeia as coordenadas para [0..K] com inteiros consecutivos,
    tal como o C original (coordenadas de grelha normalizadas).
    """
    xs = sorted(set(r[0] for r in rects) | set(r[1] for r in rects))
    ys = sorted(set(r[2] for r in rects) | set(r[3] for r in rects))
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}
    return [
        (xi[xl], xi[xr], yi[yb], yi[yt])
        for (xl, xr, yb, yt) in rects
    ]


def rect_to_vertices_ccw(xl, xr, yb, yt):
    """
    Converte bounding-box para lista de 4 vertices em sentido CCW
    (SW -> SE -> NE -> NW), como o DCEL do rectParts.c.
    """
    return [(xl, yb), (xr, yb), (xr, yt), (xl, yt)]


# =============================================================
#  3. INSTANCIAS ESPECIAIS
# =============================================================

def generate_1d_row(n):
    """Fila de n rectangulos horizontais lado a lado."""
    return [(i, i + 1, 0, 1) for i in range(n)]


def generate_grid(rows, cols):
    """Grelha rows x cols de rectangulos unitarios."""
    rects = []
    for r in range(rows):
        for c in range(cols):
            rects.append((c, c + 1, r, r + 1))
    return rects


# =============================================================
#  4. VERIFICACAO BASICA
# =============================================================

def verify_partition(rects):
    """
    Verifica que os rectangulos cobrem exactamente [0,Xmax]x[0,Ymax]
    sem sobreposicao (area total = soma das areas).
    """
    if not rects:
        return False
    total_area = sum((xr - xl) * (yt - yb) for (xl, xr, yb, yt) in rects)
    xmax = max(xr for (_, xr, _, _) in rects)
    ymax = max(yt for (_, _, _, yt) in rects)
    xmin = min(xl for (xl, _, _, _) in rects)
    ymin = min(yb for (_, _, yb, _) in rects)
    expected = (xmax - xmin) * (ymax - ymin)
    return abs(total_area - expected) < 1e-9


# =============================================================
#  5. ESCRITA NO FORMATO DO res / a.exe
# =============================================================

def write_instances(instances_list, filename):
    """
    Escreve uma lista de instancias no formato do ficheiro 'res'.

    instances_list: lista de listas de rects (xl,xr,yb,yt)
    """
    lines = [str(len(instances_list))]
    for rects in instances_list:
        norm = _normalise_coords(rects)
        lines.append(str(len(norm)))
        for fid, (xl, xr, yb, yt) in enumerate(norm, start=1):
            verts = rect_to_vertices_ccw(xl, xr, yb, yt)
            coords = ' '.join(f'{x} {y}' for (x, y) in verts)
            lines.append(f'{fid} {len(verts)} {coords}')
    with open(filename, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    n_rects = [len(_normalise_coords(r)) for r in instances_list]
    print(f'  Escrito: {filename}  '
          f'({len(instances_list)} instancias, '
          f'rect: {min(n_rects)}-{max(n_rects)})')


# =============================================================
#  6. GERACAO DOS GRUPOS
# =============================================================

def generate_all(seed=2025, output_dir='.'):
    """Gera todos os grupos de instancias para o relatorio."""
    rng = random.Random(seed)
    os.makedirs(output_dir, exist_ok=True)

    def path(name):
        return os.path.join(output_dir, name)

    # ── SMALL: 4-8 retangulos, 10 instancias ──────────────────
    print('\n[1/5] Instancias pequenas (4-8 rect, 10 instancias)...')
    sizes_s = [4, 5, 5, 6, 6, 6, 7, 7, 8, 8]
    small = []
    for n in sizes_s:
        p = generate_random_partition(n, rng=rng)
        small.append(p.rects)
        ok = verify_partition(p.rects)
        actual = len(p.rects)
        if actual != n or not ok:
            print(f'    AVISO: target={n}, obtidos={actual}, valido={ok}')
    write_instances(small, path('inst_small.txt'))

    # ── MEDIUM: 10-20 retangulos, 10 instancias ───────────────
    print('\n[2/5] Instancias medias (10-20 rect, 10 instancias)...')
    sizes_m = [10, 10, 12, 12, 14, 15, 15, 17, 18, 20]
    medium = []
    for n in sizes_m:
        p = generate_random_partition(n, rng=rng)
        medium.append(p.rects)
    write_instances(medium, path('inst_medium.txt'))

    # ── LARGE: 25-60 retangulos, 5 instancias ─────────────────
    print('\n[3/5] Instancias grandes (25-60 rect, 5 instancias)...')
    sizes_l = [25, 30, 40, 50, 60]
    large = []
    for n in sizes_l:
        p = generate_random_partition(n, rng=rng)
        large.append(p.rects)
    write_instances(large, path('inst_large.txt'))

    # ── 1D: filas de 5-20 retangulos, 5 instancias ────────────
    print('\n[4/5] Instancias 1D (filas, 5-20 rect, 5 instancias)...')
    sizes_1d = [5, 8, 10, 15, 20]
    inst_1d = [generate_1d_row(n) for n in sizes_1d]
    write_instances(inst_1d, path('inst_1d.txt'))

    # ── GRID: grelhas NxM, 6 instancias ───────────────────────
    print('\n[5/5] Instancias grelha NxM (6 instancias)...')
    grid_sizes = [(2, 2), (2, 3), (3, 3), (3, 4), (4, 4), (5, 4)]
    inst_grid = [generate_grid(r, c) for (r, c) in grid_sizes]
    write_instances(inst_grid, path('inst_grid.txt'))

    # ── Re-escreve as instancias do 'res' original ────────────
    print('\n[+] Copiando instancias originais de "res"...')
    _copy_res_if_exists(output_dir)

    print('\nGeracao concluida!')
    _print_summary(output_dir)


def _copy_res_if_exists(output_dir):
    src = 'res'
    dst = os.path.join(output_dir, 'inst_original.txt')
    if os.path.exists(src):
        import shutil
        shutil.copy2(src, dst)
        print(f'  Copiado: res -> {dst}')
    else:
        print('  Ficheiro "res" nao encontrado, a ignorar.')


def _print_summary(output_dir):
    files = [
        ('inst_small.txt',    'Pequenas (4-8 rect)'),
        ('inst_medium.txt',   'Medias (10-20 rect)'),
        ('inst_large.txt',    'Grandes (25-60 rect)'),
        ('inst_1d.txt',       '1D (filas)'),
        ('inst_grid.txt',     'Grelha NxM'),
        ('inst_original.txt', 'Original (res)'),
    ]
    print(f'\n{"="*58}')
    print(f'  {"Ficheiro":<25} {"Tipo":<28} N')
    print(f'  {"-"*55}')
    for fname, desc in files:
        fp = os.path.join(output_dir, fname)
        if os.path.exists(fp):
            with open(fp) as f:
                n = int(f.readline().strip())
            print(f'  {fname:<25} {desc:<28} {n}')
    print(f'{"="*58}')


# =============================================================
#  7. DEMO
# =============================================================

def demo():
    print('\n' + '='*55)
    print('  DEMO -- Gerador de Particoes Retangulares')
    print('='*55)

    rng = random.Random(0)
    for n in [5, 8]:
        part = generate_random_partition(n, rng=rng)
        norm = _normalise_coords(part.rects)
        ok = verify_partition(part.rects)
        print(f'\n  Target={n}  Obtidos={len(norm)}  Valido={ok}')
        for fid, (xl, xr, yb, yt) in enumerate(norm, 1):
            verts = rect_to_vertices_ccw(xl, xr, yb, yt)
            print(f'    R{fid}: {verts}')

    print('\n  Grelha 2x3:')
    g = generate_grid(2, 3)
    for fid, (xl, xr, yb, yt) in enumerate(_normalise_coords(g), 1):
        print(f'    R{fid}: ({xl},{yb})->({xr},{yt})')

    print('\n  Fila 1D com 5 rects:')
    r1d = generate_1d_row(5)
    for fid, (xl, xr, yb, yt) in enumerate(_normalise_coords(r1d), 1):
        print(f'    R{fid}: ({xl},{yb})->({xr},{yt})')


# =============================================================
#  MAIN
# =============================================================

if __name__ == '__main__':
    if '--demo' in sys.argv:
        demo()
    else:
        generate_all(seed=2025)
