import unittest

from interpretador.extractor import analisar_paragrafo
from interpretador.geracao import validar_sintese


PARAGRAFO = (
    "Apesar daquele revés temporário, a profissional não abandonou o campo de batalha "
    "nem desistiu de buscar novos recursos para o projeto solar. No fim da tarde, o "
    "documento atualizado foi enviado por ela ao diretor financeiro através de um "
    "mensageiro expresso, pois o tempo já estava se esgotando. Você realmente acredita "
    "que uma simples burocracia bancária seria capaz de frear alguém que construiu toda "
    "a carreira transformando crises em combustível?"
)


class SynthesisTests(unittest.TestCase):
    def test_sintese_preserva_periodo_com_conteudo_essencial(self) -> None:
        resultado = analisar_paragrafo(PARAGRAFO)
        sintese = resultado.sintese

        self.assertEqual(resultado.schema_version, "0.7.0")
        self.assertEqual(sintese.estado, "gerada")
        self.assertEqual(
            sintese.texto,
            "Apesar daquele revés temporário, a profissional não abandonou o campo de batalha "
            "nem desistiu de buscar novos recursos para o projeto solar.",
        )
        self.assertEqual(sintese.cobertura.proposicao_ids, ["P1", "P2"])
        self.assertEqual(sintese.cobertura.operador_ids, ["O1", "O2"])
        self.assertEqual(sintese.cobertura.relacao_ids, ["L1", "L7"])
        self.assertTrue(sintese.cobertura.mencao_ids)
        self.assertEqual(resultado.parafrases, [])

    def test_evidencias_da_sintese_reproduzem_o_original(self) -> None:
        resultado = analisar_paragrafo(PARAGRAFO)
        for evidencia in resultado.sintese.evidencias:
            intervalo = evidencia.intervalo
            self.assertEqual(
                evidencia.texto,
                PARAGRAFO[intervalo.inicio : intervalo.fim],
            )

    def test_modalidade_essencial_e_declarada_e_preservada(self) -> None:
        resultado = analisar_paragrafo("Ana pode abandonar o projeto.")

        self.assertEqual(resultado.sintese.texto, "Ana pode abandonar o projeto.")
        self.assertEqual(resultado.sintese.cobertura.proposicao_ids, ["P1"])
        self.assertEqual(resultado.sintese.cobertura.operador_ids, ["O1"])
        self.assertIn("pode", resultado.sintese.texto)

    def test_sem_conteudo_essencial_mantem_sintese_indeterminada(self) -> None:
        resultado = analisar_paragrafo("Um livro azul.")

        self.assertEqual(resultado.sintese.estado, "indeterminada")
        self.assertIsNone(resultado.sintese.texto)
        self.assertEqual(resultado.sintese.evidencias, [])
        self.assertEqual(resultado.sintese.cobertura.proposicao_ids, [])

    def test_validador_rejeita_texto_sem_apoio(self) -> None:
        resultado = analisar_paragrafo("Ana leu o livro.")
        adulterada = resultado.sintese.model_copy(update={"texto": "Ana queimou o livro."})

        with self.assertRaisesRegex(ValueError, "sem apoio"):
            validar_sintese(
                resultado.paragrafo,
                resultado.proposicoes,
                resultado.conteudo_essencial_ids,
                resultado.operadores_escopo,
                resultado.relacoes,
                adulterada,
            )


if __name__ == "__main__":
    unittest.main()
