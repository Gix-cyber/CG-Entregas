#TODO: rever zoom c objetos adicionados, tem alguma coisa estranha em relacao aos pixels (testar c reta)

class Window:

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

    @property
    def centro(self):
        centro_x = (self.xmin + self.xmax) / 2
        centro_y = (self.ymin + self.ymax) / 2

        return centro_x, centro_y

    #panning normal
    def mover(self, deslocamento_x: float, deslocamento_y: float) -> None:
        self.xmin += deslocamento_x
        self.xmax += deslocamento_x
        self.ymin += deslocamento_y
        self.ymax += deslocamento_y

    #panning em porcentagem da largura
    def mover_proporcional(self, fracao_x: float, fracao_y: float) -> None:
        deslocamento_x = fracao_x * self.largura
        deslocamento_y = fracao_y * self.altura

        self.mover(deslocamento_x, deslocamento_y)

    #fator do zooming >1 aproxima, <1 tem q afastar
    def escalar(self, fator: float) -> None:
        if fator <= 0:
            raise ValueError("O fator de zoom deve ser positivo.")

        centro_x, centro_y = self.centro
        nova_meia_largura = self.largura / (2 * fator)
        nova_meia_altura = self.altura / (2 * fator)

        self._definir_pelo_centro(centro_x, centro_y, nova_meia_largura, nova_meia_altura)

    #height e witdh da window alteradas mantendo centro. Qm chama precisa preserver proporcao do viewport,
    #pq a transformada precisa usar a msm escala em x e y (se n fizer assim distorce tava tendo problema c isso
    def definir_tamanho(self, largura: float, altura: float) -> None:
        centro_x, centro_y = self.centro

        self._definir_pelo_centro(centro_x, centro_y, largura / 2, altura / 2)

    def _definir_pelo_centro(
        self,
        centro_x: float,
        centro_y: float,
        meia_largura: float,
        meia_altura: float,
    ) -> None:
        self.xmin = centro_x - meia_largura
        self.xmax = centro_x + meia_largura
        self.ymin = centro_y - meia_altura
        self.ymax = centro_y + meia_altura
