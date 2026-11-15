#TODO: rever zoom c objetos adicionados, tem alguma coisa estranha em relacao aos pixels (testar c reta)

import math

from sgi.objetos3d import Ponto3D
from sgi.transformacoes3d import (
    Coordenada3D,
    Matriz4,
    Vetor3D,
    compor,
    matriz_escalonamento,
    matriz_rotacao_x,
    matriz_rotacao_y,
    matriz_rotacao_z,
    matriz_translacao,
    multiplicar_escalar,
    normalizar,
    preparar_rotacao_eixo_arbitrario,
    produto_vetorial,
    somar,
    transformar_vetor,
)

VISTA_TOPO = ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0))
VISTA_BAIXO = ((0.0, 0.0, -1.0), (0.0, -1.0, 0.0))
VISTA_FRENTE = ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0))
VISTA_TRAS = ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
VISTA_DIREITA = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
VISTA_ESQUERDA = ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))


class Window:

    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float):
        self.vrp = Ponto3D((xmin + xmax) / 2, (ymin + ymax) / 2, 0.0)
        self.vpn: Vetor3D = VISTA_TOPO[0]
        self.vup: Vetor3D = VISTA_TOPO[1]
        self.largura = xmax - xmin
        self.altura = ymax - ymin

    @property
    def centro(self) -> Coordenada3D:
        return self.vrp.como_tupla()

    @property
    def eixo_u(self) -> Vetor3D:
        return normalizar(produto_vetorial(self.vup, self.vpn))

    @property
    def angulo(self) -> float:
        ux, uy, _ = self.eixo_u

        if math.hypot(ux, uy) < 1e-9:
            return 0.0

        return math.degrees(math.atan2(uy, ux))

    # ---- navegacao ----

    def mover_relativo(self, deslocamento_x: float, deslocamento_y: float) -> None:
        deslocamento = somar(
            multiplicar_escalar(self.eixo_u, deslocamento_x),
            multiplicar_escalar(self.vup, deslocamento_y),
        )

        self.vrp.transladar(deslocamento[0], deslocamento[1], deslocamento[2])

    def mover_proporcional(self, fracao_x: float, fracao_y: float) -> None:
        self.mover_relativo(fracao_x * self.largura, fracao_y * self.altura)

    def escalar(self, fator: float) -> None:
        if fator <= 0:
            raise ValueError("O fator de zoom deve ser positivo.")

        self.largura = self.largura / fator
        self.altura = self.altura / fator

    #giro da window em torno do proprio VPN (o "rotacionar" do 2D). O VRP fica parado
    def rotacionar(self, angulo_graus: float) -> None:
        self._girar_orientacao(self.vpn, angulo_graus)

    #orbita em torno do VRP: positivo leva o observador p direita (o VPN vai na direcao do u)
    def orbitar_horizontal(self, angulo_graus: float) -> None:
        self._girar_orientacao(self.vup, angulo_graus)

    def orbitar_vertical(self, angulo_graus: float) -> None:
        self._girar_orientacao(self.eixo_u, -angulo_graus)

    def _girar_orientacao(self, eixo: Vetor3D, angulo_graus: float) -> None:
        matriz = preparar_rotacao_eixo_arbitrario(angulo_graus, (0.0, 0.0, 0.0), eixo)

        vpn = normalizar(transformar_vetor(self.vpn, matriz))
        vup = transformar_vetor(self.vup, matriz)

        self._definir_orientacao(vpn, vup)

    def definir_vista(self, vista) -> None:
        vpn, vup = vista

        self._definir_orientacao(vpn, vup)

    def _definir_orientacao(self, vpn: Vetor3D, vup: Vetor3D) -> None:
        vpn = normalizar(vpn)
        paralelo = vup[0] * vpn[0] + vup[1] * vpn[1] + vup[2] * vpn[2]
        vup = somar(vup, multiplicar_escalar(vpn, -paralelo))

        self.vpn = vpn
        self.vup = normalizar(vup)

    def definir_tamanho(self, largura: float, altura: float) -> None:
        self.largura = largura
        self.altura = altura


    def _angulos_do_vpn(self):
        a, b, c = self.vpn

        angulo_x = math.degrees(math.atan2(b, c))

        angulo_y = math.degrees(math.atan2(-a, math.hypot(b, c)))

        return angulo_x, angulo_y

    def _matriz_alinhamento_vpn(self) -> Matriz4:
        angulo_x, angulo_y = self._angulos_do_vpn()

        return compor([
            matriz_rotacao_x(angulo_x),
            matriz_rotacao_y(angulo_y),
        ])

    def vpn_alinhado(self) -> Vetor3D:
        return transformar_vetor(self.vpn, self._matriz_alinhamento_vpn())

    def matriz_normalizacao(self) -> Matriz4:
        x, y, z = self.centro
        alinhamento = self._matriz_alinhamento_vpn()

        # angulo do VUP ja alinhado em relacao a y. Rotacao em z faz x' = x cos - y sen
        vup_x, vup_y, _ = transformar_vetor(self.vup, alinhamento)
        angulo_z = math.degrees(math.atan2(vup_x, vup_y))

        return compor([
            matriz_translacao(-x, -y, -z),
            alinhamento,
            matriz_rotacao_z(angulo_z),
            matriz_escalonamento(2 / self.largura, 2 / self.altura, 1.0),
        ])
