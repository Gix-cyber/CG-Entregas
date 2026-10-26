import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List

from sgi.objetos import ObjetoGrafico
from sgi.transformacoes import (
    Escalonamento,
    RotacaoCentroMundo,
    RotacaoCentroObjeto,
    RotacaoPontoArbitrario,
    Transformacao,
    Translacao,
    matriz_resultante,
    transformar,
)


ABA_TRANSLACAO = 0
ABA_ESCALONAMENTO = 1
ABA_ROTACAO = 2

ROTACAO_CENTRO_OBJETO = "objeto"
ROTACAO_CENTRO_MUNDO = "mundo"
ROTACAO_PONTO_ARBITRARIO = "ponto"


#janela p enfileirar transformacoes de um obj. A matriz resultante so é calculada
#qnd o usuario clica em aplicar, depois de entrar c todas
class DialogoTransformacao:

    def __init__(
        self,
        pai: tk.Misc,
        objeto: ObjetoGrafico,
        ao_aplicar: Callable[[], None],
        aba_inicial: int = ABA_TRANSLACAO,
        angulo_window: float = 0.0,
    ):
        self.objeto = objeto
        self.angulo_window = angulo_window
        self.ao_aplicar = ao_aplicar
        self.transformacoes: List[Transformacao] = []

        self.janela = tk.Toplevel(pai)
        self.janela.title(f"Transformar '{objeto.nome}'")
        self.janela.transient(pai)
        self.janela.resizable(False, False)

        conteudo = ttk.Frame(self.janela, padding=8)
        conteudo.pack(fill=tk.BOTH, expand=True)

        self._criar_abas(conteudo)
        self._criar_lista_de_transformacoes(conteudo)
        self._criar_botoes(conteudo)

        self.abas.select(aba_inicial)

        self.janela.bind("<Escape>", self._cancelar)
        self.janela.grab_set()
        self.janela.focus_set()

    def _criar_abas(self, conteudo: ttk.Frame) -> None:
        self.abas = ttk.Notebook(conteudo)
        self.abas.grid(row=0, column=0, sticky=tk.NSEW)

        self._criar_aba_translacao()
        self._criar_aba_escalonamento()
        self._criar_aba_rotacao()

    def _criar_aba_translacao(self) -> None:
        aba = ttk.Frame(self.abas, padding=8)
        self.abas.add(aba, text="Translação (G)")

        self.translacao_dx = self._criar_campo(aba, "dx:", "0", 0)
        self.translacao_dy = self._criar_campo(aba, "dy:", "0", 1)

        ttk.Label(aba, text="Nos eixos da tela (para cima do usuário)").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky=tk.W,
            pady=(4, 0),
        )

        botao = ttk.Button(aba, text="Adicionar à lista", command=self._adicionar_translacao)
        botao.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

    def _criar_aba_escalonamento(self) -> None:
        aba = ttk.Frame(self.abas, padding=8)
        self.abas.add(aba, text="Escala (S)")

        self.escala_sx = self._criar_campo(aba, "sx:", "1", 0)
        self.escala_sy = self._criar_campo(aba, "sy:", "1", 1)

        ttk.Label(aba, text="Em torno do centro do objeto").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky=tk.W,
            pady=(4, 0),
        )

        botao = ttk.Button(aba, text="Adicionar à lista", command=self._adicionar_escalonamento)
        botao.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

    def _criar_aba_rotacao(self) -> None:
        aba = ttk.Frame(self.abas, padding=8)
        self.abas.add(aba, text="Rotação (R)")

        self.rotacao_angulo = self._criar_campo(aba, "Ângulo (°):", "0", 0)

        self.rotacao_centro = tk.StringVar(value=ROTACAO_CENTRO_OBJETO)
        opcoes = [
            ("Em torno do centro do objeto", ROTACAO_CENTRO_OBJETO),
            ("Em torno do centro do mundo", ROTACAO_CENTRO_MUNDO),
            ("Em torno de um ponto qualquer", ROTACAO_PONTO_ARBITRARIO),
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

        self.rotacao_px = self._criar_campo(aba, "Ponto x:", "0", linha)
        self.rotacao_py = self._criar_campo(aba, "Ponto y:", "0", linha + 1)
        self._atualizar_campos_do_ponto()

        botao = ttk.Button(aba, text="Adicionar à lista", command=self._adicionar_rotacao)
        botao.grid(row=linha + 2, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

    def _criar_campo(self, aba: ttk.Frame, rotulo: str, valor_inicial: str, linha: int) -> ttk.Entry:
        ttk.Label(aba, text=rotulo).grid(row=linha, column=0, sticky=tk.W, pady=2)

        entrada = ttk.Entry(aba, width=12)
        entrada.insert(0, valor_inicial)
        entrada.grid(row=linha, column=1, sticky=tk.EW, pady=2)

        return entrada

    def _criar_lista_de_transformacoes(self, conteudo: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(conteudo, text="Transformações a aplicar", padding=4)
        quadro.grid(row=0, column=1, sticky=tk.NSEW, padx=(8, 0))

        self.lista = tk.Listbox(quadro, width=34, height=10, exportselection=False)
        self.lista.pack(fill=tk.BOTH, expand=True)

        botao_remover = ttk.Button(quadro, text="Remover selecionada", command=self._remover_transformacao)
        botao_remover.pack(fill=tk.X, pady=(4, 0))

    def _criar_botoes(self, conteudo: ttk.Frame) -> None:
        botoes = ttk.Frame(conteudo)
        botoes.grid(row=1, column=0, columnspan=2, sticky=tk.E, pady=(8, 0))

        botao_cancelar = ttk.Button(botoes, text="Cancelar", command=self._cancelar)
        botao_aplicar = ttk.Button(botoes, text="Aplicar", command=self._aplicar)

        botao_cancelar.pack(side=tk.LEFT)
        botao_aplicar.pack(side=tk.LEFT, padx=(4, 0))

    def _atualizar_campos_do_ponto(self) -> None:
        if self.rotacao_centro.get() == ROTACAO_PONTO_ARBITRARIO:
            estado = tk.NORMAL
        else:
            estado = tk.DISABLED

        self.rotacao_px.configure(state=estado)
        self.rotacao_py.configure(state=estado)

    def _adicionar_translacao(self) -> None:
        try:
            dx = float(self.translacao_dx.get())
            dy = float(self.translacao_dy.get())
            transformacao = Translacao(dx, dy, self.angulo_window)
        except ValueError as erro:
            self._mostrar_erro(erro)
            return

        self._enfileirar(transformacao)

    def _adicionar_escalonamento(self) -> None:
        try:
            sx = float(self.escala_sx.get())
            sy = float(self.escala_sy.get())
            transformacao = Escalonamento(sx, sy)
        except ValueError as erro:
            self._mostrar_erro(erro)
            return

        self._enfileirar(transformacao)

    def _adicionar_rotacao(self) -> None:
        centro = self.rotacao_centro.get()

        try:
            angulo = float(self.rotacao_angulo.get())

            if centro == ROTACAO_CENTRO_MUNDO:
                transformacao = RotacaoCentroMundo(angulo)
            elif centro == ROTACAO_CENTRO_OBJETO:
                transformacao = RotacaoCentroObjeto(angulo)
            else:
                px = float(self.rotacao_px.get())
                py = float(self.rotacao_py.get())
                transformacao = RotacaoPontoArbitrario(angulo, (px, py))
        except ValueError as erro:
            self._mostrar_erro(erro)
            return

        self._enfileirar(transformacao)

    def _enfileirar(self, transformacao: Transformacao) -> None:
        self.transformacoes.append(transformacao)
        self.lista.insert(tk.END, transformacao.descricao())

    def _remover_transformacao(self) -> None:
        selecao = self.lista.curselection()

        if len(selecao) == 0:
            return

        indice = selecao[0]

        del self.transformacoes[indice]
        self.lista.delete(indice)

    def _aplicar(self) -> None:
        if len(self.transformacoes) == 0:
            messagebox.showinfo(
                "Nada a aplicar",
                "Adicione ao menos uma transformação à lista.",
                parent=self.janela,
            )
            return

        matriz = matriz_resultante(self.transformacoes, self.objeto)
        transformar(self.objeto, matriz)

        self.janela.destroy()
        self.ao_aplicar()

    def _cancelar(self, evento=None) -> None:
        self.janela.destroy()

    def _mostrar_erro(self, erro: Exception) -> None:
        messagebox.showerror("Erro", f"Valor inválido:\n{erro}", parent=self.janela)
