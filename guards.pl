/*=============================================================
  Vigilância de Partições Retangulares
  Passo 2c — SWI-Prolog com CLP(FD)
  MAD 2025/2026
=============================================================*/

:- use_module(library(clpfd)).


/*-------------------------------------------------------------
  solve(+Rectangles, -Guards, -Cost)

  Rectangles : lista de retângulos, cada um é lista de Vértices
               (índices inteiros 0-based)
  NVerts     : número total de vértices
  Guards     : lista de 0/1 (uma por vértice)
  Cost       : número total de guardas colocados
-------------------------------------------------------------*/

solve(Rectangles, NVerts, Guards, Cost) :-
    % --- Variáveis de decisão: X[v] in {0,1} ---
    length(Guards, NVerts),
    Guards ins 0..1,

    % --- Restrições de cobertura ---
    % Para cada retângulo, a soma dos seus cantos >= 1
    maplist(coverage_constraint(Guards), Rectangles),

    % --- Objectivo: minimizar o número de guardas ---
    sum(Guards, #=, Cost),

    % --- Labeling com minimização ---
    labeling([min(Cost), ff, bisect], Guards).


/*-------------------------------------------------------------
  coverage_constraint(+Guards, +Corners)

  Corners : lista de índices dos vértices do retângulo
  Garante que pelo menos um canto tem guarda.
-------------------------------------------------------------*/

coverage_constraint(Guards, Corners) :-
    maplist(nth0_guard(Guards), Corners, CornerVars),
    sum(CornerVars, #>=, 1).

% nth0_guard(+Lista, +Índice, -Elemento)
nth0_guard(Guards, Idx, G) :-
    nth0(Idx, Guards, G).


/*-------------------------------------------------------------
  Instância de demonstração embutida
  (correspondente ao exemplo do partsRects.py original)

  8 retângulos, vértices 0-15:
    v0=(0,1) v1=(2,1) v2=(2,4) v3=(0,4)  → R0
    v4=(2,3) v5=(3,3) v6=(3,4) v7=(2,4)  → R1
    ...
  Para simplificar, numeramos os vértices únicos 0..15.
-------------------------------------------------------------*/

demo_instance(Rectangles, NVerts) :-
    % Vértices únicos (por ordem de aparição):
    % 0:(0,1) 1:(2,1) 2:(2,4) 3:(0,4) 4:(2,3) 5:(3,3)
    % 6:(3,4) 7:(7,3) 8:(3,1) 9:(7,1) 10:(0,0) 11:(2,0)
    % 12:(5,0) 13:(5,1) 14:(7,4) 15:(7,0)
    NVerts = 16,
    Rectangles = [
        [0,1,2,3],    % R0: (0,1)(2,1)(2,4)(0,4)
        [4,5,6,2],    % R1: (2,3)(3,3)(3,4)(2,4)
        [5,7,14,6],   % R2: (3,3)(7,3)(7,4)(3,4)
        [1,8,5,4],    % R3: (2,1)(3,1)(3,3)(2,3)
        [8,9,7,5],    % R4: (3,1)(7,1)(7,3)(3,3)
        [10,11,1,0],  % R5: (0,0)(2,0)(2,1)(0,1)
        [11,12,13,1], % R6: (2,0)(5,0)(5,1)(2,1)
        [12,15,9,13]  % R7: (5,0)(7,0)(7,1)(5,1)
    ].


/*-------------------------------------------------------------
  solve_demo/0  — resolve a instância de demonstração
-------------------------------------------------------------*/

solve_demo :-
    demo_instance(Rectangles, NVerts),
    nl,
    write('=== Instância de demonstração (8 retângulos) ==='), nl,
    write('A resolver...'), nl,
    statistics(runtime, [T0|_]),
    solve(Rectangles, NVerts, Guards, Cost),
    statistics(runtime, [T1|_]),
    Elapsed is T1 - T0,
    format("Custo óptimo : ~w guardas~n", [Cost]),
    format("Tempo        : ~w ms~n", [Elapsed]),
    write('Guardas (0=sem guarda, 1=com guarda):'), nl,
    print_guards(Guards, 0),
    nl.

print_guards([], _).
print_guards([G|Rest], Idx) :-
    (G =:= 1 -> format("  Vértice ~w : GUARDA~n", [Idx]) ; true),
    Idx1 is Idx + 1,
    print_guards(Rest, Idx1).


/*-------------------------------------------------------------
  Versão de cobertura parcial
  solve_partial(+Rectangles, +NVerts, +TargetIdxs, -Guards, -Cost)
  TargetIdxs: lista de índices dos retângulos a cobrir
-------------------------------------------------------------*/

solve_partial(Rectangles, NVerts, TargetIdxs, Guards, Cost) :-
    length(Guards, NVerts),
    Guards ins 0..1,
    maplist(partial_constraint(Guards, Rectangles), TargetIdxs),
    sum(Guards, #=, Cost),
    labeling([min(Cost), ff, bisect], Guards).

partial_constraint(Guards, Rectangles, RIdx) :-
    nth0(RIdx, Rectangles, Corners),
    coverage_constraint(Guards, Corners).


/*-------------------------------------------------------------
  solve_partial_demo/0 — resolve cobrindo apenas 6 dos 8
-------------------------------------------------------------*/

solve_partial_demo :-
    demo_instance(Rectangles, NVerts),
    TargetIdxs = [0,1,2,3,4,5],   % primeiros 6 retângulos
    nl,
    write('=== Cobertura Parcial (6/8 retângulos) ==='), nl,
    solve_partial(Rectangles, NVerts, TargetIdxs, Guards, Cost),
    format("Custo óptimo : ~w guardas~n", [Cost]),
    write('Guardas:'), nl,
    print_guards(Guards, 0),
    nl.


/*-------------------------------------------------------------
  solve_file(+Filename)
  Lê instâncias do formato gerado pelo gerador Python
  (ficheiro .pl com factos rect/2 e nverts/1)

  Formato esperado do ficheiro .pl:
      nverts(16).
      rect([0,1,2,3]).
      rect([4,5,6,2]).
      ...

  Pode ser gerado com o script export_to_prolog.py
-------------------------------------------------------------*/

solve_file(Filename) :-
    (exists_file(Filename) ->
        consult(Filename),
        findall(R, rect(R), Rectangles),
        nverts(NVerts),
        nl,
        format("Ficheiro: ~w~n", [Filename]),
        format("Retângulos: ~w | Vértices: ~w~n",
               [length(Rectangles,_), NVerts]),
        statistics(runtime, [T0|_]),
        solve(Rectangles, NVerts, Guards, Cost),
        statistics(runtime, [T1|_]),
        Elapsed is T1 - T0,
        format("Custo óptimo: ~w guardas~n", [Cost]),
        format("Tempo: ~w ms~n", [Elapsed]),
        print_guards(Guards, 0)
    ;
        format("ERRO: ficheiro ~w não encontrado.~n", [Filename])
    ).