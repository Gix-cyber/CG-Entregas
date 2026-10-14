import math
from typing import List

from sgi.objetos import Coordenada, ObjetoGrafico


# matriz 3x3 em coordenadas homogeneas. Convencao de vetor linha: [x y 1] * M,
# ent a translacao fica na ultima linha e a composicao é M1 * M2 * ... na ordem de aplicacao
Matriz = List[List[float]]


def matriz_identidade() -> Matriz:
    return [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]


def matriz_translacao(dx: float, dy: float) -> Matriz:
    return [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [dx, dy, 1.0],
    ]


def matriz_escalonamento(sx: float, sy: float) -> Matriz:
    return [
        [sx, 0.0, 0.0],
        [0.0, sy, 0.0],
        [0.0, 0.0, 1.0],
    ]


#angulo positivo gira no sentido anti-horario, igual no blender
def matriz_rotacao(angulo_graus: float) -> Matriz:
    angulo = math.radians(angulo_graus)
    cosseno = math.cos(angulo)
    seno = math.sin(angulo)

    return [
        [cosseno, seno, 0.0],
        [-seno, cosseno, 0.0],
        [0.0, 0.0, 1.0],
    ]


def multiplicar(a: Matriz, b: Matriz) -> Matriz:
    resultado = []

    for linha in range(3):
        nova_linha = []

        for coluna in range(3):
            soma = 0.0

            for k in range(3):
                soma += a[linha][k] * b[k][coluna]

            nova_linha.append(soma)

        resultado.append(nova_linha)

    return resultado


def compor(matrizes: List[Matriz]) -> Matriz:
    resultado = matriz_identidade()

    for matriz in matrizes:
        resultado = multiplicar(resultado, matriz)

    return resultado


def transformar_ponto(coordenada: Coordenada, matriz: Matriz) -> Coordenada:
    x, y = coordenada

    novo_x = x * matriz[0][0] + y * matriz[1][0] + matriz[2][0]
    novo_y = x * matriz[0][1] + y * matriz[1][1] + matriz[2][1]

    return novo_x, novo_y


#rotina generica: aplica a matriz em todas as coordenadas do obj e devolve ele
def transformar(objeto: ObjetoGrafico, matriz: Matriz) -> ObjetoGrafico:
    novas_coordenadas = []

    for coordenada in objeto.coordenadas:
        novas_coordenadas.append(transformar_ponto(coordenada, matriz))

    objeto.coordenadas = novas_coordenadas

    return objeto


# ---- rotinas de preparo da matriz ----


def preparar_translacao(dx: float, dy: float) -> Matriz:
    return matriz_translacao(dx, dy)


def preparar_rotacao_em_torno_de(angulo_graus: float, centro: Coordenada) -> Matriz:
    cx, cy = centro

    return compor([
        matriz_translacao(-cx, -cy),
        matriz_rotacao(angulo_graus),
        matriz_translacao(cx, cy),
    ])


def preparar_escalonamento_em_torno_de(sx: float, sy: float, centro: Coordenada) -> Matriz:
    cx, cy = centro

    return compor([
        matriz_translacao(-cx, -cy),
        matriz_escalonamento(sx, sy),
        matriz_translacao(cx, cy),
    ])


# ---- transformacoes que o usuario enfileira na interface ----
# cada uma sabe preparar sua matriz a partir do centro atual do obj


class Transformacao:

    def matriz(self, centro_objeto: Coordenada) -> Matriz:
        raise NotImplementedError

    def descricao(self) -> str:
        raise NotImplementedError


class Translacao(Transformacao):

    def __init__(self, dx: float, dy: float):
        self.dx = dx
        self.dy = dy

    def matriz(self, centro_objeto: Coordenada) -> Matriz:
        return preparar_translacao(self.dx, self.dy)

    def descricao(self) -> str:
        return f"Translação ({self.dx:g}, {self.dy:g})"


class Escalonamento(Transformacao):
    #escalonamento natural, em torno do centro do obj

    def __init__(self, sx: float, sy: float):
        if sx == 0 or sy == 0:
            raise ValueError("Os fatores de escala não podem ser zero.")

        self.sx = sx
        self.sy = sy

    def matriz(self, centro_objeto: Coordenada) -> Matriz:
        return preparar_escalonamento_em_torno_de(self.sx, self.sy, centro_objeto)

    def descricao(self) -> str:
        return f"Escala ({self.sx:g}, {self.sy:g})"


class RotacaoCentroMundo(Transformacao):

    def __init__(self, angulo: float):
        self.angulo = angulo

    def matriz(self, centro_objeto: Coordenada) -> Matriz:
        return preparar_rotacao_em_torno_de(self.angulo, (0.0, 0.0))

    def descricao(self) -> str:
        return f"Rotação {self.angulo:g}° (centro do mundo)"


class RotacaoCentroObjeto(Transformacao):

    def __init__(self, angulo: float):
        self.angulo = angulo

    def matriz(self, centro_objeto: Coordenada) -> Matriz:
        return preparar_rotacao_em_torno_de(self.angulo, centro_objeto)

    def descricao(self) -> str:
        return f"Rotação {self.angulo:g}° (centro do objeto)"


class RotacaoPontoArbitrario(Transformacao):

    def __init__(self, angulo: float, ponto: Coordenada):
        self.angulo = angulo
        self.ponto = ponto

    def matriz(self, centro_objeto: Coordenada) -> Matriz:
        return preparar_rotacao_em_torno_de(self.angulo, self.ponto)

    def descricao(self) -> str:
        px, py = self.ponto

        return f"Rotação {self.angulo:g}° em ({px:g}, {py:g})"


#monta a matriz resultante de toda a lista, so depois do usuario terminar de enfileirar.
#o centro do obj muda a cada passo, mas como as transf sao afins o centro novo é
#so o centro original passado pela matriz acumulada, ent n precisa mexer no obj
def matriz_resultante(transformacoes: List[Transformacao], objeto: ObjetoGrafico) -> Matriz:
    acumulada = matriz_identidade()
    centro_original = objeto.centro()

    for transformacao in transformacoes:
        centro_atual = transformar_ponto(centro_original, acumulada)
        acumulada = multiplicar(acumulada, transformacao.matriz(centro_atual))

    return acumulada
