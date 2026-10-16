import unittest

from interpretador.extractor import analisar_paragrafo


CONTEXTO = (
    "Helena conversou com o gerente do banco. Ele examinou a proposta dela. "
    "A engenheira respondeu enquanto a bateria do seu celular acabava."
)
PARAGRAFO = (
    "A profissional enviou o documento por ela ao diretor financeiro através de um "
    "mensageiro expresso. Você acredita que alguém que construiu toda a carreira reagiria?"
)


class ReferenceResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resultado = analisar_paragrafo(PARAGRAFO, CONTEXTO)
        self.mencoes = {item.id: item for item in self.resultado.mencoes}

    def _referente_com(self, texto: str):
        mencao_id = next(
            item.id for item in self.resultado.mencoes if item.texto.casefold() == texto.casefold()
        )
        return next(item for item in self.resultado.referentes if mencao_id in item.mencoes)

    def test_forma_grupo_de_helena_com_posse_e_descricoes(self) -> None:
        referente = self._referente_com("Helena")
        superficies = {self.mencoes[item].texto.casefold() for item in referente.mencoes}
        self.assertTrue({"helena", "dela", "a engenheira", "a profissional", "ela"} <= superficies)
        self.assertTrue(any(texto.startswith("alguém que") for texto in superficies))

    def test_gerente_e_ele_formam_grupo_separado(self) -> None:
        referente = self._referente_com("o gerente do banco")
        superficies = {self.mencoes[item].texto.casefold() for item in referente.mencoes}
        self.assertEqual(superficies, {"o gerente do banco", "ele"})

    def test_possessivo_registra_relacao_de_possuidor(self) -> None:
        dela = next(item for item in self.resultado.mencoes if item.texto.casefold() == "dela")
        resolucao = next(item for item in self.resultado.resolucoes if item.mencao_id == dela.id)
        self.assertEqual(resolucao.estado, "resolvida")
        self.assertEqual(resolucao.tipo_relacao, "possuidor")
        self.assertTrue(resolucao.razoes)
        self.assertEqual(len(resolucao.evidencias), 2)

    def test_segunda_pessoa_permanece_nao_resolvida(self) -> None:
        voce = next(item for item in self.resultado.mencoes if item.texto.casefold() == "você")
        resolucao = next(item for item in self.resultado.resolucoes if item.mencao_id == voce.id)
        self.assertEqual(resolucao.estado, "nao_resolvida")
        self.assertIsNone(resolucao.referente_id)

    def test_participantes_recebem_referente_quando_seguro(self) -> None:
        construir = next(item for item in self.resultado.proposicoes if item.predicado == "construir")
        self.assertIsNotNone(construir.participantes[0].referente_id)
        self.assertEqual(
            construir.participantes[0].referente_id,
            self._referente_com("Helena").id,
        )


if __name__ == "__main__":
    unittest.main()
