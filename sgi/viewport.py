from typing import Tuple

from sgi.window import Window


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

    #coordenada do mundo -> coordenada do canva. Lembra q eixo y cresce p baixo no canva
    def transformar(self, window: Window, x: float, y: float) -> Tuple[float, float]:
        x_normalizado = (x - window.xmin) / window.largura
        y_normalizado = (y - window.ymin) / window.altura

        x_viewport = self.xmin + x_normalizado * self.largura
        y_viewport = self.ymin + (1 - y_normalizado) * self.altura

        return x_viewport, y_viewport

    #inverso do transformar, canva -> mundo (usado p achar o obj sob o mouse)
    def para_mundo(self, window: Window, x_viewport: float, y_viewport: float) -> Tuple[float, float]:
        x_normalizado = (x_viewport - self.xmin) / self.largura
        y_normalizado = 1 - (y_viewport - self.ymin) / self.altura

        x = window.xmin + x_normalizado * window.largura
        y = window.ymin + y_normalizado * window.altura

        return x, y
