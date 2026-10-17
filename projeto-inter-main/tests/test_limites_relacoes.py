import unittest

from interpretador.extractor import analisar_paragrafo


class LimitesRelacoesTests(unittest.TestCase):
    def test_que_em_outro_periodo_nao_vira_conteudo_de_fala(self) -> None:
        resultado = analisar_paragrafo("Ana disse. Que João assinou?")

        self.assertEqual(
            {item.predicado for item in resultado.proposicoes}, {"dizer", "assinar"},
        )
        self.assertFalse(resultado.relacoes)

    def test_conector_causal_em_outro_periodo_nao_liga_predicados(self) -> None:
        resultado = analisar_paragrafo("Ana assinou. Porque João chegou?")

        self.assertEqual(
            {item.predicado for item in resultado.proposicoes}, {"assinar", "chegar"},
        )
        self.assertFalse(resultado.relacoes)

    def test_nem_em_outro_periodo_nao_vira_coordenacao(self) -> None:
        resultado = analisar_paragrafo("Ana não assinou. Nem João enviou o documento.")

        self.assertEqual(len(resultado.proposicoes), 2)
        self.assertFalse(resultado.relacoes)

    def test_causal_dentro_do_periodo_preserva_direcao_e_evidencia(self) -> None:
        texto = "Ana enviou o documento, pois João chegou."
        resultado = analisar_paragrafo(texto)
        envio = next(item for item in resultado.proposicoes if item.predicado == "enviar")
        chegada = next(item for item in resultado.proposicoes if item.predicado == "chegar")

        self.assertEqual(len(resultado.relacoes), 1)
        relacao = resultado.relacoes[0]
        self.assertEqual(relacao.tipo, "justificativa_causal")
        self.assertEqual((relacao.origem_id, relacao.destino_id), (envio.id, chegada.id))
        self.assertEqual(relacao.marcador, "pois")
        intervalo = relacao.evidencia.intervalo
        self.assertEqual(texto[intervalo.inicio:intervalo.fim], "pois")

    def test_conteudo_dentro_do_periodo_preserva_vinculo(self) -> None:
        resultado = analisar_paragrafo("Ana disse que João assinou.")
        dizer = next(item for item in resultado.proposicoes if item.predicado == "dizer")
        assinar = next(item for item in resultado.proposicoes if item.predicado == "assinar")

        self.assertEqual(
            [(item.tipo, item.origem_id, item.destino_id) for item in resultado.relacoes],
            [("conteudo_atitudinal", dizer.id, assinar.id)],
        )


if __name__ == "__main__":
    unittest.main()
