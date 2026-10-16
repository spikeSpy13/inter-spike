import unittest

from interpretador.centralidade import validar_ideia_central
from interpretador.extractor import analisar_paragrafo


PARAGRAFO = (
    "Apesar daquele revés temporário, a profissional não abandonou o campo de batalha "
    "nem desistiu de buscar novos recursos para o projeto solar. No fim da tarde, o "
    "documento atualizado foi enviado por ela ao diretor financeiro através de um "
    "mensageiro expresso, pois o tempo já estava se esgotando. Você realmente acredita "
    "que uma simples burocracia bancária seria capaz de frear alguém que construiu toda "
    "a carreira transformando crises em combustível?"
)


class CentralIdeaTests(unittest.TestCase):
    def test_propoe_trecho_central_com_evidencia_e_ids_essenciais(self) -> None:
        resultado = analisar_paragrafo(PARAGRAFO)
        ideia = resultado.ideia_central

        self.assertEqual(resultado.schema_version, "0.8.0")
        self.assertEqual(ideia.estado, "proposta")
        self.assertEqual(ideia.proposicao_ids, ["P1", "P2"])
        self.assertEqual(resultado.conteudo_essencial_ids, ["P1", "P2"])
        self.assertIn("não abandonou", ideia.texto)
        self.assertIn("nem desistiu", ideia.texto)
        self.assertGreaterEqual(len(ideia.alternativas), 1)
        self.assertGreater(ideia.confianca, 0)

        evidencia = ideia.evidencias[0]
        self.assertEqual(
            evidencia.texto,
            PARAGRAFO[evidencia.intervalo.inicio : evidencia.intervalo.fim],
        )

    def test_uma_proposicao_e_selecionada_sem_alternativa(self) -> None:
        resultado = analisar_paragrafo("Ana leu o livro.")

        self.assertEqual(resultado.conteudo_essencial_ids, ["P1"])
        self.assertEqual(resultado.ideia_central.texto, "Ana leu o livro.")
        self.assertEqual(resultado.ideia_central.alternativas, [])

    def test_sem_proposicoes_mantem_ideia_indeterminada(self) -> None:
        resultado = analisar_paragrafo("Um livro azul.")

        self.assertEqual(resultado.ideia_central.estado, "indeterminada")
        self.assertIsNone(resultado.ideia_central.texto)
        self.assertEqual(resultado.conteudo_essencial_ids, [])
        self.assertTrue(any("ideia central" in alerta.casefold() for alerta in resultado.alertas))

    def test_alternativas_permanecem_rastreaveis_ao_original(self) -> None:
        resultado = analisar_paragrafo("Ana leu o livro. Beatriz viaja amanhã.")
        ids = {item.id for item in resultado.proposicoes}

        for alternativa in resultado.ideia_central.alternativas:
            self.assertLessEqual(set(alternativa.proposicao_ids), ids)
            for evidencia in alternativa.evidencias:
                intervalo = evidencia.intervalo
                self.assertEqual(evidencia.texto, resultado.paragrafo[intervalo.inicio : intervalo.fim])

    def test_validador_rejeita_id_essencial_inexistente(self) -> None:
        resultado = analisar_paragrafo("Ana leu o livro.")
        with self.assertRaisesRegex(ValueError, "inexistente"):
            validar_ideia_central(
                resultado.paragrafo,
                resultado.proposicoes,
                resultado.ideia_central,
                ["P999"],
            )


if __name__ == "__main__":
    unittest.main()
