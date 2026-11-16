#TODO: rever zoom c objetos adicionados, tem alguma coisa estranha em relacao aos pixels (testar c reta)

import math
from typing import List, Optional, Tuple

from sgi.clipping import clipar_plano_proximo
from sgi.objetos3d import Ponto3D
from sgi.transformacoes3d import (
    Coordenada3D,
    Matriz4,
    Vetor3D,
    compor,
    matriz_escalonamento,
    matriz_perspectiva,
    matriz_rotacao_x,
    matriz_rotacao_y,
    matriz_rotacao_z,
    matriz_translacao,
    multiplicar_escalar,
    normalizar,
    preparar_rotacao_eixo_arbitrario,
    produto_vetorial,
    somar,
    transformar_ponto,
    transformar_ponto_homogeneo,
    transformar_vetor,
)

VISTA_TOPO = ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0))
VISTA_BAIXO = ((0.0, 0.0, -1.0), (0.0, -1.0, 0.0))
VISTA_FRENTE = ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0))
VISTA_TRAS = ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
VISTA_DIREITA = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
VISTA_ESQUERDA = ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))

DISTANCIA_COP_PADRAO = 600.0
DISTANCIA_PLANO_PROXIMO = 1.0


class Window:

    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float):
        self.vrp = Ponto3D((xmin + xmax) / 2, (ymin + ymax) / 2, 0.0)
        self.vpn: Vetor3D = VISTA_TOPO[0]
        self.vup: Vetor3D = VISTA_TOPO[1]
        self.largura = xmax - xmin
        self.altura = ymax - ymin
        self.perspectiva = False
        self.distancia_cop = DISTANCIA_COP_PADRAO

    @property
    def centro(self) -> Coordenada3D:
        return self.vrp.como_tupla()

    @property
    def cop(self) -> Coordenada3D:
        return somar(self.centro, multiplicar_escalar(self.vpn, self.distancia_cop))

    def definir_distancia_cop(self, distancia: float) -> None:
        if distancia <= DISTANCIA_PLANO_PROXIMO:
            raise ValueError("A distância do COP deve ser maior que a do plano próximo.")

        self.distancia_cop = distancia

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

    def _matriz_orientacao(self) -> Matriz4:
        alinhamento = self._matriz_alinhamento_vpn()

        # angulo do VUP ja alinhado em relacao a y. Rotacao em z faz x' = x cos - y sen
        vup_x, vup_y, _ = transformar_vetor(self.vup, alinhamento)
        angulo_z = math.degrees(math.atan2(vup_x, vup_y))

        return compor([
            alinhamento,
            matriz_rotacao_z(angulo_z),
        ])

    def _matriz_escala_scn(self) -> Matriz4:
        return matriz_escalonamento(2 / self.largura, 2 / self.altura, 1.0)

    def matriz_normalizacao(self) -> Matriz4:
        x, y, z = self.centro

        return compor([
            matriz_translacao(-x, -y, -z),
            self._matriz_orientacao(),
            self._matriz_escala_scn(),
        ])

    def matriz_vista_perspectiva(self) -> Matriz4:
        x, y, z = self.cop

        return compor([
            matriz_translacao(-x, -y, -z),
            self._matriz_orientacao(),
        ])

    def matriz_projecao_perspectiva(self) -> Matriz4:
        return compor([
            matriz_perspectiva(self.distancia_cop),
            self._matriz_escala_scn(),
        ])

    def projetar(self, coordenadas: List[Coordenada3D]) -> Optional[List[Tuple[float, float]]]:
        if not self.perspectiva:
            return self._projetar_paralela(coordenadas)

        vista = self.matriz_vista_perspectiva()
        projecao = self.matriz_projecao_perspectiva()
        projetadas = []

        for coordenada in coordenadas:
            x, y, z = transformar_ponto(coordenada, vista)

            if z > -DISTANCIA_PLANO_PROXIMO:
                return None

            x, y, _ = transformar_ponto_homogeneo((x, y, z), projecao)
            projetadas.append((x, y))

        return projetadas

    def projetar_segmento(self, inicio: Coordenada3D, fim: Coordenada3D):
        if not self.perspectiva:
            return self._projetar_paralela([inicio, fim])

        vista = self.matriz_vista_perspectiva()
        projecao = self.matriz_projecao_perspectiva()

        recortado = clipar_plano_proximo(
            transformar_ponto(inicio, vista),
            transformar_ponto(fim, vista),
            -DISTANCIA_PLANO_PROXIMO,
        )

        if recortado is None:
            return None

        projetadas = []

        for coordenada in recortado:
            x, y, _ = transformar_ponto_homogeneo(coordenada, projecao)
            projetadas.append((x, y))

        return projetadas

    def _projetar_paralela(self, coordenadas: List[Coordenada3D]) -> List[Tuple[float, float]]:
        matriz = self.matriz_normalizacao()
        projetadas = []

        for coordenada in coordenadas:
            x, y, _ = transformar_ponto(coordenada, matriz)
            projetadas.append((x, y))

        return projetadas
