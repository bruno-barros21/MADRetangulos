# Projeto: Vigilância de Partições Retangulares

Este projeto foi organizado de acordo com as diretrizes solicitadas:

## Estrutura do Diretório

* Os ficheiros PDF correspondentes ao relatório encontram-se na raiz do projeto (ex: `3.pdf`, etc.).
* `programas/`: Diretório contendo todo o código-fonte desenvolvido (Python, C, Prolog, etc.).
* `casos_de_teste/`: Diretório contendo as instâncias de teste geradas e utilizadas.
* `README.txt`: Ficheiro atual, contendo as instruções de compilação e execução.

---

## Procedimentos para Execução dos Programas

De modo a garantir que os caminhos para as instâncias de teste e resultados estão corretos, abra o terminal e navegue para dentro da pasta dos programas antes de executar os scripts:

    cd programas

### 1. Benchmark Principal (Python)
Este script testa os algoritmos em todas as instâncias predefinidas e guarda os resultados em ficheiros CSV e de texto na subpasta `programas/results/`.

Para executar com todas as instâncias por omissão (os ficheiros localizados em `casos_de_teste/`):
    python benchmark.py

Para executar com um ficheiro de teste específico:
    python benchmark.py ../casos_de_teste/inst_small.txt

Para incluir o algoritmo MAC+AC-3 (lento em instâncias maiores):
    python benchmark.py ../casos_de_teste/inst_small.txt --mac

### 2. Gerador de Instâncias (Python)
Para regerar os ficheiros de instâncias e guardá-los automaticamente na diretoria `casos_de_teste/`:
    python generate_instances.py

Para ver o modo de demonstração (que imprime na consola sem gravar):
    python generate_instances.py --demo

### 3. Gerador de Partições em C (rectParts.c)
Se pretender compilar o gerador/visualizador original desenvolvido em C:
    gcc rectParts.c -o a.exe

Para o executar, passando o nome dos ficheiros de saída (por exemplo, criando ficheiros locais na pasta programas):
    ./a.exe res resFigs.tex

(O executável produz um ficheiro com os exemplos e, opcionalmente, um ficheiro `.tex` com figuras para LaTeX. Pode depois usar `pdflatex resFigs.tex` para ver as figuras num PDF.)

### 4. Resolução CLP(FD) via Prolog
O benchmark já invoca o Prolog automaticamente usando a biblioteca de subprocessos (desde que o `swipl` esteja instalado e no PATH do sistema). No entanto, pode também executar o Prolog isoladamente se pretender interagir diretamente com os ficheiros `.pl`.
