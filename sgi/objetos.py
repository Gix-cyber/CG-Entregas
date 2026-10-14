from typing import List, Tuple


Coordenada = Tuple[float, float]
CorRGB = Tuple[int, int, int]

COR_PADRAO: CorRGB = (0, 0, 0)


class ObjetoGrafico:
    tipo = "objeto"

    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        self.nome = nome
        self.coordenadas = list(coordenadas)
        self.cor = cor

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

    #segmnetos de reta q compoem o obj
    def segmentos(self) -> List[Tuple[Coordenada, Coordenada]]:
        return []

    def descricao(self) -> str:
        return f"{self.nome} ({self.tipo})"


class Ponto(ObjetoGrafico):

    tipo = "ponto"
    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        if len(coordenadas) != 1:
            raise ValueError("Um ponto precisa de exatamente 1 coordenada.")
        super().__init__(nome, coordenadas, cor)


class Reta(ObjetoGrafico):

    tipo = "reta"
    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        if len(coordenadas) != 2:
            raise ValueError("Uma reta precisa de exatamente 2 coordenadas.")
        super().__init__(nome, coordenadas, cor)

    def segmentos(self) -> List[Tuple[Coordenada, Coordenada]]:
        inicio = self.coordenadas[0]
        fim = self.coordenadas[1]
        return [(inicio, fim)]


class Wireframe(ObjetoGrafico):
    #lista de ponto interconectados fechado no ultimo ponto

    tipo = "wireframe"

    def __init__(self, nome: str, coordenadas: List[Coordenada], cor: CorRGB = COR_PADRAO):
        if len(coordenadas) < 3:
            raise ValueError("Um wireframe precisa de pelo menos 3 coordenadas.")

        super().__init__(nome, coordenadas, cor)

    def segmentos(self) -> List[Tuple[Coordenada, Coordenada]]:
        segmentos = []
        quantidade = len(self.coordenadas)

        for indice in range(quantidade):
            inicio = self.coordenadas[indice]
            fim = self.coordenadas[(indice + 1) % quantidade]
            segmentos.append((inicio, fim))

        return segmentos


TIPOS = {
    Ponto.tipo: Ponto,
    Reta.tipo: Reta,
    Wireframe.tipo: Wireframe,
}


def criar_objeto(
    tipo: str,
    nome: str,
    coordenadas: List[Coordenada],
    cor: CorRGB = COR_PADRAO,
) -> ObjetoGrafico:
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de objeto desconhecido: {tipo}")

    classe = TIPOS[tipo]

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
