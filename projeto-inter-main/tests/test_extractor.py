import unittest

from interpretador.extractor import analisar_paragrafo


EXEMPLO = (
    "Quando Helena se sentou no banco da praça, percebeu que o gerente não havia "
    "assinado o contrato. Ele afirmou que talvez assinasse amanhã."
)


class ExtractorTests(unittest.TestCase):
    def test_extrai_proposicoes_com_evidencias_validas(self) -> None:
        resultado = analisar_paragrafo(EXEMPLO)
        self.assertGreaterEqual(len(resultado.proposicoes), 3)
        for proposicao in resultado.proposicoes:
            intervalo = proposicao.evidencia.intervalo
            self.assertEqual(
                proposicao.evidencia.texto,
                resultado.paragrafo[intervalo.inicio:intervalo.fim],
            )

    def test_detecta_negacao(self) -> None:
        resultado = analisar_paragrafo(EXEMPLO)
        negadas = [prop for prop in resultado.proposicoes if prop.operadores.negacao]
        self.assertTrue(negadas)
        self.assertTrue(any(prop.predicado == "assinar" for prop in negadas))

    def test_participantes_apontam_para_mencoes(self) -> None:
        resultado = analisar_paragrafo(EXEMPLO)
        ids = {mencao.id for mencao in resultado.mencoes}
        for proposicao in resultado.proposicoes:
            for participante in proposicao.participantes:
                self.assertIn(participante.mencao_id, ids)
                self.assertEqual(
                    participante.mencao,
                    resultado.paragrafo[participante.intervalo.inicio:participante.intervalo.fim],
                )

    def test_cadeia_auxiliar_gera_uma_proposicao_lexical(self) -> None:
        resultado = analisar_paragrafo("Nenhuma falha tivesse sido encontrada.")
        predicados = [proposicao.predicado for proposicao in resultado.proposicoes]
        self.assertEqual(predicados, ["encontrar"])
        self.assertEqual(resultado.proposicoes[0].participantes[0].mencao, "Nenhuma falha")

    def test_contexto_nao_gera_proposicoes(self) -> None:
        resultado = analisar_paragrafo("Ela insistiu.", "Helena apresentou a proposta.")
        self.assertTrue(any(m.origem == "contexto_anterior" for m in resultado.mencoes))
        self.assertTrue(all(p.evidencia.texto in resultado.paragrafo for p in resultado.proposicoes))

    def test_adjetivo_nao_vira_predicado_e_sujeito_complexo_e_preservado(self) -> None:
        texto = (
            "O documento atualizado foi enviado, pois o tempo já estava se esgotando. "
            "Alguém que construiu a carreira transformando crises reagiu."
        )
        resultado = analisar_paragrafo(texto)
        formas = {item.forma_textual.casefold() for item in resultado.proposicoes}
        self.assertNotIn("atualizado", formas)
        esgotar = next(item for item in resultado.proposicoes if item.predicado == "esgotar")
        self.assertEqual(esgotar.participantes[0].mencao, "o tempo")
        construir = next(item for item in resultado.proposicoes if item.predicado == "construir")
        transformar = next(item for item in resultado.proposicoes if item.predicado == "transformar")
        self.assertEqual(construir.participantes[0].mencao.casefold(), "alguém")
        self.assertEqual(transformar.participantes[0].mencao.casefold(), "alguém")

    def test_negacao_nao_vaza_para_coordenada_afirmativa(self) -> None:
        resultado = analisar_paragrafo("João não assinou e Helena enviou o contrato.")
        assinar = next(item for item in resultado.proposicoes if item.predicado == "assinar")
        enviar = next(item for item in resultado.proposicoes if item.predicado == "enviar")
        self.assertEqual(assinar.polaridade, "negativa")
        self.assertEqual(enviar.polaridade, "positiva")
        self.assertIsNone(enviar.operadores.negacao)

    def test_modal_comum_tem_escopo_sobre_predicado_lexical(self) -> None:
        resultado = analisar_paragrafo("Ana pode abandonar o projeto.")
        self.assertEqual([item.predicado for item in resultado.proposicoes], ["abandonar"])
        operador = next(item for item in resultado.operadores_escopo if item.tipo == "modalidade")
        self.assertEqual(operador.marcador.casefold(), "pode")
        self.assertEqual(operador.escopo, ["P1"])

    def test_verbos_comuns_e_espacos_originais_sao_preservados(self) -> None:
        texto = "  Maria leu o livro. Talvez Beatriz viaje amanhã.  "
        resultado = analisar_paragrafo(texto)
        self.assertEqual(resultado.paragrafo, texto)
        self.assertEqual(
            [item.predicado for item in resultado.proposicoes],
            ["ler", "viajar"],
        )
        for proposicao in resultado.proposicoes:
            intervalo = proposicao.evidencia.intervalo
            self.assertEqual(
                proposicao.evidencia.texto,
                texto[intervalo.inicio:intervalo.fim],
            )


if __name__ == "__main__":
    unittest.main()

