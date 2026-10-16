import unittest

from interpretador.extractor import analisar_paragrafo
from interpretador.fidelidade import checar_fidelidade


TEXTO = "Ana não abandonou o projeto nem desistiu do trabalho."


class FidelityCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resultado = analisar_paragrafo(TEXTO)

    def _checar(self, sintese=None, parafrases=None):
        return checar_fidelidade(
            self.resultado.paragrafo,
            self.resultado.proposicoes,
            self.resultado.conteudo_essencial_ids,
            self.resultado.operadores_escopo,
            self.resultado.relacoes,
            sintese or self.resultado.sintese,
            self.resultado.parafrases if parafrases is None else parafrases,
        )

    def test_saidas_geradas_ficam_sem_alertas_detectados(self) -> None:
        checagem = self.resultado.checagem

        self.assertEqual(self.resultado.schema_version, "0.9.0")
        self.assertEqual(checagem.estado, "sem_alertas_detectados")
        self.assertEqual(checagem.alvos_verificados, ["sintese", "PF1"])
        self.assertEqual(checagem.achados, [])
        self.assertTrue(any("não certifica" in item for item in checagem.limitacoes))

    def test_afirmacao_acrescentada_na_sintese_gera_alerta(self) -> None:
        adulterada = self.resultado.sintese.model_copy(
            update={"texto": self.resultado.sintese.texto + " O projeto foi aprovado."}
        )

        checagem = self._checar(sintese=adulterada, parafrases=[])

        self.assertEqual(checagem.estado, "revisao_necessaria")
        achado = next(item for item in checagem.achados if item.codigo == "afirmacao_sem_apoio")
        self.assertEqual(achado.alvo_id, "sintese")

    def test_relacao_essencial_removida_gera_alerta_com_id(self) -> None:
        adulterada = self.resultado.sintese.model_copy(deep=True)
        adulterada.cobertura.relacao_ids = []

        checagem = self._checar(sintese=adulterada, parafrases=[])

        achado = next(
            item
            for item in checagem.achados
            if item.codigo == "relacao_essencial_ausente"
        )
        self.assertEqual(achado.alvo_id, "sintese")
        self.assertEqual(achado.ids_afetados, ["L1"])

    def test_afirmacao_acrescentada_na_parafrase_gera_alerta(self) -> None:
        adulterada = self.resultado.parafrases[0].model_copy(
            update={
                "texto": self.resultado.parafrases[0].texto + " O projeto foi aprovado."
            }
        )

        checagem = self._checar(parafrases=[adulterada])

        achado = next(item for item in checagem.achados if item.codigo == "afirmacao_sem_apoio")
        self.assertEqual(achado.alvo_id, "PF1")

    def test_transformacao_nao_autorizada_gera_alerta(self) -> None:
        adulterada = self.resultado.parafrases[0].model_copy(deep=True)
        adulterada.transformacoes[0].substituicao = "ou"
        adulterada.texto = "Ana não abandonou o projeto ou desistiu do trabalho."

        checagem = self._checar(parafrases=[adulterada])

        achado = next(
            item
            for item in checagem.achados
            if item.codigo == "transformacao_nao_autorizada"
        )
        self.assertEqual(achado.alvo_id, "PF1")

    def test_sem_conteudo_essencial_fica_indeterminada(self) -> None:
        resultado = analisar_paragrafo("Um livro azul.")

        self.assertEqual(resultado.checagem.estado, "indeterminada")
        self.assertEqual(resultado.checagem.achados, [])


if __name__ == "__main__":
    unittest.main()
