from typing import Callable, Dict, List, Optional, Tuple

from sgi.viewport import SCN_MAX, SCN_MIN


#o clipping é feito em SCN, depois da normalizacao e antes da transformada de viewport
#Como a window em SCN é sempre o quadrado [-1, 1] x [-1, 1], os limites sao fixos e
#a window pode estar rotacionada no mundo sem o clipping precisar saber disso
XW_MIN = SCN_MIN
XW_MAX = SCN_MAX
YW_MIN = SCN_MIN
YW_MAX = SCN_MAX


Coordenada = Tuple[float, float]
Segmento = Tuple[Coordenada, Coordenada]

# um algoritmo de clipping de reta recebe os 2 extremos e devolve o trecho visivel,
# ou None se a reta ta toda fora da window
AlgoritmoReta = Callable[[Coordenada, Coordenada], Optional[Segmento]]


# ---------------------------------------------------------------- pontos

def clipar_ponto(ponto: Coordenada) -> bool:
    x, y = ponto

    dentro_em_x = XW_MIN <= x <= XW_MAX
    dentro_em_y = YW_MIN <= y <= YW_MAX

    return dentro_em_x and dentro_em_y


# ---------------------------------------------------------------- Cohen-Sutherland

DENTRO = 0b0000
ESQUERDA = 0b0001
DIREITA = 0b0010
ABAIXO = 0b0100
ACIMA = 0b1000


def _region_code(ponto: Coordenada) -> int:
    x, y = ponto
    codigo = DENTRO

    if x < XW_MIN:
        codigo |= ESQUERDA
    elif x > XW_MAX:
        codigo |= DIREITA

    if y < YW_MIN:
        codigo |= ABAIXO
    elif y > YW_MAX:
        codigo |= ACIMA

    return codigo


#  1. os 2 codigos zerados -> reta toda dentro
#  2. AND dos codigos != 0 -> os 2 extremos do msm lado de fora, reta toda fora
#  3. senao pega um extremo q ta fora e troca ele pela intersecao c a borda
#     indicada pelo codigo dele, e repete ate cair no caso 1 ou 2
def cohen_sutherland(inicio: Coordenada, fim: Coordenada) -> Optional[Segmento]:
    x1, y1 = inicio
    x2, y2 = fim

    codigo_inicio = _region_code((x1, y1))
    codigo_fim = _region_code((x2, y2))

    while True:
        if codigo_inicio == DENTRO and codigo_fim == DENTRO:
            return (x1, y1), (x2, y2)

        if codigo_inicio & codigo_fim != 0:
            return None

        if codigo_inicio != DENTRO:
            codigo_fora = codigo_inicio
        else:
            codigo_fora = codigo_fim

        x, y = _intersecao_cohen_sutherland(x1, y1, x2, y2, codigo_fora)

        if codigo_fora == codigo_inicio:
            x1 = x
            y1 = y
            codigo_inicio = _region_code((x1, y1))
        else:
            x2 = x
            y2 = y
            codigo_fim = _region_code((x2, y2))


#se o codigo tem bit de cima/baixo a reta n é horizontal, e se tem bit de esquerda/direita
#n é vertical, ent as divisoes abaixo nunca sao por zero
def _intersecao_cohen_sutherland(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    codigo_fora: int,
) -> Coordenada:
    if codigo_fora & ACIMA:
        x = x1 + (x2 - x1) * (YW_MAX - y1) / (y2 - y1)
        y = YW_MAX
    elif codigo_fora & ABAIXO:
        x = x1 + (x2 - x1) * (YW_MIN - y1) / (y2 - y1)
        y = YW_MIN
    elif codigo_fora & DIREITA:
        x = XW_MAX
        y = y1 + (y2 - y1) * (XW_MAX - x1) / (x2 - x1)
    else:
        x = XW_MIN
        y = y1 + (y2 - y1) * (XW_MIN - x1) / (x2 - x1)

    return x, y


# ---------------------------------------------------------------- Liang-Barsky

#reta parametrica P(u) = P1 + u * (P2 - P1), c u em [0, 1].
#p/q de cada borda: p < 0 a reta ta entrando, p > 0 saindo, p == 0 paralela.
#u1 é o maior u de entrada e u2 o menor u de saida; se u1 > u2 a reta ta fora
def liang_barsky(inicio: Coordenada, fim: Coordenada) -> Optional[Segmento]:
    x1, y1 = inicio
    x2, y2 = fim

    delta_x = x2 - x1
    delta_y = y2 - y1

    # esquerda, direita, baixo, cima
    valores_p = [-delta_x, delta_x, -delta_y, delta_y]
    valores_q = [x1 - XW_MIN, XW_MAX - x1, y1 - YW_MIN, YW_MAX - y1]

    u1 = 0.0
    u2 = 1.0

    for p, q in zip(valores_p, valores_q):
        if p == 0:
            # paralela a borda: se ta do lado de fora dela n tem como entrar
            if q < 0:
                return None

            continue

        r = q / p

        if p < 0:
            if r > u1:
                u1 = r
        else:
            if r < u2:
                u2 = r

    if u1 > u2:
        return None

    novo_inicio = (x1 + u1 * delta_x, y1 + u1 * delta_y)
    novo_fim = (x1 + u2 * delta_x, y1 + u2 * delta_y)

    return novo_inicio, novo_fim


ALGORITMOS_RETA: Dict[str, AlgoritmoReta] = {
    "Cohen-Sutherland": cohen_sutherland,
    "Liang-Barsky": liang_barsky,
}

ALGORITMO_RETA_PADRAO = "Cohen-Sutherland"


# ---------------------------------------------------------------- Sutherland-Hodgman

#o poligono é recortado contra uma borda da window por vez, e o resultado de uma
#borda vira a entrada da proxima. P/ cada aresta (anterior -> atual):
#  dentro -> dentro: guarda atual
#  dentro -> fora:   guarda a intersecao
#  fora -> fora:     n guarda nada
#  fora -> dentro:   guarda a intersecao e o atual
def sutherland_hodgman(vertices: List[Coordenada]) -> List[Coordenada]:
    bordas = [
        (_dentro_da_esquerda, _intersecao_vertical, XW_MIN),
        (_dentro_da_direita, _intersecao_vertical, XW_MAX),
        (_dentro_de_baixo, _intersecao_horizontal, YW_MIN),
        (_dentro_de_cima, _intersecao_horizontal, YW_MAX),
    ]

    resultado = list(vertices)

    for esta_dentro, intersecao, limite in bordas:
        resultado = _clipar_contra_borda(resultado, esta_dentro, intersecao, limite)

        if len(resultado) == 0:
            break

    return resultado


def _clipar_contra_borda(vertices, esta_dentro, intersecao, limite) -> List[Coordenada]:
    saida = []
    quantidade = len(vertices)

    for indice in range(quantidade):
        atual = vertices[indice]
        anterior = vertices[indice - 1]

        atual_dentro = esta_dentro(atual)
        anterior_dentro = esta_dentro(anterior)

        if atual_dentro:
            if not anterior_dentro:
                saida.append(intersecao(anterior, atual, limite))

            saida.append(atual)
        elif anterior_dentro:
            saida.append(intersecao(anterior, atual, limite))

    return saida


def _dentro_da_esquerda(ponto: Coordenada) -> bool:
    return ponto[0] >= XW_MIN


def _dentro_da_direita(ponto: Coordenada) -> bool:
    return ponto[0] <= XW_MAX


def _dentro_de_baixo(ponto: Coordenada) -> bool:
    return ponto[1] >= YW_MIN


def _dentro_de_cima(ponto: Coordenada) -> bool:
    return ponto[1] <= YW_MAX


#so é chamada qnd os 2 pontos estao em lados opostos da borda, ent x1 != x2
def _intersecao_vertical(a: Coordenada, b: Coordenada, x_borda: float) -> Coordenada:
    x1, y1 = a
    x2, y2 = b

    t = (x_borda - x1) / (x2 - x1)

    return x_borda, y1 + t * (y2 - y1)


#msm coisa p borda horizontal, aqui y1 != y2
def _intersecao_horizontal(a: Coordenada, b: Coordenada, y_borda: float) -> Coordenada:
    x1, y1 = a
    x2, y2 = b

    t = (y_borda - y1) / (y2 - y1)

    return x1 + t * (x2 - x1), y_borda


# ---------------------------------------------------------------- primitivas

#o resultado do clipping de um obj é uma lista de primitivas ja em SCN e ja recortadas.
#So elas passam pela transformada de viewport, o obj original n é desenhado
PRIMITIVA_PONTO = "ponto"
PRIMITIVA_SEGMENTO = "segmento"
PRIMITIVA_POLIGONO = "poligono"

Primitiva = Tuple[str, List[Coordenada]]
