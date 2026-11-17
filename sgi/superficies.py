from typing import List

from sgi.objetos import COR_PADRAO, MATRIZ_BEZIER, CorRGB, ObjetoGrafico
from sgi.objetos3d import Objeto3D, Ponto3D, Segmento3D, _eh_coordenada_3d, _novo_ponto
from sgi.transformacoes3d import Coordenada3D, Matriz4

CURVAS_POR_RETALHO = 10
PASSOS_POR_CURVA = 20

Retalho = List[List[Ponto3D]]
MatrizCoeficientes = List[List[float]]


class SuperficieBezier(Objeto3D):
    tipo = "superfície bézier"

    def __init__(self, nome: str, retalhos: List[List[List[Coordenada3D]]], cor: CorRGB = COR_PADRAO):
        if len(retalhos) == 0:
            raise ValueError("Uma superfície precisa de pelo menos 1 retalho.")

        ObjetoGrafico.__init__(self, nome, [], cor)

        self.retalhos: List[Retalho] = []

        for retalho in retalhos:
            self.retalhos.append(_novo_retalho(retalho))

        self.segmentos_3d: List[Segmento3D] = []
        self._gerar_malha()

    def descricao(self) -> str:
        quantidade = len(self.retalhos)

        if quantidade == 1:
            return f"{self.nome} ({self.tipo}, 1 retalho)"

        return f"{self.nome} ({self.tipo}, {quantidade} retalhos)"

    def pontos_de_controle(self) -> List[Ponto3D]:
        pontos = []

        for retalho in self.retalhos:
            for linha in retalho:
                pontos.extend(linha)

        return pontos

    def vertices(self) -> List[Coordenada3D]:
        unicos = []

        for ponto in self.pontos_de_controle():
            coordenada = ponto.como_tupla()

            if coordenada not in unicos:
                unicos.append(coordenada)

        return unicos

    #a superficie fica no fecho convexo dos pontos de controle, ent transformar
    #os pontos e regerar a malha é o msm q transformar a superficie
    def transformar(self, matriz: Matriz4) -> "SuperficieBezier":
        for ponto in self.pontos_de_controle():
            ponto.transformar(matriz)

        self._gerar_malha()

        return self

    def _gerar_malha(self) -> None:
        self.segmentos_3d = []

        for retalho in self.retalhos:
            self.segmentos_3d.extend(segmentos_do_retalho(retalho, CURVAS_POR_RETALHO, PASSOS_POR_CURVA))


def segmentos_do_retalho(retalho: Retalho, curvas: int, passos: int) -> List[Segmento3D]:
    coeficientes_x = _coeficientes_do_retalho(retalho, 0)
    coeficientes_y = _coeficientes_do_retalho(retalho, 1)
    coeficientes_z = _coeficientes_do_retalho(retalho, 2)

    def avaliar(s: float, t: float) -> Ponto3D:
        x = _avaliar_bicubica(coeficientes_x, s, t)
        y = _avaliar_bicubica(coeficientes_y, s, t)
        z = _avaliar_bicubica(coeficientes_z, s, t)

        return Ponto3D(x, y, z)

    segmentos = []

    for curva in range(curvas + 1):
        fixo = curva / curvas

        pontos_com_s_fixo = []
        pontos_com_t_fixo = []

        for passo in range(passos + 1):
            variavel = passo / passos

            pontos_com_s_fixo.append(avaliar(fixo, variavel))
            pontos_com_t_fixo.append(avaliar(variavel, fixo))

        segmentos.extend(_polilinha(pontos_com_s_fixo))
        segmentos.extend(_polilinha(pontos_com_t_fixo))

    return segmentos


def _polilinha(pontos: List[Ponto3D]) -> List[Segmento3D]:
    segmentos = []

    for indice in range(len(pontos) - 1):
        segmentos.append((pontos[indice], pontos[indice + 1]))

    return segmentos


def _coeficientes_do_retalho(retalho: Retalho, eixo: int) -> MatrizCoeficientes:
    geometria = []

    for linha in retalho:
        valores = []

        for ponto in linha:
            valores.append(ponto.como_tupla()[eixo])

        geometria.append(valores)

    transposta = _transpor(MATRIZ_BEZIER)

    return _multiplicar(_multiplicar(MATRIZ_BEZIER, geometria), transposta)


def _avaliar_bicubica(coeficientes: MatrizCoeficientes, s: float, t: float) -> float:
    vetor_s = [s ** 3, s ** 2, s, 1.0]
    vetor_t = [t ** 3, t ** 2, t, 1.0]

    resultado = 0.0

    for i in range(4):
        for j in range(4):
            resultado += vetor_s[i] * coeficientes[i][j] * vetor_t[j]

    return resultado


def _multiplicar(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    resultado = []

    for i in range(len(a)):
        linha = []

        for j in range(len(b[0])):
            soma = 0.0

            for k in range(len(b)):
                soma += a[i][k] * b[k][j]

            linha.append(soma)

        resultado.append(linha)

    return resultado


def _transpor(matriz: List[List[float]]) -> List[List[float]]:
    transposta = []

    for j in range(len(matriz[0])):
        linha = []

        for i in range(len(matriz)):
            linha.append(matriz[i][j])

        transposta.append(linha)

    return transposta


def _novo_retalho(retalho) -> Retalho:
    if len(retalho) != 4:
        raise ValueError("Cada retalho precisa de 4 linhas de pontos de controle.")

    novo = []

    for linha in retalho:
        if len(linha) != 4:
            raise ValueError("Cada linha de um retalho precisa de 4 pontos de controle.")

        nova_linha = []

        for coordenada in linha:
            nova_linha.append(_novo_ponto(coordenada))

        novo.append(nova_linha)

    return novo


#linhas da matriz separadas por ";", 4 pontos por linha. A cada 4 linhas (16 pontos) fecha um retalho:
#(x11,y11,z11),(x12,y12,z12),(x13,y13,z13),(x14,y14,z14);(x21,y21,z21),...;...
def interpretar_retalhos(texto: str) -> List[List[List[Coordenada3D]]]:
    linhas_de_texto = []

    for parte in texto.split(";"):
        if parte.strip() != "":
            linhas_de_texto.append(parte)

    if len(linhas_de_texto) == 0 or len(linhas_de_texto) % 4 != 0:
        raise ValueError("Informe as linhas da matriz de 4 em 4 (16 pontos por retalho), separadas por \";\".")

    linhas = []

    for numero, parte in enumerate(linhas_de_texto, start=1):
        linhas.append(_interpretar_linha(parte, numero))

    retalhos = []

    for inicio in range(0, len(linhas), 4):
        retalhos.append(linhas[inicio:inicio + 4])

    return retalhos


def _interpretar_linha(texto: str, numero: int) -> List[Coordenada3D]:
    resultado = list(eval(texto))

    if len(resultado) != 4:
        raise ValueError(f"A linha {numero} precisa de exatamente 4 pontos (x, y, z).")

    pontos = []

    for ponto in resultado:
        if not _eh_coordenada_3d(ponto):
            raise ValueError(f"Coordenada 3D inválida na linha {numero}: {ponto!r}")

        pontos.append((float(ponto[0]), float(ponto[1]), float(ponto[2])))

    return pontos
