import math
from typing import List, Tuple


Matriz4 = List[List[float]]
Coordenada3D = Tuple[float, float, float]
Vetor3D = Tuple[float, float, float]

ORIGEM: Coordenada3D = (0.0, 0.0, 0.0)

EIXO_X = "x"
EIXO_Y = "y"
EIXO_Z = "z"


def matriz_identidade() -> Matriz4:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matriz_translacao(dx: float, dy: float, dz: float) -> Matriz4:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [dx, dy, dz, 1.0],
    ]


def matriz_escalonamento(sx: float, sy: float, sz: float) -> Matriz4:
    return [
        [sx, 0.0, 0.0, 0.0],
        [0.0, sy, 0.0, 0.0],
        [0.0, 0.0, sz, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matriz_rotacao_x(angulo_graus: float) -> Matriz4:
    angulo = math.radians(angulo_graus)
    cosseno = math.cos(angulo)
    seno = math.sin(angulo)

    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, cosseno, seno, 0.0],
        [0.0, -seno, cosseno, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matriz_rotacao_y(angulo_graus: float) -> Matriz4:
    angulo = math.radians(angulo_graus)
    cosseno = math.cos(angulo)
    seno = math.sin(angulo)

    return [
        [cosseno, 0.0, -seno, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [seno, 0.0, cosseno, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matriz_rotacao_z(angulo_graus: float) -> Matriz4:
    angulo = math.radians(angulo_graus)
    cosseno = math.cos(angulo)
    seno = math.sin(angulo)

    return [
        [cosseno, seno, 0.0, 0.0],
        [-seno, cosseno, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matriz_rotacao(eixo: str, angulo_graus: float) -> Matriz4:
    if eixo == EIXO_X:
        return matriz_rotacao_x(angulo_graus)

    if eixo == EIXO_Y:
        return matriz_rotacao_y(angulo_graus)

    if eixo == EIXO_Z:
        return matriz_rotacao_z(angulo_graus)

    raise ValueError(f"Eixo desconhecido: {eixo!r}")


def multiplicar(a: Matriz4, b: Matriz4) -> Matriz4:
    resultado = []

    for linha in range(4):
        nova_linha = []

        for coluna in range(4):
            soma = 0.0

            for k in range(4):
                soma += a[linha][k] * b[k][coluna]

            nova_linha.append(soma)

        resultado.append(nova_linha)

    return resultado


def compor(matrizes: List[Matriz4]) -> Matriz4:
    resultado = matriz_identidade()

    for matriz in matrizes:
        resultado = multiplicar(resultado, matriz)

    return resultado


def transformar_ponto(coordenada: Coordenada3D, matriz: Matriz4) -> Coordenada3D:
    x, y, z = coordenada

    novo_x = x * matriz[0][0] + y * matriz[1][0] + z * matriz[2][0] + matriz[3][0]
    novo_y = x * matriz[0][1] + y * matriz[1][1] + z * matriz[2][1] + matriz[3][1]
    novo_z = x * matriz[0][2] + y * matriz[1][2] + z * matriz[2][2] + matriz[3][2]

    return novo_x, novo_y, novo_z


def transformar_vetor(vetor: Vetor3D, matriz: Matriz4) -> Vetor3D:
    x, y, z = vetor

    novo_x = x * matriz[0][0] + y * matriz[1][0] + z * matriz[2][0]
    novo_y = x * matriz[0][1] + y * matriz[1][1] + z * matriz[2][1]
    novo_z = x * matriz[0][2] + y * matriz[1][2] + z * matriz[2][2]

    return novo_x, novo_y, novo_z

def subtrair(a: Vetor3D, b: Vetor3D) -> Vetor3D:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def somar(a: Vetor3D, b: Vetor3D) -> Vetor3D:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def multiplicar_escalar(vetor: Vetor3D, fator: float) -> Vetor3D:
    return vetor[0] * fator, vetor[1] * fator, vetor[2] * fator


def produto_vetorial(a: Vetor3D, b: Vetor3D) -> Vetor3D:
    x = a[1] * b[2] - a[2] * b[1]
    y = a[2] * b[0] - a[0] * b[2]
    z = a[0] * b[1] - a[1] * b[0]

    return x, y, z


def comprimento(vetor: Vetor3D) -> float:
    return math.sqrt(vetor[0] ** 2 + vetor[1] ** 2 + vetor[2] ** 2)


def normalizar(vetor: Vetor3D) -> Vetor3D:
    tamanho = comprimento(vetor)

    if tamanho == 0:
        raise ValueError("Vetor nulo não tem direção.")

    return multiplicar_escalar(vetor, 1 / tamanho)

def preparar_escalonamento_em_torno_de(sx: float, sy: float, sz: float, centro: Coordenada3D) -> Matriz4:
    cx, cy, cz = centro

    return compor([
        matriz_translacao(-cx, -cy, -cz),
        matriz_escalonamento(sx, sy, sz),
        matriz_translacao(cx, cy, cz),
    ])


def preparar_rotacao_em_torno_de(eixo: str, angulo_graus: float, centro: Coordenada3D) -> Matriz4:
    cx, cy, cz = centro

    return compor([
        matriz_translacao(-cx, -cy, -cz),
        matriz_rotacao(eixo, angulo_graus),
        matriz_translacao(cx, cy, cz),
    ])

def preparar_rotacao_eixo_arbitrario(angulo_graus: float, ponto_a: Coordenada3D, ponto_b: Coordenada3D) -> Matriz4:
    direcao = subtrair(ponto_b, ponto_a)

    if comprimento(direcao) == 0:
        raise ValueError("Os dois pontos do eixo precisam ser diferentes.")

    a, b, c = normalizar(direcao)

    angulo_x = math.degrees(math.atan2(-c, b))

    projecao_yz = math.hypot(b, c)
    angulo_z = math.degrees(math.atan2(a, projecao_yz))

    ax, ay, az = ponto_a

    return compor([
        matriz_translacao(-ax, -ay, -az),
        matriz_rotacao_x(angulo_x),
        matriz_rotacao_z(angulo_z),
        matriz_rotacao_y(angulo_graus),
        matriz_rotacao_z(-angulo_z),
        matriz_rotacao_x(-angulo_x),
        matriz_translacao(ax, ay, az),
    ])

class Transformacao3D:

    def matriz(self, centro_objeto: Coordenada3D) -> Matriz4:
        raise NotImplementedError

    def descricao(self) -> str:
        raise NotImplementedError


class Translacao3D(Transformacao3D):

    def __init__(self, dx: float, dy: float, dz: float):
        self.dx = dx
        self.dy = dy
        self.dz = dz

    def matriz(self, centro_objeto: Coordenada3D) -> Matriz4:
        return matriz_translacao(self.dx, self.dy, self.dz)

    def descricao(self) -> str:
        return f"Translação ({self.dx:g}, {self.dy:g}, {self.dz:g})"


class Escalonamento3D(Transformacao3D):

    def __init__(self, sx: float, sy: float, sz: float):
        if sx == 0 or sy == 0 or sz == 0:
            raise ValueError("Os fatores de escala não podem ser zero.")

        self.sx = sx
        self.sy = sy
        self.sz = sz

    def matriz(self, centro_objeto: Coordenada3D) -> Matriz4:
        return preparar_escalonamento_em_torno_de(self.sx, self.sy, self.sz, centro_objeto)

    def descricao(self) -> str:
        return f"Escala ({self.sx:g}, {self.sy:g}, {self.sz:g})"


class RotacaoEixoDoObjeto(Transformacao3D):

    def __init__(self, eixo: str, angulo: float):
        self.eixo = eixo
        self.angulo = angulo

    def matriz(self, centro_objeto: Coordenada3D) -> Matriz4:
        return preparar_rotacao_em_torno_de(self.eixo, self.angulo, centro_objeto)

    def descricao(self) -> str:
        return f"Rotação {self.angulo:g}° em {self.eixo.upper()} (centro do objeto)"


class RotacaoEixoArbitrario(Transformacao3D):

    def __init__(self, angulo: float, ponto_a: Coordenada3D, ponto_b: Coordenada3D):
        if comprimento(subtrair(ponto_b, ponto_a)) == 0:
            raise ValueError("Os dois pontos do eixo precisam ser diferentes.")

        self.angulo = angulo
        self.ponto_a = ponto_a
        self.ponto_b = ponto_b

    def matriz(self, centro_objeto: Coordenada3D) -> Matriz4:
        return preparar_rotacao_eixo_arbitrario(self.angulo, self.ponto_a, self.ponto_b)

    def descricao(self) -> str:
        a = _formatar(self.ponto_a)
        b = _formatar(self.ponto_b)

        return f"Rotação {self.angulo:g}° no eixo {a} → {b}"


def _formatar(coordenada: Coordenada3D) -> str:
    x, y, z = coordenada

    return f"({x:g}, {y:g}, {z:g})"

def matriz_resultante(transformacoes: List[Transformacao3D], centro_original: Coordenada3D) -> Matriz4:
    acumulada = matriz_identidade()

    for transformacao in transformacoes:
        centro_atual = transformar_ponto(centro_original, acumulada)
        acumulada = multiplicar(acumulada, transformacao.matriz(centro_atual))

    return acumulada
