import math
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from sgi.dialogo_transformacao import (
    ABA_ESCALONAMENTO,
    ABA_ROTACAO,
    ABA_TRANSLACAO,
    DialogoTransformacao,
)
from sgi.dialogo_transformacao3d import DialogoTransformacao3D
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
from sgi.objetos3d import MALHAS, Objeto3D, criar_cubo, criar_piramide, interpretar_segmentos
from sgi.transformacoes3d import comprimento
from sgi.viewport import Viewport
from sgi.window import (
    VISTA_BAIXO,
    VISTA_DIREITA,
    VISTA_ESQUERDA,
    VISTA_FRENTE,
    VISTA_TOPO,
    VISTA_TRAS,
    DISTANCIA_COP_PADRAO,
    Window,
)


LARGURA_CANVAS = 800
ALTURA_CANVAS = 600

PASSO_PANNING = 0.1
FATOR_ZOOM = 1.1

# passo em graus do Shift + NumPad 4/6 (giro) e do NumPad 2/4/6/8 (orbita), igual ao blender
PASSO_ROTACAO = 15
PASSO_ORBITA = 15

GRAUS_POR_PIXEL = 0.5

DISTANCIA_COP_MIN = 50
DISTANCIA_COP_MAX = 4000

FRACAO_TAMANHO_MALHA = 0.25

TIPO_OBJETO_3D = Objeto3D.tipo

# a viewport é menor q o canvas, c uma moldura em volta. Assim se o clipping deixar
# passar alguma coisa ela aparece fora da moldura, em vez de ser cortada pelo proprio canvas
MARGEM_VIEWPORT = 10
COR_MOLDURA = "#ff00ff"

COR_FUNDO = "white"
# eixos do mundo c as cores do blender, so q claras: x vermelho, y verde, z azul
CORES_EIXOS = ["#f0a0a0", "#a0d8a0", "#a0b8f0"]
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
        self._modo_arraste = None
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
        barra.add_cascade(label="Adicionar", menu=self._criar_menu_adicionar(barra))
        self.raiz.configure(menu=barra)

    def _criar_menu_adicionar(self, pai: tk.Misc) -> tk.Menu:
        menu = tk.Menu(pai, tearoff=False)
        menu_malha = tk.Menu(menu, tearoff=False)

        for nome in MALHAS:
            menu_malha.add_command(label=nome, command=lambda nome=nome: self._adicionar_malha(nome))

        menu.add_cascade(label="Malha", menu=menu_malha)
        menu.add_separator()
        menu.add_command(label="Pelo formulário...", command=self._focar_formulario)

        return menu

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

        opcao_3d = ttk.Radiobutton(
            quadro,
            text="Objeto 3D",
            value=TIPO_OBJETO_3D,
            variable=self.tipo_selecionado,
            command=self._atualizar_opcao_de_preenchimento,
        )
        opcao_3d.pack(anchor=tk.W)

        # so faz sentido p wireframe, ent fica desabilitado nos outros tipos
        self.preenchido_selecionado = tk.BooleanVar(value=False)
        self.opcao_preenchido = ttk.Checkbutton(
            quadro,
            text="Preenchido",
            variable=self.preenchido_selecionado,
        )
        self.opcao_preenchido.pack(anchor=tk.W, padx=(16, 0))

        ttk.Label(quadro, text="Coordenadas (x1, y1),(x2, y2),...").pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(quadro, text="Curva: 4, 7, 10, ... pontos de controle", foreground="gray").pack(anchor=tk.W)
        ttk.Label(quadro, text="B-Spline: 4 ou mais pontos de controle", foreground="gray").pack(anchor=tk.W)
        ttk.Label(quadro, text="Objeto 3D: (x, y, z) em pares, 1 par = 1 segmento", foreground="gray").pack(anchor=tk.W)
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

        self._criar_controles_de_orbita(quadro)
        self._criar_controles_de_projecao(quadro)

        self.rotulo_window = ttk.Label(quadro, justify=tk.LEFT)
        self.rotulo_window.pack(anchor=tk.W, pady=(4, 0))

    def _criar_controles_de_orbita(self, quadro: ttk.Frame) -> None:
        linha = ttk.Frame(quadro)
        linha.pack(pady=(4, 0))

        orbita = ttk.LabelFrame(linha, text="Órbita", padding=2)
        orbita.pack(side=tk.LEFT)

        botao_cima = ttk.Button(orbita, text="↑", width=3, command=self._orbitar_para_cima)
        botao_esquerda = ttk.Button(orbita, text="←", width=3, command=self._orbitar_para_esquerda)
        botao_direita = ttk.Button(orbita, text="→", width=3, command=self._orbitar_para_direita)
        botao_baixo = ttk.Button(orbita, text="↓", width=3, command=self._orbitar_para_baixo)

        botao_cima.grid(row=0, column=1)
        botao_esquerda.grid(row=1, column=0)
        botao_direita.grid(row=1, column=2)
        botao_baixo.grid(row=2, column=1)

        vistas = ttk.LabelFrame(linha, text="Vistas", padding=2)
        vistas.pack(side=tk.LEFT, padx=(8, 0), fill=tk.Y)

        botao_topo = ttk.Button(vistas, text="Topo (7)", command=self._vista_topo)
        botao_frente = ttk.Button(vistas, text="Frente (1)", command=self._vista_frente)
        botao_lado = ttk.Button(vistas, text="Direita (3)", command=self._vista_direita)

        botao_topo.pack(fill=tk.X)
        botao_frente.pack(fill=tk.X)
        botao_lado.pack(fill=tk.X)

    def _criar_controles_de_projecao(self, quadro: ttk.Frame) -> None:
        projecao = ttk.LabelFrame(quadro, text="Projeção (NumPad 5)", padding=2)
        projecao.pack(fill=tk.X, pady=(4, 0))

        self.projecao_perspectiva = tk.BooleanVar(value=self.window.perspectiva)

        opcoes = ttk.Frame(projecao)
        opcoes.pack(fill=tk.X)

        opcao_paralela = ttk.Radiobutton(
            opcoes,
            text="Paralela",
            value=False,
            variable=self.projecao_perspectiva,
            command=self._aplicar_projecao,
        )
        opcao_perspectiva = ttk.Radiobutton(
            opcoes,
            text="Perspectiva",
            value=True,
            variable=self.projecao_perspectiva,
            command=self._aplicar_projecao,
        )

        opcao_paralela.pack(side=tk.LEFT)
        opcao_perspectiva.pack(side=tk.LEFT, padx=(8, 0))

        # d pequeno = grande angular, d grande = teleobjetiva
        self.rotulo_distancia_cop = ttk.Label(projecao)
        self.rotulo_distancia_cop.pack(anchor=tk.W)

        self.escala_distancia_cop = ttk.Scale(
            projecao,
            from_=DISTANCIA_COP_MIN,
            to=DISTANCIA_COP_MAX,
            value=DISTANCIA_COP_PADRAO,
            command=self._mudar_distancia_cop,
        )
        self.escala_distancia_cop.pack(fill=tk.X)

        self._atualizar_rotulo_distancia_cop()

    def _aplicar_projecao(self) -> None:
        self.window.perspectiva = self.projecao_perspectiva.get()
        self.desenhar()

    def _alternar_projecao(self, evento=None) -> None:
        self.projecao_perspectiva.set(not self.projecao_perspectiva.get())
        self._aplicar_projecao()

    def _mudar_distancia_cop(self, valor) -> None:
        self.window.definir_distancia_cop(float(valor))
        self._atualizar_rotulo_distancia_cop()
        self.desenhar()

    def _atualizar_rotulo_distancia_cop(self) -> None:
        self.rotulo_distancia_cop.configure(text=f"Distância do COP (d): {self.window.distancia_cop:.0f}")

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

        self.canvas.bind("<Shift-ButtonPress-2>", self._iniciar_panning)
        self.canvas.bind("<ButtonPress-2>", self._iniciar_orbita)
        self.canvas.bind("<B2-Motion>", self._arrastar)
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
        self.menu_shift_a = self._criar_menu_adicionar(self.raiz)
        self.raiz.bind("<Shift-A>", self._abrir_menu_adicionar)
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

        atalhos_de_orbita = [
            (("<KP_8>", "<KP_Up>"), self._orbitar_para_cima),
            (("<KP_2>", "<KP_Down>"), self._orbitar_para_baixo),
            (("<KP_4>", "<KP_Left>"), self._orbitar_para_esquerda),
            (("<KP_6>", "<KP_Right>"), self._orbitar_para_direita),
        ]

        atalhos_de_vista = [
            (("<KP_7>", "<KP_Home>"), self._vista_topo),
            (("<Control-KP_7>", "<Control-KP_Home>"), self._vista_baixo),
            (("<KP_1>", "<KP_End>"), self._vista_frente),
            (("<Control-KP_1>", "<Control-KP_End>"), self._vista_tras),
            (("<KP_3>", "<KP_Next>"), self._vista_direita),
            (("<Control-KP_3>", "<Control-KP_Next>"), self._vista_esquerda),
        ]

        atalhos_de_vista.append((("<KP_5>", "<KP_Begin>"), self._alternar_projecao))

        for teclas, comando in atalhos_de_orbita + atalhos_de_vista:
            for tecla in teclas:
                self.canvas.bind(tecla, comando)

    def _adicionar_objetos_de_exemplo(self) -> None:
        # o losango e a reta longa ja comecam passando da borda, p mostrar o clipping
        exemplos = [
            ("wireframe", "quadrado", "(-100, -100),(100, -100),(100, 100),(-100, 100)", (0, 0, 255), False),
            ("wireframe", "triangulo", "(150, 50),(300, 50),(225, 180)", (0, 160, 0), True),
            ("wireframe", "losango", "(300, -150),(480, -50),(300, 50),(120, -50)", (255, 160, 0), True),
            ("reta", "diagonal", "(-300, -250),(-150, 200)", (200, 0, 0), False),
            ("reta", "atravessa", "(-600, 150),(600, 250)", (128, 0, 128), False),
            ("ponto", "origem", "(0, 0)", (0, 0, 0), False),
            # 2 trechos de Bezier (7 pontos), o 2o sai pela borda de baixo p mostrar o clipping
            (
                "curva",
                "onda",
                "(-350, -150),(-300, 0),(-200, 0),(-150, -150),(-100, -300),(0, -450),(50, -150)",
                (0, 128, 128),
                False,
            ),
            (
                "b-spline",
                "mola",
                "(-450, 250),(-350, 50),(-250, 250),(-150, 50),(-50, 250),(50, 50)",
                (200, 0, 120),
                False,
            ),
        ]

        for tipo, nome, texto, cor, preenchido in exemplos:
            coordenadas = interpretar_coordenadas(texto)
            objeto = criar_objeto(tipo, nome, coordenadas, cor, preenchido)
            self.display_file.adicionar(objeto)

        cubo = criar_cubo("cubo", (250.0, -220.0, 60.0), 120.0, (0, 90, 200))
        cubo.rotacionar_eixo_arbitrario(30.0, (250.0, -220.0, 60.0), (251.0, -219.0, 61.0))
        self.display_file.adicionar(cubo)

        piramide = criar_piramide("pirâmide", (-250.0, 180.0, 50.0), 100.0, (180, 90, 0))
        self.display_file.adicionar(piramide)

        self._atualizar_lista_de_objetos()

    def desenhar(self) -> None:
        self.canvas.delete("all")

        # gera a descricao em SCN de todo o mundo antes de desenhar
        self.display_file.normalizar(self.window)

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

    def _desenhar_eixos(self) -> None:
        alcance = comprimento(self.window.centro) + math.hypot(self.window.largura, self.window.altura)

        eixos = [
            ((-alcance, 0.0, 0.0), (alcance, 0.0, 0.0)),
            ((0.0, -alcance, 0.0), (0.0, alcance, 0.0)),
            ((0.0, 0.0, -alcance), (0.0, 0.0, alcance)),
        ]

        algoritmo_reta = self._algoritmo_reta()

        for (inicio, fim), cor in zip(eixos, CORES_EIXOS):
            projetado = self.window.projetar_segmento(inicio, fim)

            if projetado is None:
                continue

            (inicio_x, inicio_y), (fim_x, fim_y) = projetado

            if math.hypot(fim_x - inicio_x, fim_y - inicio_y) < 1e-9:
                continue

            # os eixos tb passam pelo clipping, senao vazariam da moldura
            recortado = algoritmo_reta((inicio_x, inicio_y), (fim_x, fim_y))

            if recortado is None:
                continue

            self._desenhar_segmento(recortado[0], recortado[1], cor)

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
        if len(objeto.coordenadas_normalizadas) == 0:
            return

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
        texto = (
            f"Window:\n"
            f"  VRP: {_formatar_vetor(self.window.centro, 1)}\n"
            f"  VPN: {_formatar_vetor(self.window.vpn, 2)}\n"
            f"  VUP: {_formatar_vetor(self.window.vup, 2)}\n"
            f"  VPN alinhado: {_formatar_vetor(self.window.vpn_alinhado(), 2)}\n"
            f"  COP: {_formatar_vetor(self.window.cop, 1)}\n"
            f"  tamanho: {self.window.largura:.1f} x {self.window.altura:.1f}"
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
            if tipo == TIPO_OBJETO_3D:
                segmentos = interpretar_segmentos(texto)
                objeto = Objeto3D(nome, segmentos, self.cor_selecionada)
            else:
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

    def _adicionar_malha(self, nome_malha: str) -> None:
        lado = FRACAO_TAMANHO_MALHA * min(self.window.largura, self.window.altura)
        criar = MALHAS[nome_malha]
        malha = criar(nome_malha.lower(), self.window.centro, lado, self.cor_selecionada)

        self._acrescentar_objetos([malha])
        self._selecionar_na_lista(malha.nome)
        self.desenhar()

    def _abrir_menu_adicionar(self, evento=None) -> None:
        if evento is not None and isinstance(evento.widget, (tk.Entry, ttk.Entry)):
            return

        x = self.raiz.winfo_pointerx()
        y = self.raiz.winfo_pointery()
        self.menu_shift_a.tk_popup(x, y)

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

        if isinstance(objeto, Objeto3D):
            DialogoTransformacao3D(self.raiz, objeto, self.desenhar, aba)
            return

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
        if len(objeto.coordenadas_normalizadas) == 0:
            return float("inf")

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

    def _orbitar_para_cima(self, evento=None) -> None:
        self.window.orbitar_vertical(PASSO_ORBITA)
        self.desenhar()

    def _orbitar_para_baixo(self, evento=None) -> None:
        self.window.orbitar_vertical(-PASSO_ORBITA)
        self.desenhar()

    def _orbitar_para_esquerda(self, evento=None) -> None:
        self.window.orbitar_horizontal(-PASSO_ORBITA)
        self.desenhar()

    def _orbitar_para_direita(self, evento=None) -> None:
        self.window.orbitar_horizontal(PASSO_ORBITA)
        self.desenhar()

    def _mudar_vista(self, vista) -> None:
        self.window.definir_vista(vista)
        self.desenhar()

    def _vista_topo(self, evento=None) -> None:
        self._mudar_vista(VISTA_TOPO)

    def _vista_baixo(self, evento=None) -> None:
        self._mudar_vista(VISTA_BAIXO)

    def _vista_frente(self, evento=None) -> None:
        self._mudar_vista(VISTA_FRENTE)

    def _vista_tras(self, evento=None) -> None:
        self._mudar_vista(VISTA_TRAS)

    def _vista_direita(self, evento=None) -> None:
        self._mudar_vista(VISTA_DIREITA)

    def _vista_esquerda(self, evento=None) -> None:
        self._mudar_vista(VISTA_ESQUERDA)

    def _ao_rolar_mouse(self, evento) -> None:
        if evento.delta > 0:
            self._aproximar()
        else:
            self._afastar()

    def _iniciar_panning(self, evento) -> None:
        self._modo_arraste = "panning"
        self._ultimo_arraste = (evento.x, evento.y)

    def _iniciar_orbita(self, evento) -> None:
        self._modo_arraste = "orbita"
        self._ultimo_arraste = (evento.x, evento.y)

    def _arrastar(self, evento) -> None:
        if self._ultimo_arraste is None:
            return

        anterior_x, anterior_y = self._ultimo_arraste
        pixels_x = evento.x - anterior_x
        pixels_y = evento.y - anterior_y

        if self._modo_arraste == "orbita":
            self._orbitar_pelo_mouse(pixels_x, pixels_y)
        else:
            self._mover_pelo_mouse(pixels_x, pixels_y)

        self._ultimo_arraste = (evento.x, evento.y)
        self.desenhar()

    def _orbitar_pelo_mouse(self, pixels_x: float, pixels_y: float) -> None:
        if pixels_x != 0:
            self.window.orbitar_horizontal(-pixels_x * GRAUS_POR_PIXEL)

        if pixels_y != 0:
            self.window.orbitar_vertical(pixels_y * GRAUS_POR_PIXEL)

    def _mover_pelo_mouse(self, pixels_x: float, pixels_y: float) -> None:
        deslocamento_x = -pixels_x * self.window.largura / self.viewport.largura
        deslocamento_y = pixels_y * self.window.altura / self.viewport.altura

        self.window.mover_relativo(deslocamento_x, deslocamento_y)

    def _finalizar_arraste(self, evento=None) -> None:
        self._ultimo_arraste = None
        self._modo_arraste = None

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


def _formatar_vetor(vetor, casas: int) -> str:
    componentes = []

    for componente in vetor:
        if abs(componente) < 0.5 * 10 ** -casas:
            componente = 0.0

        componentes.append(f"{componente:.{casas}f}")

    return "(" + ", ".join(componentes) + ")"


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
