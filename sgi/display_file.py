from typing import Iterator, List

from sgi.objetos import ObjetoGrafico
from sgi.transformacoes3d import Matriz4, transformar_ponto


class DisplayFile:

    def __init__(self):
        self._objetos: List[ObjetoGrafico] = []

    def adicionar(self, objeto: ObjetoGrafico) -> None:
        if self.buscar(objeto.nome) is not None:
            raise ValueError(f"Obj ja existe c o msm nome: '{objeto.nome}'.")

        self._objetos.append(objeto)

    def remover(self, nome: str) -> None:
        objeto = self.buscar(nome)

        if objeto is None:
            raise ValueError(f"Obj '{nome}' n encontrado")

        self._objetos.remove(objeto)

    def limpar(self) -> None:
        self._objetos = []

    def normalizar(self, matriz: Matriz4) -> None:
        for objeto in self._objetos:
            normalizadas = []

            for coordenada in objeto.coordenadas_3d():
                x, y, _ = transformar_ponto(coordenada, matriz)
                normalizadas.append((x, y))

            objeto.coordenadas_normalizadas = normalizadas

    def buscar(self, nome: str):
        for objeto in self._objetos:
            if objeto.nome == nome:
                return objeto

        return None

    def __iter__(self) -> Iterator[ObjetoGrafico]:
        return iter(self._objetos)

    def __len__(self) -> int:
        return len(self._objetos)
