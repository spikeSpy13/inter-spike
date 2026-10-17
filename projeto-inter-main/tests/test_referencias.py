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
        self.assertEqual(resolucao.motivo_pendencia, "exoforia")

    def test_primeira_pessoa_narrativa_forma_participante_discursivo(self) -> None:
        resultado = analisar_paragrafo("Eu revisei meu relatório e mantive minha decisão.")
        primeiras = [
            item for item in resultado.mencoes
            if item.texto.casefold() in {"eu", "meu", "minha"}
        ]
        resolucoes = [
            next(item for item in resultado.resolucoes if item.mencao_id == mencao.id)
            for mencao in primeiras
        ]
        self.assertEqual(len({item.referente_id for item in resolucoes}), 1)
        referente = next(item for item in resultado.referentes if item.id == resolucoes[0].referente_id)
        self.assertEqual((referente.rotulo, referente.tipo), ("narrador", "participante_discursivo"))
        self.assertTrue(all(item.estado == "resolvida" for item in resolucoes))
        self.assertTrue(all("identidade externa" in item.razoes[1] for item in resolucoes))

        plural = analisar_paragrafo("Nós revisamos nossos relatórios.")
        nos = next(item for item in plural.mencoes if item.texto == "Nós")
        self.assertEqual(nos.caracteristicas.numero, "plural")
        resolucao_nos = next(item for item in plural.resolucoes if item.mencao_id == nos.id)
        referente_nos = next(item for item in plural.referentes if item.id == resolucao_nos.referente_id)
        self.assertEqual(referente_nos.tipo, "participante_discursivo")

    def test_terceira_pessoa_com_dois_antecedentes_permanece_ambigua(self) -> None:
        resultado = analisar_paragrafo("Ana encontrou Maria. Ela respondeu.")
        ela = next(item for item in resultado.mencoes if item.texto == "Ela")
        resolucao = next(item for item in resultado.resolucoes if item.mencao_id == ela.id)
        self.assertEqual(resolucao.estado, "ambigua")
        self.assertEqual(resolucao.motivo_pendencia, "ambiguidade")
        self.assertGreaterEqual(len(resolucao.alternativas), 2)

    def test_pronome_sem_antecedente_informa_causa(self) -> None:
        resultado = analisar_paragrafo("Ela chegou cedo.")
        ela = next(item for item in resultado.mencoes if item.texto == "Ela")
        resolucao = next(item for item in resultado.resolucoes if item.mencao_id == ela.id)
        self.assertEqual(resolucao.estado, "nao_resolvida")
        self.assertEqual(resolucao.motivo_pendencia, "ausencia_antecedente")
        self.assertTrue(any("antecedente textual" in item for item in resolucao.razoes))

    def test_pronome_com_antecedentes_incompativeis_informa_causa(self) -> None:
        resultado = analisar_paragrafo("O contrato chegou. Ela respondeu.")
        ela = next(item for item in resultado.mencoes if item.texto == "Ela")
        resolucao = next(item for item in resultado.resolucoes if item.mencao_id == ela.id)
        self.assertEqual(resolucao.estado, "nao_resolvida")
        self.assertEqual(resolucao.motivo_pendencia, "candidatos_incompativeis")
        self.assertTrue(any("classes semânticas incompatíveis" in item for item in resolucao.razoes))

    def test_participantes_recebem_referente_quando_seguro(self) -> None:
        construir = next(item for item in self.resultado.proposicoes if item.predicado == "construir")
        self.assertIsNotNone(construir.participantes[0].referente_id)
        self.assertEqual(
            construir.participantes[0].referente_id,
            self._referente_com("Helena").id,
        )


if __name__ == "__main__":
    unittest.main()
