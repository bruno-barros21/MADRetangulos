import sys, os, subprocess
from benchmark import parse_file, _find_swipl
from Ortools import export_to_prolog

instances = parse_file('inst_small.txt')
rectangles = instances[0]
swipl = _find_swipl()

export_to_prolog(rectangles, 'test_inst', filename='_tmp_bench_test_inst.pl')

goal = "consult('_tmp_bench_test_inst.pl'), consult('guards.pl'), findall(R, rect(R), Rects), nverts(NV), solve(Rects, NV, Guards, Cost), format('COST:~w~n',[Cost]), halt."

proc = subprocess.run([swipl, '-q', '-g', goal], capture_output=True, text=True)
print('STDOUT:', proc.stdout)
print('STDERR:', proc.stderr)
