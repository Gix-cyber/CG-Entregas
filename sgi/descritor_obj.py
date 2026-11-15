import os
from typing import Dict, List, Set, Tuple

from sgi.display_file import DisplayFile
from sgi.objetos import (
    COR_PADRAO,
    BSpline,
    Coordenada,
    CorRGB,
    Curva2D,
    ObjetoGrafico,
    Ponto,
    Reta,
    Wireframe,
)
from sgi.objetos3d import Objeto3D
from sgi.transformacoes3d import Coordenada3D

# abaixo disso o z do vertice conta como 0, p decidir se um obj do .obj é 2D ou 3D
TOLERANCIA_Z = 1e-9


#transcreve um obj grafico p o formato .obj: nome (o), cor (usemtl), vertices (v) e
#arestas (p p/ ponto, l p/ reta e wireframe de arame, f p/ wireframe preenchido). Os indices de vertice do .obj sao
#globais e comecam em 1, ent o descritor precisa saber quantos vertices ja foram escritos.
#Devolve as linhas e qnts vertices foram escritos
class DescritorOBJ:

    def descrever(self, objeto: ObjetoGrafico, primeiro_indice: int) -> Tuple[List[str], int]:
        if isinstance(objeto, Objeto3D):
            return _descrever_objeto_3d(objeto, primeiro_indice)

        linhas = [f"o {objeto.nome}"]
        linhas.append(f"usemtl {nome_do_material(objeto.cor)}")

        indices = []

        for indice, (x, y) in enumerate(objeto.coordenadas):
            linhas.append(f"v {float(x)} {float(y)} 0.0")
            indices.append(str(primeiro_indice + indice))

        if objeto.tipo == Ponto.tipo:
            linhas.append("p " + " ".join(indices))
        elif objeto.tipo == Reta.tipo:
            linhas.append("l " + " ".join(indices))
        elif objeto.tipo == Curva2D.tipo:
            linhas.append("cstype bezier")
            linhas.append("deg 3")
            linhas.append("curv 0.0 1.0 " + " ".join(indices))
            linhas.append("end")
        elif objeto.tipo == BSpline.tipo:
            linhas.extend(_descrever_bspline(indices))
        elif objeto.preenchido:
            # face do .obj ja é fechada por definicao
            linhas.append("f " + " ".join(indices))
        else:
            # wireframe é fechado, ent a polilinha volta pro primeiro vertice
            indices.append(indices[0])
            linhas.append("l " + " ".join(indices))

        return linhas, len(objeto.coordenadas)


def _descrever_objeto_3d(objeto: Objeto3D, primeiro_indice: int) -> Tuple[List[str], int]:
    linhas = [f"o {objeto.nome}"]
    linhas.append(f"usemtl {nome_do_material(objeto.cor)}")

    vertices = objeto.vertices()
    indice_do_vertice = {}

    for posicao, (x, y, z) in enumerate(vertices):
        linhas.append(f"v {x} {y} {z}")
        indice_do_vertice[(x, y, z)] = primeiro_indice + posicao

    for inicio, fim in objeto.segmentos_3d:
        indice_inicio = indice_do_vertice[inicio.como_tupla()]
        indice_fim = indice_do_vertice[fim.como_tupla()]
        linhas.append(f"l {indice_inicio} {indice_fim}")

    return linhas, len(vertices)


#B-Spline cubica uniforme: n pontos de controle pedem n + 4 nós igualmente espacados,
#e a curva vale no intervalo [nó 3, nó n] (onde os 4 pontos de cada trecho tem efeito)
def _descrever_bspline(indices: List[str]) -> List[str]:
    quantidade = len(indices)
    nos = []

    for no in range(quantidade + 4):
        nos.append(f"{float(no)}")

    inicio = float(3)
    fim = float(quantidade)

    return [
        "cstype bspline",
        "deg 3",
        f"curv {inicio} {fim} " + " ".join(indices),
        "parm u " + " ".join(nos),
        "end",
    ]


def nome_do_material(cor: CorRGB) -> str:
    r, g, b = cor

    return f"cor_{r}_{g}_{b}"


#o cabecalho é so o comentario e o mtllib, o resto sai do percurso do display file c o descritor
def escrever_mundo(display_file: DisplayFile, caminho: str) -> None:
    caminho_mtl = os.path.splitext(caminho)[0] + ".mtl"
    descritor = DescritorOBJ()

    linhas = [
        "# Mundo exportado pelo SGI",
        f"mtllib {os.path.basename(caminho_mtl)}",
    ]

    proximo_indice = 1
    cores = []

    for objeto in display_file:
        linhas_do_objeto, quantidade_de_vertices = descritor.descrever(objeto, proximo_indice)
        linhas.extend(linhas_do_objeto)
        proximo_indice += quantidade_de_vertices

        if objeto.cor not in cores:
            cores.append(objeto.cor)

    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")

    _escrever_materiais(cores, caminho_mtl)


#no .mtl a cor difusa (Kd) vai de 0 a 1
def _escrever_materiais(cores: List[CorRGB], caminho_mtl: str) -> None:
    linhas = ["# Cores do mundo exportado pelo SGI"]

    for cor in cores:
        r, g, b = cor

        linhas.append(f"newmtl {nome_do_material(cor)}")
        linhas.append(f"Kd {r / 255:.6f} {g / 255:.6f} {b / 255:.6f}")

    with open(caminho_mtl, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")


#le um .obj e devolve os objs graficos. Se algum vertice das arestas (l e f) de um obj ("o"/"g")
#tem z != 0, todas essas arestas viram um unico objeto 3D (modelo de arame). Senao o obj é 2D
#e so x e y sao usados:
#p vira ponto, l c 2 vertices vira reta, l fechado vira wireframe de arame,
#f vira wireframe preenchido, curv vira curva de bezier ou B-Spline (conforme o cstype) e l aberto c + de 2 vertices vira uma reta por segmento
def ler_mundo(caminho: str) -> List[ObjetoGrafico]:
    leitor = _LeitorOBJ(os.path.dirname(caminho))

    with open(caminho, "r", encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo, start=1):
            try:
                leitor.interpretar_linha(linha)
            except (ValueError, IndexError) as erro:
                raise ValueError(f"Linha {numero} inválida: {linha.strip()!r} ({erro})")

    leitor.finalizar_grupo()

    return leitor.objetos


class _LeitorOBJ:

    def __init__(self, diretorio: str):
        self.diretorio = diretorio
        self.vertices: List[Coordenada3D] = []
        self.materiais: Dict[str, CorRGB] = {}
        self.objetos: List[ObjetoGrafico] = []

        self.nome_atual = "objeto"
        self.cor_atual = COR_PADRAO

        self.tipo_de_curva_atual = "bezier"

        # qnts elementos ja sairam do obj atual, p dar nome unico qnd um "o" tem varios
        self.elementos_no_atual = 0

        self.arestas_pendentes: List[Tuple[str, List[int], CorRGB]] = []

    def interpretar_linha(self, linha: str) -> None:
        partes = linha.split("#")[0].split()

        if len(partes) == 0:
            return

        comando = partes[0]
        argumentos = partes[1:]

        if comando == "v":
            x = float(argumentos[0])
            y = float(argumentos[1])
            z = 0.0

            if len(argumentos) > 2:
                z = float(argumentos[2])

            self.vertices.append((x, y, z))
        elif comando == "o" or comando == "g":
            self.finalizar_grupo()
            self.nome_atual = " ".join(argumentos)
            self.elementos_no_atual = 0
        elif comando == "mtllib":
            for nome_arquivo in argumentos:
                self._ler_materiais(os.path.join(self.diretorio, nome_arquivo))
        elif comando == "usemtl":
            self.cor_atual = self.materiais.get(argumentos[0], COR_PADRAO)
        elif comando == "p":
            for argumento in argumentos:
                self._adicionar(Ponto, [self._vertice(argumento)])
        elif comando == "l" or comando == "f":
            indices = self._indices(argumentos)
            self.arestas_pendentes.append((comando, indices, self.cor_atual))
        elif comando == "cstype":
            # "cstype rat bspline" tbm é valido, ent o tipo é o ultimo argumento
            self.tipo_de_curva_atual = argumentos[-1]
        elif comando == "curv":
            # os 2 primeiros argumentos sao o intervalo do parametro, o resto sao os vertices.
            # So curvas cubicas sao suportadas e a B-Spline é sempre uniforme,
            # ent deg e parm sao ignorados
            coordenadas = self._vertices(argumentos[2:])

            if self.tipo_de_curva_atual == "bspline":
                self._adicionar(BSpline, coordenadas)
            else:
                self._adicionar(Curva2D, coordenadas)

        # o resto (vt, vn, s, w, deg, parm, end...) n tem uso num mundo de pontos e linhas

    def finalizar_grupo(self) -> None:
        pendentes = self.arestas_pendentes
        self.arestas_pendentes = []

        if len(pendentes) == 0:
            return

        if self._grupo_eh_3d(pendentes):
            self._adicionar_objeto_3d(pendentes)
            return

        for comando, indices, cor in pendentes:
            if comando == "f":
                self._adicionar(Wireframe, self._coordenadas_2d(indices), preenchido=True, cor=cor)
            else:
                self._interpretar_polilinha(indices, cor)

    def _grupo_eh_3d(self, pendentes) -> bool:
        for _, indices, _ in pendentes:
            for indice in indices:
                z = self.vertices[indice][2]

                if abs(z) > TOLERANCIA_Z:
                    return True

        return False

    def _adicionar_objeto_3d(self, pendentes) -> None:
        arestas_vistas: Set[Tuple[int, int]] = set()
        segmentos = []

        for comando, indices, _ in pendentes:
            pares = []

            for posicao in range(len(indices) - 1):
                pares.append((indices[posicao], indices[posicao + 1]))

            if comando == "f" and len(indices) > 2:
                pares.append((indices[-1], indices[0]))

            for inicio, fim in pares:
                chave = (min(inicio, fim), max(inicio, fim))

                if inicio == fim or chave in arestas_vistas:
                    continue

                arestas_vistas.add(chave)
                segmentos.append((self.vertices[inicio], self.vertices[fim]))

        if len(segmentos) == 0:
            return

        cor = pendentes[0][2]
        self._adicionar(Objeto3D, segmentos, cor=cor)

    def _interpretar_polilinha(self, indices: List[int], cor: CorRGB) -> None:
        coordenadas = self._coordenadas_2d(indices)
        fechada = len(indices) > 3 and indices[0] == indices[-1]

        if fechada:
            self._adicionar(Wireframe, coordenadas[:-1], cor=cor)
            return

        if len(coordenadas) == 2:
            self._adicionar(Reta, coordenadas, cor=cor)
            return

        for indice in range(len(coordenadas) - 1):
            segmento = [coordenadas[indice], coordenadas[indice + 1]]
            self._adicionar(Reta, segmento, cor=cor)

    def _adicionar(self, classe, coordenadas, preenchido: bool = False, cor: CorRGB = None) -> None:
        self.elementos_no_atual += 1

        if cor is None:
            cor = self.cor_atual

        if self.elementos_no_atual == 1:
            nome = self.nome_atual
        else:
            nome = f"{self.nome_atual}_{self.elementos_no_atual}"

        if classe is Wireframe:
            objeto = Wireframe(nome, coordenadas, cor, preenchido)
        else:
            objeto = classe(nome, coordenadas, cor)

        self.objetos.append(objeto)

    def _indices(self, argumentos: List[str]) -> List[int]:
        indices = []

        for argumento in argumentos:
            indices.append(self._indice(argumento))

        return indices

    def _coordenadas_2d(self, indices: List[int]) -> List[Coordenada]:
        coordenadas = []

        for indice in indices:
            x, y, _ = self.vertices[indice]
            coordenadas.append((x, y))

        return coordenadas

    def _vertices(self, argumentos: List[str]) -> List[Coordenada]:
        return self._coordenadas_2d(self._indices(argumentos))

    def _vertice(self, argumento: str) -> Coordenada:
        x, y, _ = self.vertices[self._indice(argumento)]

        return x, y

    def _indice(self, argumento: str) -> int:
        indice = int(argumento.split("/")[0])

        if indice == 0:
            raise ValueError("índice de vértice 0 não existe no .obj")

        if indice < 0:
            posicao = len(self.vertices) + indice
        else:
            posicao = indice - 1

        if posicao < 0 or posicao >= len(self.vertices):
            raise IndexError(f"vértice {indice} não existe")

        return posicao

    #se o .mtl n existir o mundo é lido mesmo assim, c a cor padrao
    def _ler_materiais(self, caminho_mtl: str) -> None:
        if not os.path.exists(caminho_mtl):
            return

        material_atual = None

        with open(caminho_mtl, "r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                partes = linha.split("#")[0].split()

                if len(partes) == 0:
                    continue

                if partes[0] == "newmtl":
                    material_atual = " ".join(partes[1:])
                    self.materiais[material_atual] = COR_PADRAO
                elif partes[0] == "Kd" and material_atual is not None:
                    r = _componente_de_cor(partes[1])
                    g = _componente_de_cor(partes[2])
                    b = _componente_de_cor(partes[3])
                    self.materiais[material_atual] = (r, g, b)


#Kd vem de 0 a 1, o SGI guarda de 0 a 255
def _componente_de_cor(texto: str) -> int:
    valor = round(float(texto) * 255)

    return max(0, min(255, valor))
