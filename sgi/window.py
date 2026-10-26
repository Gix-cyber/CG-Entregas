#TODO: rever zoom c objetos adicionados, tem alguma coisa estranha em relacao aos pixels (testar c reta)

import math
from typing import List, Tuple

from sgi.objetos import Coordenada
from sgi.transformacoes import (
    Matriz,
    compor,
    matriz_escalonamento,
    matriz_rotacao,
    matriz_translacao,
    preparar_escalonamento_em_torno_de,
    preparar_rotacao_em_torno_de,
    transformar_ponto,
)


#a window é tratada como um obj grafico qualquer: 4 cantos em WC, na ordem
#inferior esquerdo, inferior direito, superior direito, superior esquerdo.
#centro, tamanho e angulo (vup) saem desses cantos, n sao guardados separado
class Window:

    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float):
        self.cantos: List[Coordenada] = [
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
            (xmin, ymax),
        ]

    @property
    def centro(self) -> Coordenada:
        soma_x = 0.0
        soma_y = 0.0

        for x, y in self.cantos:
            soma_x += x
            soma_y += y

        return soma_x / 4, soma_y / 4

    @property
    def largura(self) -> float:
        return _distancia(self.cantos[0], self.cantos[1])

    @property
    def altura(self) -> float:
        return _distancia(self.cantos[1], self.cantos[2])

    #angulo do eixo x da window c o eixo x do mundo, em graus (anti-horario positivo).
    #o vup é esse msm angulo aplicado no eixo y
    @property
    def angulo(self) -> float:
        inicio_x, inicio_y = self.cantos[0]
        fim_x, fim_y = self.cantos[1]

        return math.degrees(math.atan2(fim_y - inicio_y, fim_x - inicio_x))

    def _aplicar(self, matriz: Matriz) -> None:
        novos_cantos = []

        for canto in self.cantos:
            novos_cantos.append(transformar_ponto(canto, matriz))

        self.cantos = novos_cantos

    #panning em WC
    def mover(self, deslocamento_x: float, deslocamento_y: float) -> None:
        self._aplicar(matriz_translacao(deslocamento_x, deslocamento_y))

    #panning nos eixos da propria window, ou seja, respeitando o "p cima" do usuario
    def mover_relativo(self, deslocamento_x: float, deslocamento_y: float) -> None:
        deslocamento_mundo = transformar_ponto(
            (deslocamento_x, deslocamento_y),
            matriz_rotacao(self.angulo),
        )

        self.mover(deslocamento_mundo[0], deslocamento_mundo[1])

    #panning em porcentagem do tamanho da window, nos eixos dela
    def mover_proporcional(self, fracao_x: float, fracao_y: float) -> None:
        deslocamento_x = fracao_x * self.largura
        deslocamento_y = fracao_y * self.altura

        self.mover_relativo(deslocamento_x, deslocamento_y)

    #fator do zooming >1 aproxima, <1 tem q afastar. Escala uniforme no centro,
    #ent n importa se a window ta rotacionada
    def escalar(self, fator: float) -> None:
        if fator <= 0:
            raise ValueError("O fator de zoom deve ser positivo.")

        inverso = 1 / fator

        self._aplicar(preparar_escalonamento_em_torno_de(inverso, inverso, self.centro))

    #rotacao de obj em torno de ponto arbitrario, c o ponto sendo o centro da window
    def rotacionar(self, angulo_graus: float) -> None:
        self._aplicar(preparar_rotacao_em_torno_de(angulo_graus, self.centro))

    #height e witdh da window alteradas mantendo centro e angulo. Qm chama precisa preserver proporcao do viewport,
    #pq a transformada precisa usar a msm escala em x e y (se n fizer assim distorce tava tendo problema c isso
    def definir_tamanho(self, largura: float, altura: float) -> None:
        centro_x, centro_y = self.centro
        angulo = self.angulo
        meia_largura = largura / 2
        meia_altura = altura / 2

        # monta alinhada aos eixos e dps gira de volta p onde tava
        self.cantos = [
            (centro_x - meia_largura, centro_y - meia_altura),
            (centro_x + meia_largura, centro_y - meia_altura),
            (centro_x + meia_largura, centro_y + meia_altura),
            (centro_x - meia_largura, centro_y + meia_altura),
        ]
        self.rotacionar(angulo)

    #algoritmo gerar descricao em SCN:
    #  1. translada o centro da window p origem
    #  2. rotaciona o mundo por -angulo (o mundo gira ao contrario da window)
    #  3. escala p window virar o quadrado [-1, 1] x [-1, 1]
    def matriz_normalizacao(self) -> Matriz:
        centro_x, centro_y = self.centro

        return compor([
            matriz_translacao(-centro_x, -centro_y),
            matriz_rotacao(-self.angulo),
            matriz_escalonamento(2 / self.largura, 2 / self.altura),
        ])

    #inverso da normalizacao, SCN -> WC
    def para_mundo(self, x_normalizado: float, y_normalizado: float) -> Tuple[float, float]:
        centro_x, centro_y = self.centro

        matriz = compor([
            matriz_escalonamento(self.largura / 2, self.altura / 2),
            matriz_rotacao(self.angulo),
            matriz_translacao(centro_x, centro_y),
        ])

        return transformar_ponto((x_normalizado, y_normalizado), matriz)


def _distancia(a: Coordenada, b: Coordenada) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])
