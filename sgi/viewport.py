from typing import Tuple


#a window em SCN é sempre o quadrado [-1, 1] x [-1, 1]
SCN_MIN = -1.0
SCN_MAX = 1.0


class Viewport:
    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    @property
    def largura(self) -> float:
        return self.xmax - self.xmin

    @property
    def altura(self) -> float:
        return self.ymax - self.ymin

    def redimensionar(self, largura: float, altura: float) -> None:
        self.xmax = self.xmin + largura
        self.ymax = self.ymin + altura

    #coordenada em SCN -> coordenada do canva. Lembra q eixo y cresce p baixo no canva
    def transformar(self, x_normalizado: float, y_normalizado: float) -> Tuple[float, float]:
        fracao_x = (x_normalizado - SCN_MIN) / (SCN_MAX - SCN_MIN)
        fracao_y = (y_normalizado - SCN_MIN) / (SCN_MAX - SCN_MIN)

        x_viewport = self.xmin + fracao_x * self.largura
        y_viewport = self.ymin + (1 - fracao_y) * self.altura

        return x_viewport, y_viewport

    #inverso do transformar, canva -> SCN
    def para_normalizado(self, x_viewport: float, y_viewport: float) -> Tuple[float, float]:
        fracao_x = (x_viewport - self.xmin) / self.largura
        fracao_y = 1 - (y_viewport - self.ymin) / self.altura

        x_normalizado = SCN_MIN + fracao_x * (SCN_MAX - SCN_MIN)
        y_normalizado = SCN_MIN + fracao_y * (SCN_MAX - SCN_MIN)

        return x_normalizado, y_normalizado
