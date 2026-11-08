from typing import List, Tuple

from sgi.clipping import (
    PRIMITIVA_POLIGONO,
    PRIMITIVA_PONTO,
    PRIMITIVA_SEGMENTO,
    AlgoritmoReta,
    Primitiva,
    clipar_ponto,
    sutherland_hodgman,
)


Coordenada = Tuple[float, float]
CorRGB = Tuple[int, int, int]

COR_PADRAO: CorRGB = (0, 0, 0)


class ObjetoGrafico:
    tipo = "objeto"

    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        self.nome = nome
        self.coordenadas = list(coordenadas)
        self.cor = cor

        # cache das coordenadas em SCN, recalculada pelo display file sempre q a window muda.
        # as coordenadas do mundo (WC) n mudam c a navegacao
        self.coordenadas_normalizadas: List[Coordenada] = list(coordenadas)

    #tkinter so entende a cor como string hex
    def cor_hex(self) -> str:
        r, g, b = self.cor

        return f"#{r:02x}{g:02x}{b:02x}"

    #centro geometrico = media das coordenadas
    def centro(self) -> Coordenada:
        quantidade = len(self.coordenadas)
        soma_x = 0.0
        soma_y = 0.0

        for x, y in self.coordenadas:
            soma_x += x
            soma_y += y

        return soma_x / quantidade, soma_y / quantidade

    #segmnetos de reta q compoem o obj, em WC
    def segmentos(self) -> List[Tuple[Coordenada, Coordenada]]:
        return self._segmentos_de(self.coordenadas)

    #msm segmentos, mas em SCN (é o q vai p transformada de viewport)
    def segmentos_normalizados(self) -> List[Tuple[Coordenada, Coordenada]]:
        return self._segmentos_de(self.coordenadas_normalizadas)

    def _segmentos_de(self, coordenadas: List[Coordenada]) -> List[Tuple[Coordenada, Coordenada]]:
        return []

    def clipar(self, algoritmo_reta: AlgoritmoReta) -> List[Primitiva]:
        primitivas = []

        for inicio, fim in self.segmentos_normalizados():
            recortado = algoritmo_reta(inicio, fim)

            if recortado is None:
                continue

            novo_inicio, novo_fim = recortado
            primitivas.append((PRIMITIVA_SEGMENTO, [novo_inicio, novo_fim]))

        return primitivas

    def descricao(self) -> str:
        return f"{self.nome} ({self.tipo})"


class Ponto(ObjetoGrafico):

    tipo = "ponto"
    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        if len(coordenadas) != 1:
            raise ValueError("Um ponto precisa de exatamente 1 coordenada.")
        super().__init__(nome, coordenadas, cor)

    def clipar(self, algoritmo_reta: AlgoritmoReta) -> List[Primitiva]:
        ponto = self.coordenadas_normalizadas[0]

        if not clipar_ponto(ponto):
            return []

        return [(PRIMITIVA_PONTO, [ponto])]


class Reta(ObjetoGrafico):

    tipo = "reta"
    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        if len(coordenadas) != 2:
            raise ValueError("Uma reta precisa de exatamente 2 coordenadas.")
        super().__init__(nome, coordenadas, cor)

    def _segmentos_de(self, coordenadas: List[Coordenada]) -> List[Tuple[Coordenada, Coordenada]]:
        inicio = coordenadas[0]
        fim = coordenadas[1]
        return [(inicio, fim)]


class Wireframe(ObjetoGrafico):
    tipo = "wireframe"

    def __init__(
        self,
        nome: str,
        coordenadas: List[Coordenada],
        cor: CorRGB = COR_PADRAO,
        preenchido: bool = False,
    ):
        if len(coordenadas) < 3:
            raise ValueError("Um wireframe precisa de pelo menos 3 coordenadas.")

        super().__init__(nome, coordenadas, cor)
        self.preenchido = preenchido
    def clipar(self, algoritmo_reta: AlgoritmoReta) -> List[Primitiva]:
        if not self.preenchido:
            return super().clipar(algoritmo_reta)

        recortado = sutherland_hodgman(self.coordenadas_normalizadas)

        if len(recortado) < 3:
            return []

        return [(PRIMITIVA_POLIGONO, recortado)]

    def descricao(self) -> str:
        if self.preenchido:
            return f"{self.nome} ({self.tipo} preenchido)"

        return super().descricao()

    def _segmentos_de(self, coordenadas: List[Coordenada]) -> List[Tuple[Coordenada, Coordenada]]:
        segmentos = []
        quantidade = len(coordenadas)

        for indice in range(quantidade):
            inicio = coordenadas[indice]
            fim = coordenadas[(indice + 1) % quantidade]
            segmentos.append((inicio, fim))

        return segmentos


# matriz de Bezier p/ a forma matricial C(t) = T * Mb * G, c T = [t^3 t^2 t 1]
# e G = [P1 P2 P3 P4] (os 4 pontos de controle de um trecho)
MATRIZ_BEZIER = [
    [-1, 3, -3, 1],
    [3, -6, 3, 0],
    [-3, 3, 0, 0],
    [1, 0, 0, 0],
]

PASSOS_POR_TRECHO = 40


#a curva é composta de trechos de Bezier cubica. O ultimo ponto de controle de um trecho
#é o primeiro do proximo, o q garante continuidade G(0). Ent sao 4 pontos p/ o 1o trecho
#e + 3 p/ cada trecho a mais: 4, 7, 10, ...
class Curva2D(ObjetoGrafico):
    tipo = "curva"

    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        quantidade = len(coordenadas)

        if quantidade < 4 or (quantidade - 1) % 3 != 0:
            raise ValueError(
                "Uma curva de Bézier precisa de 4, 7, 10, ... pontos de controle "
                "(4 no primeiro trecho e +3 por trecho seguinte)."
            )

        super().__init__(nome, coordenadas, cor)

    def quantidade_de_trechos(self) -> int:
        return (len(self.coordenadas) - 1) // 3

    def descricao(self) -> str:
        trechos = self.quantidade_de_trechos()

        if trechos == 1:
            return f"{self.nome} ({self.tipo}, 1 trecho)"

        return f"{self.nome} ({self.tipo}, {trechos} trechos)"

    def _segmentos_de(self, coordenadas: List[Coordenada]) -> List[Tuple[Coordenada, Coordenada]]:
        pontos = pontos_da_curva(coordenadas, PASSOS_POR_TRECHO)
        segmentos = []

        for indice in range(len(pontos) - 1):
            segmentos.append((pontos[indice], pontos[indice + 1]))

        return segmentos


def pontos_da_curva(controle: List[Coordenada], passos: int) -> List[Coordenada]:
    pontos = [controle[0]]
    quantidade_de_trechos = (len(controle) - 1) // 3

    for trecho in range(quantidade_de_trechos):
        inicio = trecho * 3
        geometria = controle[inicio:inicio + 4]
        coeficientes = _coeficientes_bezier(geometria)

        for passo in range(1, passos + 1):
            t = passo / passos
            pontos.append(_avaliar_cubica(coeficientes, t))

    return pontos

#x(t) = a t^3 + b t^2 + c t + d (e o msm p/ y)
def _coeficientes_bezier(geometria: List[Coordenada]) -> List[Coordenada]:
    coeficientes = []

    for linha in MATRIZ_BEZIER:
        x = 0.0
        y = 0.0

        for peso, (px, py) in zip(linha, geometria):
            x += peso * px
            y += peso * py

        coeficientes.append((x, y))

    return coeficientes


#T * (Mb * G) c T = [t^3 t^2 t 1]
def _avaliar_cubica(coeficientes: List[Coordenada], t: float) -> Coordenada:
    vetor_t = [t ** 3, t ** 2, t, 1.0]

    x = 0.0
    y = 0.0

    for potencia, (cx, cy) in zip(vetor_t, coeficientes):
        x += potencia * cx
        y += potencia * cy

    return x, y


TIPOS = {
    Ponto.tipo: Ponto,
    Reta.tipo: Reta,
    Wireframe.tipo: Wireframe,
    Curva2D.tipo: Curva2D,
}


def criar_objeto(
    tipo: str,
    nome: str,
    coordenadas: List[Coordenada],
    cor: CorRGB = COR_PADRAO,
    preenchido: bool = False,
) -> ObjetoGrafico:
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de objeto desconhecido: {tipo}")

    classe = TIPOS[tipo]

    if classe is Wireframe:
        return Wireframe(nome, coordenadas, cor, preenchido)

    return classe(nome, coordenadas, cor)


#cast de entrada como x1,y1;x2,y2 em coordenadas. Coord x,y vai ser tupla de numeros e n tupla de tupla, ent tem q ser envolvida em lista
def interpretar_coordenadas(texto: str) -> List[Coordenada]:
    resultado = eval(texto)

    if _eh_coordenada(resultado):
        resultado = [resultado]

    pontos = list(resultado)
    coordenadas = []

    for ponto in pontos:
        if not _eh_coordenada(ponto):
            raise ValueError(f"Coordenada inválida: {ponto!r}")

        x = float(ponto[0])
        y = float(ponto[1])
        coordenadas.append((x, y))

    return coordenadas


def _eh_coordenada(valor) -> bool:
    if not isinstance(valor, (tuple, list)):
        return False

    if len(valor) != 2:
        return False

    for componente in valor:
        if not isinstance(componente, (int, float)):
            return False

    return True
