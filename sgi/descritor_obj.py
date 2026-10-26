import os
from typing import Dict, List

from sgi.display_file import DisplayFile
from sgi.objetos import (
    COR_PADRAO,
    Coordenada,
    CorRGB,
    ObjetoGrafico,
    Ponto,
    Reta,
    Wireframe,
)


#transcreve um obj grafico p o formato .obj: nome (o), cor (usemtl), vertices (v) e
#arestas (p p/ ponto, l p/ reta e wireframe). Os indices de vertice do .obj sao
#globais e comecam em 1, ent o descritor precisa saber quantos vertices ja foram escritos
class DescritorOBJ:

    def descrever(self, objeto: ObjetoGrafico, primeiro_indice: int) -> List[str]:
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
        else:
            # wireframe é fechado, ent a polilinha volta pro primeiro vertice
            indices.append(indices[0])
            linhas.append("l " + " ".join(indices))

        return linhas


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
        linhas.extend(descritor.descrever(objeto, proximo_indice))
        proximo_indice += len(objeto.coordenadas)

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


#le um .obj e devolve os objs graficos. So x e y dos vertices sao usados (mundo 2D).
#p vira ponto, l c 2 vertices vira reta, l fechado ou f vira wireframe e
#l aberto c + de 2 vertices vira uma reta por segmento
def ler_mundo(caminho: str) -> List[ObjetoGrafico]:
    leitor = _LeitorOBJ(os.path.dirname(caminho))

    with open(caminho, "r", encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo, start=1):
            try:
                leitor.interpretar_linha(linha)
            except (ValueError, IndexError) as erro:
                raise ValueError(f"Linha {numero} inválida: {linha.strip()!r} ({erro})")

    return leitor.objetos


class _LeitorOBJ:

    def __init__(self, diretorio: str):
        self.diretorio = diretorio
        self.vertices: List[Coordenada] = []
        self.materiais: Dict[str, CorRGB] = {}
        self.objetos: List[ObjetoGrafico] = []

        self.nome_atual = "objeto"
        self.cor_atual = COR_PADRAO

        # qnts elementos ja sairam do obj atual, p dar nome unico qnd um "o" tem varios
        self.elementos_no_atual = 0

    def interpretar_linha(self, linha: str) -> None:
        partes = linha.split("#")[0].split()

        if len(partes) == 0:
            return

        comando = partes[0]
        argumentos = partes[1:]

        if comando == "v":
            x = float(argumentos[0])
            y = float(argumentos[1])
            self.vertices.append((x, y))
        elif comando == "o" or comando == "g":
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
        elif comando == "l":
            self._interpretar_polilinha(argumentos)
        elif comando == "f":
            coordenadas = self._vertices(argumentos)
            self._adicionar(Wireframe, coordenadas)

        # o resto (vt, vn, s, w...) n tem uso num mundo 2D de pontos e linhas

    def _interpretar_polilinha(self, argumentos: List[str]) -> None:
        coordenadas = self._vertices(argumentos)
        fechada = len(argumentos) > 3 and argumentos[0] == argumentos[-1]

        if fechada:
            self._adicionar(Wireframe, coordenadas[:-1])
            return

        if len(coordenadas) == 2:
            self._adicionar(Reta, coordenadas)
            return

        for indice in range(len(coordenadas) - 1):
            segmento = [coordenadas[indice], coordenadas[indice + 1]]
            self._adicionar(Reta, segmento)

    def _adicionar(self, classe, coordenadas: List[Coordenada]) -> None:
        self.elementos_no_atual += 1

        if self.elementos_no_atual == 1:
            nome = self.nome_atual
        else:
            nome = f"{self.nome_atual}_{self.elementos_no_atual}"

        self.objetos.append(classe(nome, coordenadas, self.cor_atual))

    def _vertices(self, argumentos: List[str]) -> List[Coordenada]:
        coordenadas = []

        for argumento in argumentos:
            coordenadas.append(self._vertice(argumento))

        return coordenadas

    #indice pode vir como "3", "3/1/2" ou negativo (relativo ao fim da lista)
    def _vertice(self, argumento: str) -> Coordenada:
        indice = int(argumento.split("/")[0])

        if indice < 0:
            return self.vertices[indice]

        if indice == 0:
            raise ValueError("índice de vértice 0 não existe no .obj")

        return self.vertices[indice - 1]

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
