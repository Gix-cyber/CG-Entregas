from typing import Callable, Dict, List, Tuple

from sgi.objetos import COR_PADRAO, Coordenada, CorRGB, ObjetoGrafico
from sgi.transformacoes3d import (
    Coordenada3D,
    Matriz4,
    matriz_escalonamento,
    matriz_rotacao_x,
    matriz_rotacao_y,
    matriz_rotacao_z,
    matriz_translacao,
    preparar_escalonamento_em_torno_de,
    preparar_rotacao_em_torno_de,
    preparar_rotacao_eixo_arbitrario,
    transformar_ponto,
)


class Ponto3D:

    def __init__(self, x: float, y: float, z: float):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def como_tupla(self) -> Coordenada3D:
        return self.x, self.y, self.z

    def transformar(self, matriz: Matriz4) -> "Ponto3D":
        self.x, self.y, self.z = transformar_ponto(self.como_tupla(), matriz)

        return self

    def transladar(self, dx: float, dy: float, dz: float) -> "Ponto3D":
        return self.transformar(matriz_translacao(dx, dy, dz))

    def escalonar(self, sx: float, sy: float, sz: float) -> "Ponto3D":
        return self.transformar(matriz_escalonamento(sx, sy, sz))

    def rotacionar_x(self, angulo_graus: float) -> "Ponto3D":
        return self.transformar(matriz_rotacao_x(angulo_graus))

    def rotacionar_y(self, angulo_graus: float) -> "Ponto3D":
        return self.transformar(matriz_rotacao_y(angulo_graus))

    def rotacionar_z(self, angulo_graus: float) -> "Ponto3D":
        return self.transformar(matriz_rotacao_z(angulo_graus))

    def __repr__(self) -> str:
        return f"Ponto3D({self.x:g}, {self.y:g}, {self.z:g})"


Segmento3D = Tuple[Ponto3D, Ponto3D]


class Objeto3D(ObjetoGrafico):
    tipo = "objeto 3d"

    def __init__(self, nome: str, segmentos: List[Tuple[Coordenada3D, Coordenada3D]], cor: CorRGB = COR_PADRAO):
        if len(segmentos) == 0:
            raise ValueError("Um objeto 3D precisa de pelo menos 1 segmento.")

        super().__init__(nome, [], cor)

        self.segmentos_3d: List[Segmento3D] = []

        for inicio, fim in segmentos:
            self.segmentos_3d.append((_novo_ponto(inicio), _novo_ponto(fim)))

    def descricao(self) -> str:
        quantidade = len(self.segmentos_3d)

        if quantidade == 1:
            return f"{self.nome} ({self.tipo}, 1 segmento)"

        return f"{self.nome} ({self.tipo}, {quantidade} segmentos)"

    def coordenadas_3d(self) -> List[Coordenada3D]:
        coordenadas = []

        for inicio, fim in self.segmentos_3d:
            coordenadas.append(inicio.como_tupla())
            coordenadas.append(fim.como_tupla())

        return coordenadas

    #vertices sem repeticao, na ordem em q aparecem
    def vertices(self) -> List[Coordenada3D]:
        unicos = []

        for coordenada in self.coordenadas_3d():
            if coordenada not in unicos:
                unicos.append(coordenada)

        return unicos

    def centro(self) -> Coordenada3D:
        vertices = self.vertices()
        quantidade = len(vertices)
        soma_x = 0.0
        soma_y = 0.0
        soma_z = 0.0

        for x, y, z in vertices:
            soma_x += x
            soma_y += y
            soma_z += z

        return soma_x / quantidade, soma_y / quantidade, soma_z / quantidade

    def _segmentos_de(self, coordenadas: List[Coordenada]) -> List[Tuple[Coordenada, Coordenada]]:
        segmentos = []

        for indice in range(0, len(coordenadas) - 1, 2):
            segmentos.append((coordenadas[indice], coordenadas[indice + 1]))

        return segmentos


    def transformar(self, matriz: Matriz4) -> "Objeto3D":
        for inicio, fim in self.segmentos_3d:
            inicio.transformar(matriz)
            fim.transformar(matriz)

        return self

    def transladar(self, dx: float, dy: float, dz: float) -> "Objeto3D":
        return self.transformar(matriz_translacao(dx, dy, dz))

    def escalonar(self, sx: float, sy: float, sz: float) -> "Objeto3D":
        return self.transformar(preparar_escalonamento_em_torno_de(sx, sy, sz, self.centro()))

    def rotacionar(self, eixo: str, angulo_graus: float) -> "Objeto3D":
        return self.transformar(preparar_rotacao_em_torno_de(eixo, angulo_graus, self.centro()))

    def rotacionar_eixo_arbitrario(
        self,
        angulo_graus: float,
        ponto_a: Coordenada3D,
        ponto_b: Coordenada3D,
    ) -> "Objeto3D":
        return self.transformar(preparar_rotacao_eixo_arbitrario(angulo_graus, ponto_a, ponto_b))


def _novo_ponto(coordenada) -> Ponto3D:
    if isinstance(coordenada, Ponto3D):
        return Ponto3D(coordenada.x, coordenada.y, coordenada.z)

    x, y, z = coordenada

    return Ponto3D(x, y, z)




def _segmentos_por_arestas(
    vertices: List[Coordenada3D],
    arestas: List[Tuple[int, int]],
) -> List[Tuple[Coordenada3D, Coordenada3D]]:
    segmentos = []

    for inicio, fim in arestas:
        segmentos.append((vertices[inicio], vertices[fim]))

    return segmentos


def criar_cubo(nome: str, centro: Coordenada3D, lado: float, cor: CorRGB = COR_PADRAO) -> Objeto3D:
    cx, cy, cz = centro
    meio = lado / 2

    vertices = []

    for z in (cz - meio, cz + meio):
        vertices.append((cx - meio, cy - meio, z))
        vertices.append((cx + meio, cy - meio, z))
        vertices.append((cx + meio, cy + meio, z))
        vertices.append((cx - meio, cy + meio, z))

    arestas = []

    for indice in range(4):
        proximo = (indice + 1) % 4

        arestas.append((indice, proximo))
        arestas.append((indice + 4, proximo + 4))
        arestas.append((indice, indice + 4))

    return Objeto3D(nome, _segmentos_por_arestas(vertices, arestas), cor)


def criar_piramide(nome: str, centro: Coordenada3D, lado: float, cor: CorRGB = COR_PADRAO) -> Objeto3D:
    cx, cy, cz = centro
    meio = lado / 2

    vertices = [
        (cx - meio, cy - meio, cz - meio),
        (cx + meio, cy - meio, cz - meio),
        (cx + meio, cy + meio, cz - meio),
        (cx - meio, cy + meio, cz - meio),
        (cx, cy, cz + meio),
    ]

    arestas = []

    for indice in range(4):
        proximo = (indice + 1) % 4

        arestas.append((indice, proximo))
        arestas.append((indice, 4))

    return Objeto3D(nome, _segmentos_por_arestas(vertices, arestas), cor)


MALHAS: Dict[str, Callable[..., Objeto3D]] = {
    "Cubo": criar_cubo,
    "Pirâmide": criar_piramide,
}

def interpretar_segmentos(texto: str) -> List[Tuple[Coordenada3D, Coordenada3D]]:
    resultado = eval(texto)

    if _eh_coordenada_3d(resultado):
        resultado = [resultado]

    pontos = list(resultado)
    coordenadas = []

    for ponto in pontos:
        if not _eh_coordenada_3d(ponto):
            raise ValueError(f"Coordenada 3D inválida: {ponto!r}")

        coordenadas.append((float(ponto[0]), float(ponto[1]), float(ponto[2])))

    if len(coordenadas) == 0 or len(coordenadas) % 2 != 0:
        raise ValueError("Informe os pontos em pares: cada par é um segmento do objeto 3D.")

    segmentos = []

    for indice in range(0, len(coordenadas), 2):
        segmentos.append((coordenadas[indice], coordenadas[indice + 1]))

    return segmentos


def interpretar_ponto(texto: str) -> Coordenada3D:
    resultado = eval(texto)

    if not _eh_coordenada_3d(resultado):
        raise ValueError(f"Ponto 3D inválido: {texto!r}, use (x, y, z)")

    return float(resultado[0]), float(resultado[1]), float(resultado[2])


def _eh_coordenada_3d(valor) -> bool:
    if not isinstance(valor, (tuple, list)):
        return False

    if len(valor) != 3:
        return False

    for componente in valor:
        if not isinstance(componente, (int, float)):
            return False

    return True
