import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from sgi.dialogo_transformacao import (
    ABA_ESCALONAMENTO,
    ABA_ROTACAO,
    ABA_TRANSLACAO,
    DialogoTransformacao,
)
from sgi.display_file import DisplayFile
from sgi.objetos import COR_PADRAO, TIPOS, criar_objeto, interpretar_coordenadas
from sgi.viewport import Viewport
from sgi.window import Window


LARGURA_CANVAS = 800
ALTURA_CANVAS = 600

PASSO_PANNING = 0.1
FATOR_ZOOM = 1.1

COR_FUNDO = "white"
COR_EIXOS = "#cccccc"
ESPESSURA_LINHA = 1
ESPESSURA_PONTO = 5

# obj selecionado é desenhado mais grosso, p n esconder a cor dele
ESPESSURA_EXTRA_SELECIONADO = 2

# distancia max em pixels entre o mouse e o obj p considerar q ta "sob o mouse"
TOLERANCIA_SELECAO = 6


#TODO: essa classe precisa provavelmente ser quberada em uma subclasses, dps estruturo isso melhor
class Aplicacao:

    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        self.raiz.title("SGI - Sistema Gráfico Interativo")

        self.display_file = DisplayFile()
        self.window = Window(-400, -300, 400, 300)
        self.viewport = Viewport(0, 0, LARGURA_CANVAS, ALTURA_CANVAS)

        self._ultimo_arraste = None
        self.cor_selecionada = COR_PADRAO

        self._criar_painel_lateral()
        self._criar_canvas()
        self._criar_atalhos()
        self._adicionar_objetos_de_exemplo()

    def _criar_painel_lateral(self) -> None:
        painel = ttk.Frame(self.raiz, padding=8)
        painel.pack(side=tk.LEFT, fill=tk.Y)

        self._criar_lista_de_objetos(painel)
        self._criar_botoes_de_transformacao(painel)
        self._criar_formulario_de_objeto(painel)
        self._criar_controles_de_navegacao(painel)

    def _criar_lista_de_objetos(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Objetos", padding=4)
        quadro.pack(fill=tk.BOTH, expand=True)

        self.lista_objetos = tk.Listbox(quadro, height=10, exportselection=False)
        self.lista_objetos.pack(fill=tk.BOTH, expand=True)
        self.lista_objetos.bind("<<ListboxSelect>>", self._ao_selecionar_objeto)

        botao_remover = ttk.Button(quadro, text="Remover selecionado", command=self._remover_objeto)
        botao_remover.pack(fill=tk.X, pady=(4, 0))

    def _criar_botoes_de_transformacao(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Transformar selecionado", padding=4)
        quadro.pack(fill=tk.X, pady=(8, 0))

        botao_transladar = ttk.Button(quadro, text="Transladar (G)", command=self._abrir_translacao)
        botao_escalonar = ttk.Button(quadro, text="Escalonar (S)", command=self._abrir_escalonamento)
        botao_rotacionar = ttk.Button(quadro, text="Rotacionar (R)", command=self._abrir_rotacao)

        botao_transladar.pack(fill=tk.X)
        botao_escalonar.pack(fill=tk.X)
        botao_rotacionar.pack(fill=tk.X)

    def _criar_formulario_de_objeto(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Adicionar objeto (Shift+A)", padding=4)
        quadro.pack(fill=tk.X, pady=8)

        ttk.Label(quadro, text="Nome:").pack(anchor=tk.W)
        self.entrada_nome = ttk.Entry(quadro)
        self.entrada_nome.pack(fill=tk.X)

        ttk.Label(quadro, text="Tipo:").pack(anchor=tk.W, pady=(4, 0))
        self.tipo_selecionado = tk.StringVar(value="wireframe")

        for tipo in TIPOS:
            opcao = ttk.Radiobutton(
                quadro,
                text=tipo.capitalize(),
                value=tipo,
                variable=self.tipo_selecionado,
            )
            opcao.pack(anchor=tk.W)

        ttk.Label(quadro, text="Coordenadas (x1, y1),(x2, y2),...").pack(anchor=tk.W, pady=(4, 0))
        self.entrada_coordenadas = ttk.Entry(quadro)
        self.entrada_coordenadas.pack(fill=tk.X)
        self.entrada_coordenadas.bind("<Return>", self._adicionar_objeto)

        linha_cor = ttk.Frame(quadro)
        linha_cor.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(linha_cor, text="Cor:").pack(side=tk.LEFT)

        # tk.Label pq o ttk n deixa trocar o background facil
        self.amostra_cor = tk.Label(linha_cor, width=4, relief=tk.SUNKEN)
        self.amostra_cor.pack(side=tk.LEFT, padx=4)

        self.rotulo_cor = ttk.Label(linha_cor)
        self.rotulo_cor.pack(side=tk.LEFT)

        botao_cor = ttk.Button(linha_cor, text="Escolher...", command=self._escolher_cor)
        botao_cor.pack(side=tk.RIGHT)

        self._atualizar_amostra_de_cor()

        botao_adicionar = ttk.Button(quadro, text="Adicionar", command=self._adicionar_objeto)
        botao_adicionar.pack(fill=tk.X, pady=(4, 0))

    def _criar_controles_de_navegacao(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Navegação", padding=4)
        quadro.pack(fill=tk.X)

        setas = ttk.Frame(quadro)
        setas.pack()

        botao_cima = ttk.Button(setas, text="↑", width=3, command=self._mover_para_cima)
        botao_esquerda = ttk.Button(setas, text="←", width=3, command=self._mover_para_esquerda)
        botao_direita = ttk.Button(setas, text="→", width=3, command=self._mover_para_direita)
        botao_baixo = ttk.Button(setas, text="↓", width=3, command=self._mover_para_baixo)

        botao_cima.grid(row=0, column=1)
        botao_esquerda.grid(row=1, column=0)
        botao_direita.grid(row=1, column=2)
        botao_baixo.grid(row=2, column=1)

        zoom = ttk.Frame(quadro)
        zoom.pack(pady=(4, 0))

        botao_zoom_in = ttk.Button(zoom, text="Zoom +", command=self._aproximar)
        botao_zoom_out = ttk.Button(zoom, text="Zoom −", command=self._afastar)

        botao_zoom_in.pack(side=tk.LEFT)
        botao_zoom_out.pack(side=tk.LEFT)

        self.rotulo_window = ttk.Label(quadro, justify=tk.LEFT)
        self.rotulo_window.pack(anchor=tk.W, pady=(4, 0))

    def _criar_canvas(self) -> None:
        self.canvas = tk.Canvas(
            self.raiz,
            width=LARGURA_CANVAS,
            height=ALTURA_CANVAS,
            background=COR_FUNDO,
            highlightthickness=0,
        )
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", self._ao_redimensionar_canvas)

        #isso aq tava bugando, zoom c roda do mouse n parece consistent
        self.canvas.bind("<MouseWheel>", self._ao_rolar_mouse)
        self.canvas.bind("<Button-4>", self._aproximar)
        self.canvas.bind("<Button-5>", self._afastar)

        # panning c shift + drag c botao do meio
        self.canvas.bind("<Shift-ButtonPress-2>", self._iniciar_arraste)
        self.canvas.bind("<Shift-B2-Motion>", self._arrastar)
        self.canvas.bind("<ButtonRelease-2>", self._finalizar_arraste)

        # menu de contexto c botao direito p transformar o obj sob o mouse
        self.canvas.bind("<Button-3>", self._abrir_menu_de_contexto)
        self._criar_menu_de_contexto()

    def _criar_menu_de_contexto(self) -> None:
        self.menu_contexto = tk.Menu(self.canvas, tearoff=False)
        self.menu_contexto.add_command(label="Transladar (G)", command=self._abrir_translacao)
        self.menu_contexto.add_command(label="Escalonar (S)", command=self._abrir_escalonamento)
        self.menu_contexto.add_command(label="Rotacionar (R)", command=self._abrir_rotacao)
        self.menu_contexto.add_separator()
        self.menu_contexto.add_command(label="Remover", command=self._remover_objeto)

    def _criar_atalhos(self) -> None:
        self.raiz.bind("<Shift-A>", self._focar_formulario)
        self.canvas.bind("<Up>", self._mover_para_cima)
        self.canvas.bind("<Down>", self._mover_para_baixo)
        self.canvas.bind("<Left>", self._mover_para_esquerda)
        self.canvas.bind("<Right>", self._mover_para_direita)
        self.canvas.bind("<plus>", self._aproximar)
        self.canvas.bind("<minus>", self._afastar)
        self.canvas.bind("<KP_Add>", self._aproximar)
        self.canvas.bind("<KP_Subtract>", self._afastar)
        self.canvas.bind("<Button-1>", self._focar_canvas)

        # msm teclas do blender
        self.canvas.bind("<g>", self._abrir_translacao)
        self.canvas.bind("<s>", self._abrir_escalonamento)
        self.canvas.bind("<r>", self._abrir_rotacao)

    def _adicionar_objetos_de_exemplo(self) -> None:
        exemplos = [
            ("wireframe", "quadrado", "(-100, -100),(100, -100),(100, 100),(-100, 100)", (0, 0, 255)),
            ("wireframe", "triangulo", "(150, 50),(300, 50),(225, 180)", (0, 160, 0)),
            ("reta", "diagonal", "(-300, -250),(-150, 200)", (200, 0, 0)),
            ("ponto", "origem", "(0, 0)", (0, 0, 0)),
        ]

        for tipo, nome, texto, cor in exemplos:
            coordenadas = interpretar_coordenadas(texto)
            objeto = criar_objeto(tipo, nome, coordenadas, cor)
            self.display_file.adicionar(objeto)

        self._atualizar_lista_de_objetos()

    def desenhar(self) -> None:
        self.canvas.delete("all")

        self._desenhar_eixos()

        nome_selecionado = self._nome_selecionado()

        for objeto in self.display_file:
            if objeto.nome == nome_selecionado:
                espessura_extra = ESPESSURA_EXTRA_SELECIONADO
            else:
                espessura_extra = 0

            self._desenhar_objeto(objeto, objeto.cor_hex(), espessura_extra)

        self._atualizar_rotulo_window()

    def _desenhar_eixos(self) -> None:
        self._desenhar_segmento((self.window.xmin, 0), (self.window.xmax, 0), COR_EIXOS)
        self._desenhar_segmento((0, self.window.ymin), (0, self.window.ymax), COR_EIXOS)

    def _desenhar_objeto(self, objeto, cor: str, espessura_extra: int) -> None:
        segmentos = objeto.segmentos()

        if len(segmentos) == 0:
            for coordenada in objeto.coordenadas:
                self._desenhar_ponto(coordenada, cor, espessura_extra)

            return

        for inicio, fim in segmentos:
            self._desenhar_segmento(inicio, fim, cor, ESPESSURA_LINHA + espessura_extra)

    def _desenhar_ponto(self, coordenada, cor: str, espessura_extra: int = 0) -> None:
        x, y = self.viewport.transformar(self.window, coordenada[0], coordenada[1])

        # n achei primitiva de ponto do tkinter nas docs(pedi p claude ele n achou tb),
        # ent vou usar uma linha de 1 pixel c ponta arrendondada pq é o + proximo de um ponto na tela
        self.canvas.create_line(
            x,
            y,
            x + 1,
            y,
            fill=cor,
            width=ESPESSURA_PONTO + espessura_extra,
            capstyle=tk.ROUND,
        )

    def _desenhar_segmento(self, inicio, fim, cor: str, espessura: int = ESPESSURA_LINHA) -> None:
        x1, y1 = self.viewport.transformar(self.window, inicio[0], inicio[1])
        x2, y2 = self.viewport.transformar(self.window, fim[0], fim[1])

        self.canvas.create_line(x1, y1, x2, y2, fill=cor, width=espessura)

    def _atualizar_rotulo_window(self) -> None:
        texto = (
            f"Window:\n"
            f"  x: [{self.window.xmin:.1f}, {self.window.xmax:.1f}]\n"
            f"  y: [{self.window.ymin:.1f}, {self.window.ymax:.1f}]"
        )
        self.rotulo_window.configure(text=texto)

    def _adicionar_objeto(self, evento=None) -> None:
        nome = self.entrada_nome.get().strip()
        tipo = self.tipo_selecionado.get()
        texto = self.entrada_coordenadas.get().strip()

        if nome == "":
            messagebox.showerror("Erro", "Informe um nome para o objeto.")
            return

        try:
            coordenadas = interpretar_coordenadas(texto)
            objeto = criar_objeto(tipo, nome, coordenadas, self.cor_selecionada)
            self.display_file.adicionar(objeto)
        except Exception as erro:
            messagebox.showerror("Erro", f"Não foi possível adicionar o objeto:\n{erro}")
            return

        self.entrada_nome.delete(0, tk.END)
        self.entrada_coordenadas.delete(0, tk.END)

        self._atualizar_lista_de_objetos()
        self.desenhar()

    def _remover_objeto(self) -> None:
        nome = self._nome_selecionado()

        if nome is None:
            return

        self.display_file.remover(nome)

        self._atualizar_lista_de_objetos()
        self.desenhar()

    def _atualizar_lista_de_objetos(self) -> None:
        self.lista_objetos.delete(0, tk.END)

        for objeto in self.display_file:
            self.lista_objetos.insert(tk.END, objeto.descricao())

    def _escolher_cor(self) -> None:
        r, g, b = self.cor_selecionada
        cor_inicial = f"#{r:02x}{g:02x}{b:02x}"

        rgb, _ = colorchooser.askcolor(color=cor_inicial, title="Cor do objeto", parent=self.raiz)

        if rgb is None:
            return

        self.cor_selecionada = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        self._atualizar_amostra_de_cor()

    def _atualizar_amostra_de_cor(self) -> None:
        r, g, b = self.cor_selecionada

        self.amostra_cor.configure(background=f"#{r:02x}{g:02x}{b:02x}")
        self.rotulo_cor.configure(text=f"RGB({r}, {g}, {b})")

    def _abrir_translacao(self, evento=None) -> None:
        self._abrir_dialogo_de_transformacao(ABA_TRANSLACAO)

    def _abrir_escalonamento(self, evento=None) -> None:
        self._abrir_dialogo_de_transformacao(ABA_ESCALONAMENTO)

    def _abrir_rotacao(self, evento=None) -> None:
        self._abrir_dialogo_de_transformacao(ABA_ROTACAO)

    def _abrir_dialogo_de_transformacao(self, aba: int) -> None:
        nome = self._nome_selecionado()

        if nome is None:
            messagebox.showinfo("Nenhum objeto", "Selecione um objeto na lista para transformá-lo.")
            return

        objeto = self.display_file.buscar(nome)

        DialogoTransformacao(self.raiz, objeto, self.desenhar, aba)

    def _abrir_menu_de_contexto(self, evento) -> None:
        objeto = self._objeto_sob_o_mouse(evento.x, evento.y)

        if objeto is None:
            return

        self._selecionar_na_lista(objeto.nome)
        self.desenhar()

        self.menu_contexto.tk_popup(evento.x_root, evento.y_root)

    #em 2D basta achar o obj c a menor distancia (em pixels) ate o mouse
    def _objeto_sob_o_mouse(self, x: float, y: float):
        mais_proximo = None
        menor_distancia = TOLERANCIA_SELECAO

        for objeto in self.display_file:
            distancia = self._distancia_ate_objeto(objeto, x, y)

            if distancia <= menor_distancia:
                mais_proximo = objeto
                menor_distancia = distancia

        return mais_proximo

    def _distancia_ate_objeto(self, objeto, x: float, y: float) -> float:
        segmentos = objeto.segmentos()

        if len(segmentos) == 0:
            for coordenada in objeto.coordenadas:
                segmentos.append((coordenada, coordenada))

        menor = float("inf")

        for inicio, fim in segmentos:
            x1, y1 = self.viewport.transformar(self.window, inicio[0], inicio[1])
            x2, y2 = self.viewport.transformar(self.window, fim[0], fim[1])

            distancia = _distancia_ponto_segmento(x, y, x1, y1, x2, y2)

            if distancia < menor:
                menor = distancia

        return menor

    def _selecionar_na_lista(self, nome: str) -> None:
        self.lista_objetos.selection_clear(0, tk.END)

        for indice, objeto in enumerate(self.display_file):
            if objeto.nome == nome:
                self.lista_objetos.selection_set(indice)
                self.lista_objetos.see(indice)

    def _nome_selecionado(self):
        selecao = self.lista_objetos.curselection()

        if len(selecao) == 0:
            return None

        indice = selecao[0]
        objetos = list(self.display_file)

        return objetos[indice].nome

    def _ao_selecionar_objeto(self, evento=None) -> None:
        self.desenhar()

    def _focar_formulario(self, evento=None) -> None:
        self.entrada_nome.focus_set()

    def _focar_canvas(self, evento=None) -> None:
        self.canvas.focus_set()

    def _mover_para_cima(self, evento=None) -> None:
        self.window.mover_proporcional(0, PASSO_PANNING)
        self.desenhar()

    def _mover_para_baixo(self, evento=None) -> None:
        self.window.mover_proporcional(0, -PASSO_PANNING)
        self.desenhar()

    def _mover_para_esquerda(self, evento=None) -> None:
        self.window.mover_proporcional(-PASSO_PANNING, 0)
        self.desenhar()

    def _mover_para_direita(self, evento=None) -> None:
        self.window.mover_proporcional(PASSO_PANNING, 0)
        self.desenhar()

    def _aproximar(self, evento=None) -> None:
        self.window.escalar(FATOR_ZOOM)
        self.desenhar()

    def _afastar(self, evento=None) -> None:
        self.window.escalar(1 / FATOR_ZOOM)
        self.desenhar()

    def _ao_rolar_mouse(self, evento) -> None:
        if evento.delta > 0:
            self._aproximar()
        else:
            self._afastar()

    def _iniciar_arraste(self, evento) -> None:
        self._ultimo_arraste = (evento.x, evento.y)

    def _arrastar(self, evento) -> None:
        if self._ultimo_arraste is None:
            return

        anterior_x, anterior_y = self._ultimo_arraste
        pixels_x = evento.x - anterior_x
        pixels_y = evento.y - anterior_y

        # drag da cena p direita é q nem mover window p esuqerda, tem q lembrar q isso é invertido
        # eixo y cresce p baixo, ent sinal y n inverte
        deslocamento_x = -pixels_x * self.window.largura / self.viewport.largura
        deslocamento_y = pixels_y * self.window.altura / self.viewport.altura

        self.window.mover(deslocamento_x, deslocamento_y)
        self._ultimo_arraste = (evento.x, evento.y)
        self.desenhar()

    def _finalizar_arraste(self, evento=None) -> None:
        self._ultimo_arraste = None

    def _ao_redimensionar_canvas(self, evento) -> None:
        if evento.width <= 1 or evento.height <= 1:
            return

        # manter msm escala ao fazer redimensionamento, pq window e viewport continuam na msm proporcao
        unidades_por_pixel = self.window.largura / self.viewport.largura

        self.viewport.redimensionar(evento.width, evento.height)
        self.window.definir_tamanho(
            evento.width * unidades_por_pixel,
            evento.height * unidades_por_pixel,
        )

        self.desenhar()


def _distancia_ponto_segmento(px, py, x1, y1, x2, y2) -> float:
    dx = x2 - x1
    dy = y2 - y1
    comprimento_quadrado = dx * dx + dy * dy

    if comprimento_quadrado == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5

    # projecao do ponto na reta, limitada ao segmento
    t = ((px - x1) * dx + (py - y1) * dy) / comprimento_quadrado
    t = max(0.0, min(1.0, t))

    mais_proximo_x = x1 + t * dx
    mais_proximo_y = y1 + t * dy

    return ((px - mais_proximo_x) ** 2 + (py - mais_proximo_y) ** 2) ** 0.5


def executar() -> None:
    raiz = tk.Tk()
    Aplicacao(raiz)
    raiz.mainloop()
