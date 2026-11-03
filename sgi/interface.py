import math
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from sgi.dialogo_transformacao import (
    ABA_ESCALONAMENTO,
    ABA_ROTACAO,
    ABA_TRANSLACAO,
    DialogoTransformacao,
)
from sgi.clipping import (
    ALGORITMO_RETA_PADRAO,
    ALGORITMOS_RETA,
    PRIMITIVA_POLIGONO,
    PRIMITIVA_PONTO,
    PRIMITIVA_SEGMENTO,
)
from sgi.descritor_obj import escrever_mundo, ler_mundo
from sgi.display_file import DisplayFile
from sgi.objetos import COR_PADRAO, TIPOS, Wireframe, criar_objeto, interpretar_coordenadas
from sgi.transformacoes import transformar_ponto
from sgi.viewport import Viewport
from sgi.window import Window


LARGURA_CANVAS = 800
ALTURA_CANVAS = 600

PASSO_PANNING = 0.1
FATOR_ZOOM = 1.1

# passo em graus do Shift + NumPad 4/6, igual ao blender
PASSO_ROTACAO = 15

# a viewport é menor q o canvas, c uma moldura em volta. Assim se o clipping deixar
# passar alguma coisa ela aparece fora da moldura, em vez de ser cortada pelo proprio canvas
MARGEM_VIEWPORT = 10
COR_MOLDURA = "#ff00ff"

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
        # window c a msm proporcao da viewport, p n distorcer
        largura_viewport = LARGURA_CANVAS - 2 * MARGEM_VIEWPORT
        altura_viewport = ALTURA_CANVAS - 2 * MARGEM_VIEWPORT

        self.window = Window(
            -largura_viewport / 2,
            -altura_viewport / 2,
            largura_viewport / 2,
            altura_viewport / 2,
        )
        self.viewport = Viewport(
            MARGEM_VIEWPORT,
            MARGEM_VIEWPORT,
            MARGEM_VIEWPORT + largura_viewport,
            MARGEM_VIEWPORT + altura_viewport,
        )

        self._ultimo_arraste = None
        self.cor_selecionada = COR_PADRAO

        self._criar_menu()
        self._criar_painel_lateral()
        self._criar_canvas()
        self._criar_atalhos()
        self._adicionar_objetos_de_exemplo()

    def _criar_menu(self) -> None:
        barra = tk.Menu(self.raiz)

        menu_arquivo = tk.Menu(barra, tearoff=False)
        menu_arquivo.add_command(label="Abrir mundo (.obj)...", command=self._abrir_mundo)
        menu_arquivo.add_command(label="Importar .obj...", command=self._importar_obj)
        menu_arquivo.add_command(label="Salvar mundo (.obj)...", command=self._salvar_mundo)

        barra.add_cascade(label="Arquivo", menu=menu_arquivo)
        self.raiz.configure(menu=barra)

    def _criar_painel_lateral(self) -> None:
        painel = ttk.Frame(self.raiz, padding=8)
        painel.pack(side=tk.LEFT, fill=tk.Y)

        coluna_edicao = ttk.Frame(painel)
        coluna_edicao.pack(side=tk.LEFT, fill=tk.Y)
        coluna_cena = ttk.Frame(painel)
        coluna_cena.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        self._criar_formulario_de_objeto(coluna_edicao)
        self._criar_selecao_de_clipping(coluna_edicao)
        self._criar_botoes_de_transformacao(coluna_edicao)
        self._criar_controles_de_navegacao(coluna_cena)
        self._criar_lista_de_objetos(coluna_cena)

    def _criar_lista_de_objetos(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Objetos", padding=4)
        quadro.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # o botao é empacotado antes da lista p n ser ele o cortado qnd falta espaco
        botao_remover = ttk.Button(quadro, text="Remover selecionado", command=self._remover_objeto)
        botao_remover.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))

        self.lista_objetos = tk.Listbox(quadro, height=4, exportselection=False)
        self.lista_objetos.pack(fill=tk.BOTH, expand=True)
        self.lista_objetos.bind("<<ListboxSelect>>", self._ao_selecionar_objeto)

    def _criar_botoes_de_transformacao(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Transformar selecionado", padding=4)
        quadro.pack(side=tk.TOP, fill=tk.X, pady=(8, 0))

        botao_transladar = ttk.Button(quadro, text="Transladar (G)", command=self._abrir_translacao)
        botao_escalonar = ttk.Button(quadro, text="Escalonar (S)", command=self._abrir_escalonamento)
        botao_rotacionar = ttk.Button(quadro, text="Rotacionar (R)", command=self._abrir_rotacao)

        botao_transladar.pack(fill=tk.X)
        botao_escalonar.pack(fill=tk.X)
        botao_rotacionar.pack(fill=tk.X)

    #o algoritmo de clipping de reta pode ser trocado a qlqr momento, e vale p retas,
    #arestas de wireframe e eixos. Pontos e poligonos preenchidos tem algoritmo proprio
    def _criar_selecao_de_clipping(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Clipping de retas", padding=4)
        quadro.pack(side=tk.TOP, fill=tk.X, pady=(8, 0))

        self.algoritmo_reta_selecionado = tk.StringVar(value=ALGORITMO_RETA_PADRAO)

        for nome in ALGORITMOS_RETA:
            opcao = ttk.Radiobutton(
                quadro,
                text=nome,
                value=nome,
                variable=self.algoritmo_reta_selecionado,
                command=self.desenhar,
            )
            opcao.pack(anchor=tk.W)

    def _criar_formulario_de_objeto(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Adicionar objeto (Shift+A)", padding=4)
        quadro.pack(side=tk.TOP, fill=tk.X)

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
                command=self._atualizar_opcao_de_preenchimento,
            )
            opcao.pack(anchor=tk.W)

        # so faz sentido p wireframe, ent fica desabilitado nos outros tipos
        self.preenchido_selecionado = tk.BooleanVar(value=False)
        self.opcao_preenchido = ttk.Checkbutton(
            quadro,
            text="Preenchido",
            variable=self.preenchido_selecionado,
        )
        self.opcao_preenchido.pack(anchor=tk.W, padx=(16, 0))

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

    def _atualizar_opcao_de_preenchimento(self) -> None:
        if self.tipo_selecionado.get() == Wireframe.tipo:
            self.opcao_preenchido.state(["!disabled"])
        else:
            self.opcao_preenchido.state(["disabled"])

    def _criar_controles_de_navegacao(self, painel: ttk.Frame) -> None:
        quadro = ttk.LabelFrame(painel, text="Navegação", padding=4)
        quadro.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        # setas a esquerda e zoom/giro a direita, lado a lado, p o quadro n ficar alto demais
        controles = ttk.Frame(quadro)
        controles.pack()

        setas = ttk.Frame(controles)
        setas.pack(side=tk.LEFT)

        botao_cima = ttk.Button(setas, text="↑", width=3, command=self._mover_para_cima)
        botao_esquerda = ttk.Button(setas, text="←", width=3, command=self._mover_para_esquerda)
        botao_direita = ttk.Button(setas, text="→", width=3, command=self._mover_para_direita)
        botao_baixo = ttk.Button(setas, text="↓", width=3, command=self._mover_para_baixo)

        botao_cima.grid(row=0, column=1)
        botao_esquerda.grid(row=1, column=0)
        botao_direita.grid(row=1, column=2)
        botao_baixo.grid(row=2, column=1)

        ajustes = ttk.Frame(controles)
        ajustes.pack(side=tk.LEFT, padx=(8, 0))

        botao_zoom_in = ttk.Button(ajustes, text="Zoom +", command=self._aproximar)
        botao_zoom_out = ttk.Button(ajustes, text="Zoom −", command=self._afastar)

        botao_zoom_in.pack(fill=tk.X)
        botao_zoom_out.pack(fill=tk.X)

        giro = ttk.Frame(ajustes)
        giro.pack(fill=tk.X)

        botao_anti_horario = ttk.Button(giro, text="⟲", width=3, command=self._girar_anti_horario)
        botao_horario = ttk.Button(giro, text="⟳", width=3, command=self._girar_horario)

        botao_anti_horario.pack(side=tk.LEFT, fill=tk.X, expand=True)
        botao_horario.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # rotacao é sempre em torno do centro da window, ent so precisa do angulo
        rotacao = ttk.Frame(quadro)
        rotacao.pack(pady=(4, 0))

        ttk.Label(rotacao, text="Rotação (°):").pack(side=tk.LEFT)

        self.entrada_angulo_window = ttk.Entry(rotacao, width=6)
        self.entrada_angulo_window.insert(0, str(PASSO_ROTACAO))
        self.entrada_angulo_window.pack(side=tk.LEFT, padx=(4, 0))
        self.entrada_angulo_window.bind("<Return>", self._rotacionar_window_pelo_campo)

        botao_rotacionar = ttk.Button(rotacao, text="Girar", command=self._rotacionar_window_pelo_campo)
        botao_rotacionar.pack(side=tk.LEFT, padx=(4, 0))

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

        # rotacao da window, Shift + NumPad 4/6 como no blender. C numlock ligado
        # o shift faz o teclado mandar KP_Left/KP_Right, ent liga as duas formas
        self.canvas.bind("<Shift-KP_4>", self._girar_anti_horario)
        self.canvas.bind("<Shift-KP_Left>", self._girar_anti_horario)
        self.canvas.bind("<Shift-KP_6>", self._girar_horario)
        self.canvas.bind("<Shift-KP_Right>", self._girar_horario)

    def _adicionar_objetos_de_exemplo(self) -> None:
        # o losango e a reta longa ja comecam passando da borda, p mostrar o clipping
        exemplos = [
            ("wireframe", "quadrado", "(-100, -100),(100, -100),(100, 100),(-100, 100)", (0, 0, 255), False),
            ("wireframe", "triangulo", "(150, 50),(300, 50),(225, 180)", (0, 160, 0), True),
            ("wireframe", "losango", "(300, -150),(480, -50),(300, 50),(120, -50)", (255, 160, 0), True),
            ("reta", "diagonal", "(-300, -250),(-150, 200)", (200, 0, 0), False),
            ("reta", "atravessa", "(-600, 150),(600, 250)", (128, 0, 128), False),
            ("ponto", "origem", "(0, 0)", (0, 0, 0), False),
        ]

        for tipo, nome, texto, cor, preenchido in exemplos:
            coordenadas = interpretar_coordenadas(texto)
            objeto = criar_objeto(tipo, nome, coordenadas, cor, preenchido)
            self.display_file.adicionar(objeto)

        self._atualizar_lista_de_objetos()

    def desenhar(self) -> None:
        self.canvas.delete("all")

        # gera a descricao em SCN de todo o mundo antes de desenhar
        self.display_file.normalizar(self.window.matriz_normalizacao())

        self._desenhar_eixos()
        self._desenhar_moldura()

        nome_selecionado = self._nome_selecionado()

        for objeto in self.display_file:
            if objeto.nome == nome_selecionado:
                espessura_extra = ESPESSURA_EXTRA_SELECIONADO
            else:
                espessura_extra = 0

            self._desenhar_objeto(objeto, objeto.cor_hex(), espessura_extra)

        self._atualizar_rotulo_window()

    #c a window rotacionada n da p usar os limites dela p cortar os eixos. Qlqr ponto da window
    #ta a no max meia diagonal do centro, ent um trecho de uma diagonal p cada lado cobre ela toda
    def _desenhar_eixos(self) -> None:
        centro_x, centro_y = self.window.centro
        alcance = math.hypot(self.window.largura, self.window.altura)

        eixo_x = ((centro_x - alcance, 0), (centro_x + alcance, 0))
        eixo_y = ((0, centro_y - alcance), (0, centro_y + alcance))

        matriz = self.window.matriz_normalizacao()
        algoritmo_reta = self._algoritmo_reta()

        for inicio, fim in (eixo_x, eixo_y):
            inicio_normalizado = transformar_ponto(inicio, matriz)
            fim_normalizado = transformar_ponto(fim, matriz)

            # os eixos tb passam pelo clipping, senao vazariam da moldura
            recortado = algoritmo_reta(inicio_normalizado, fim_normalizado)

            if recortado is None:
                continue

            self._desenhar_segmento(recortado[0], recortado[1], COR_EIXOS)

    #a moldura é o contorno da viewport (n da window), desenhado direto em pixels
    def _desenhar_moldura(self) -> None:
        self.canvas.create_rectangle(
            self.viewport.xmin,
            self.viewport.ymin,
            self.viewport.xmax,
            self.viewport.ymax,
            outline=COR_MOLDURA,
        )

    def _algoritmo_reta(self):
        nome = self.algoritmo_reta_selecionado.get()

        return ALGORITMOS_RETA[nome]

    #pipeline: WC -> SCN (cache do display file) -> clipping -> viewport.
    #so as primitivas q sobram do clipping passam pela transformada de viewport
    def _desenhar_objeto(self, objeto, cor: str, espessura_extra: int) -> None:
        primitivas = objeto.clipar(self._algoritmo_reta())

        for tipo, coordenadas in primitivas:
            if tipo == PRIMITIVA_PONTO:
                self._desenhar_ponto(coordenadas[0], cor, espessura_extra)
            elif tipo == PRIMITIVA_SEGMENTO:
                self._desenhar_segmento(coordenadas[0], coordenadas[1], cor, ESPESSURA_LINHA + espessura_extra)
            elif tipo == PRIMITIVA_POLIGONO:
                self._desenhar_poligono(coordenadas, cor, espessura_extra)

    def _desenhar_ponto(self, coordenada, cor: str, espessura_extra: int = 0) -> None:
        x, y = self.viewport.transformar(coordenada[0], coordenada[1])

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
        x1, y1 = self.viewport.transformar(inicio[0], inicio[1])
        x2, y2 = self.viewport.transformar(fim[0], fim[1])

        self.canvas.create_line(x1, y1, x2, y2, fill=cor, width=espessura)

    #primitiva de preenchimento do tkinter. O contorno fica na msm cor e engrossa qnd selecionado
    def _desenhar_poligono(self, coordenadas, cor: str, espessura_extra: int = 0) -> None:
        pontos_viewport = []

        for x_normalizado, y_normalizado in coordenadas:
            x, y = self.viewport.transformar(x_normalizado, y_normalizado)
            pontos_viewport.append(x)
            pontos_viewport.append(y)

        self.canvas.create_polygon(
            pontos_viewport,
            fill=cor,
            outline=cor,
            width=ESPESSURA_LINHA + espessura_extra,
        )

    def _atualizar_rotulo_window(self) -> None:
        centro_x, centro_y = self.window.centro

        texto = (
            f"Window:\n"
            f"  centro: ({centro_x:.1f}, {centro_y:.1f})\n"
            f"  tamanho: {self.window.largura:.1f} x {self.window.altura:.1f}\n"
            f"  ângulo: {self.window.angulo:.1f}°"
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
            preenchido = self.preenchido_selecionado.get()
            objeto = criar_objeto(tipo, nome, coordenadas, self.cor_selecionada, preenchido)
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

        # passa o angulo da window p translacao seguir o "p cima" do usuario
        DialogoTransformacao(self.raiz, objeto, self.desenhar, aba, self.window.angulo)

    def _abrir_menu_de_contexto(self, evento) -> None:
        # fora da viewport tudo foi clipado, ent n tem obj visivel p selecionar
        if not self._dentro_da_viewport(evento.x, evento.y):
            return

        objeto = self._objeto_sob_o_mouse(evento.x, evento.y)

        if objeto is None:
            return

        self._selecionar_na_lista(objeto.nome)
        self.desenhar()

        self.menu_contexto.tk_popup(evento.x_root, evento.y_root)

    def _dentro_da_viewport(self, x: float, y: float) -> bool:
        dentro_em_x = self.viewport.xmin <= x <= self.viewport.xmax
        dentro_em_y = self.viewport.ymin <= y <= self.viewport.ymax

        return dentro_em_x and dentro_em_y

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
        segmentos = objeto.segmentos_normalizados()

        if len(segmentos) == 0:
            for coordenada in objeto.coordenadas_normalizadas:
                segmentos.append((coordenada, coordenada))

        menor = float("inf")

        for inicio, fim in segmentos:
            x1, y1 = self.viewport.transformar(inicio[0], inicio[1])
            x2, y2 = self.viewport.transformar(fim[0], fim[1])

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

    #o mundo aparece girando no sentido contrario ao da window
    def _rotacionar_window(self, angulo: float) -> None:
        self.window.rotacionar(angulo)
        self.desenhar()

    def _girar_anti_horario(self, evento=None) -> None:
        self._rotacionar_window(PASSO_ROTACAO)

    def _girar_horario(self, evento=None) -> None:
        self._rotacionar_window(-PASSO_ROTACAO)

    def _rotacionar_window_pelo_campo(self, evento=None) -> None:
        try:
            angulo = float(self.entrada_angulo_window.get())
        except ValueError:
            messagebox.showerror("Erro", "Informe um ângulo numérico para rotacionar a window.")
            return

        self._rotacionar_window(angulo)

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

        # o deslocamento ta nos eixos da tela, a window converte p WC c o angulo dela
        self.window.mover_relativo(deslocamento_x, deslocamento_y)
        self._ultimo_arraste = (evento.x, evento.y)
        self.desenhar()

    def _finalizar_arraste(self, evento=None) -> None:
        self._ultimo_arraste = None

    def _ao_redimensionar_canvas(self, evento) -> None:
        if evento.width <= 1 or evento.height <= 1:
            return

        # manter msm escala ao fazer redimensionamento, pq window e viewport continuam na msm proporcao
        unidades_por_pixel = self.window.largura / self.viewport.largura

        largura_viewport = evento.width - 2 * MARGEM_VIEWPORT
        altura_viewport = evento.height - 2 * MARGEM_VIEWPORT

        if largura_viewport <= 1 or altura_viewport <= 1:
            return

        self.viewport.redimensionar(largura_viewport, altura_viewport)
        self.window.definir_tamanho(
            largura_viewport * unidades_por_pixel,
            altura_viewport * unidades_por_pixel,
        )

        self.desenhar()

    def _abrir_mundo(self) -> None:
        objetos = self._ler_obj("Abrir mundo")

        if objetos is None:
            return

        self.display_file.limpar()
        self._acrescentar_objetos(objetos)

    def _importar_obj(self) -> None:
        objetos = self._ler_obj("Importar .obj")

        if objetos is None:
            return

        self._acrescentar_objetos(objetos)

    def _ler_obj(self, titulo: str):
        caminho = filedialog.askopenfilename(
            title=titulo,
            filetypes=[("Wavefront OBJ", "*.obj"), ("Todos os arquivos", "*")],
            parent=self.raiz,
        )

        if not caminho:
            return None

        try:
            return ler_mundo(caminho)
        except Exception as erro:
            messagebox.showerror("Erro", f"Não foi possível ler o arquivo:\n{erro}")
            return None

    #nomes repetidos ganham sufixo, pq o display file n aceita dois objs c o msm nome
    def _acrescentar_objetos(self, objetos) -> None:
        for objeto in objetos:
            nome_original = objeto.nome
            sufixo = 1

            while self.display_file.buscar(objeto.nome) is not None:
                sufixo += 1
                objeto.nome = f"{nome_original}.{sufixo:03d}"

            self.display_file.adicionar(objeto)

        self._atualizar_lista_de_objetos()
        self.desenhar()

    def _salvar_mundo(self) -> None:
        caminho = filedialog.asksaveasfilename(
            title="Salvar mundo",
            defaultextension=".obj",
            filetypes=[("Wavefront OBJ", "*.obj")],
            parent=self.raiz,
        )

        if not caminho:
            return

        try:
            escrever_mundo(self.display_file, caminho)
        except Exception as erro:
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo:\n{erro}")


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
