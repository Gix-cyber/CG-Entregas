import tkinter as tk
from tkinter import ttk

from sgi.dialogo_transformacao import DialogoTransformacao
from sgi.objetos3d import interpretar_ponto
from sgi.transformacoes3d import (
    EIXO_X,
    EIXO_Y,
    EIXO_Z,
    Escalonamento3D,
    RotacaoEixoArbitrario,
    RotacaoEixoDoObjeto,
    Translacao3D,
    matriz_resultante,
)


ROTACAO_EIXO_ARBITRARIO = "arbitrario"


class DialogoTransformacao3D(DialogoTransformacao):

    def _criar_aba_translacao(self) -> None:
        aba = ttk.Frame(self.abas, padding=8)
        self.abas.add(aba, text="Translação (G)")

        self.translacao_dx = self._criar_campo(aba, "dx:", "0", 0)
        self.translacao_dy = self._criar_campo(aba, "dy:", "0", 1)
        self.translacao_dz = self._criar_campo(aba, "dz:", "0", 2)

        ttk.Label(aba, text="Nos eixos do mundo").grid(
            row=3,
            column=0,
            columnspan=2,
            sticky=tk.W,
            pady=(4, 0),
        )

        botao = ttk.Button(aba, text="Adicionar à lista", command=self._adicionar_translacao)
        botao.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

    def _criar_aba_escalonamento(self) -> None:
        aba = ttk.Frame(self.abas, padding=8)
        self.abas.add(aba, text="Escala (S)")

        self.escala_sx = self._criar_campo(aba, "sx:", "1", 0)
        self.escala_sy = self._criar_campo(aba, "sy:", "1", 1)
        self.escala_sz = self._criar_campo(aba, "sz:", "1", 2)

        ttk.Label(aba, text="Em torno do centro do objeto").grid(
            row=3,
            column=0,
            columnspan=2,
            sticky=tk.W,
            pady=(4, 0),
        )

        botao = ttk.Button(aba, text="Adicionar à lista", command=self._adicionar_escalonamento)
        botao.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

    def _criar_aba_rotacao(self) -> None:
        aba = ttk.Frame(self.abas, padding=8)
        self.abas.add(aba, text="Rotação (R)")

        self.rotacao_angulo = self._criar_campo(aba, "Ângulo (°):", "0", 0)

        self.rotacao_centro = tk.StringVar(value=EIXO_Z)
        opcoes = [
            ("Eixo X pelo centro do objeto", EIXO_X),
            ("Eixo Y pelo centro do objeto", EIXO_Y),
            ("Eixo Z pelo centro do objeto", EIXO_Z),
            ("Eixo arbitrário (de A para B)", ROTACAO_EIXO_ARBITRARIO),
        ]

        linha = 1

        for texto, valor in opcoes:
            opcao = ttk.Radiobutton(
                aba,
                text=texto,
                value=valor,
                variable=self.rotacao_centro,
                command=self._atualizar_campos_do_ponto,
            )
            opcao.grid(row=linha, column=0, columnspan=2, sticky=tk.W)
            linha += 1

        self.rotacao_ponto_a = self._criar_campo(aba, "A (x, y, z):", "(0, 0, 0)", linha)
        self.rotacao_ponto_b = self._criar_campo(aba, "B (x, y, z):", "(1, 1, 1)", linha + 1)
        self._atualizar_campos_do_ponto()

        botao = ttk.Button(aba, text="Adicionar à lista", command=self._adicionar_rotacao)
        botao.grid(row=linha + 2, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

    def _atualizar_campos_do_ponto(self) -> None:
        if self.rotacao_centro.get() == ROTACAO_EIXO_ARBITRARIO:
            estado = tk.NORMAL
        else:
            estado = tk.DISABLED

        self.rotacao_ponto_a.configure(state=estado)
        self.rotacao_ponto_b.configure(state=estado)

    def _adicionar_translacao(self) -> None:
        try:
            dx = float(self.translacao_dx.get())
            dy = float(self.translacao_dy.get())
            dz = float(self.translacao_dz.get())
            transformacao = Translacao3D(dx, dy, dz)
        except ValueError as erro:
            self._mostrar_erro(erro)
            return

        self._enfileirar(transformacao)

    def _adicionar_escalonamento(self) -> None:
        try:
            sx = float(self.escala_sx.get())
            sy = float(self.escala_sy.get())
            sz = float(self.escala_sz.get())
            transformacao = Escalonamento3D(sx, sy, sz)
        except ValueError as erro:
            self._mostrar_erro(erro)
            return

        self._enfileirar(transformacao)

    def _adicionar_rotacao(self) -> None:
        eixo = self.rotacao_centro.get()

        try:
            angulo = float(self.rotacao_angulo.get())

            if eixo == ROTACAO_EIXO_ARBITRARIO:
                ponto_a = interpretar_ponto(self.rotacao_ponto_a.get())
                ponto_b = interpretar_ponto(self.rotacao_ponto_b.get())
                transformacao = RotacaoEixoArbitrario(angulo, ponto_a, ponto_b)
            else:
                transformacao = RotacaoEixoDoObjeto(eixo, angulo)
        except (ValueError, SyntaxError, NameError, TypeError) as erro:
            self._mostrar_erro(erro)
            return

        self._enfileirar(transformacao)

    def _transformar_objeto(self) -> None:
        matriz = matriz_resultante(self.transformacoes, self.objeto.centro())
        self.objeto.transformar(matriz)
