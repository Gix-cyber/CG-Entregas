from typing import Iterator, List

from sgi.objetos import ObjetoGrafico
from sgi.objetos3d import Objeto3D


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

    def normalizar(self, window) -> None:
        for objeto in self._objetos:
            if isinstance(objeto, Objeto3D):
                objeto.coordenadas_normalizadas = self._normalizar_segmentos(objeto, window)
                continue

            normalizadas = window.projetar(objeto.coordenadas_3d())

            if normalizadas is None:
                normalizadas = []

            objeto.coordenadas_normalizadas = normalizadas

    def _normalizar_segmentos(self, objeto: Objeto3D, window) -> list:
        normalizadas = []

        for inicio, fim in objeto.segmentos_3d:
            projetado = window.projetar_segmento(inicio.como_tupla(), fim.como_tupla())

            if projetado is None:
                continue

            normalizadas.extend(projetado)

        return normalizadas

    def buscar(self, nome: str):
        for objeto in self._objetos:
            if objeto.nome == nome:
                return objeto

        return None

    def __iter__(self) -> Iterator[ObjetoGrafico]:
        return iter(self._objetos)

    def __len__(self) -> int:
        return len(self._objetos)
