import unittest

from interpretador.extractor import analisar_paragrafo


class ExecutionMetadataTests(unittest.TestCase):
    def test_registra_motor_parametros_duracao_e_custos_locais(self) -> None:
        resultado = analisar_paragrafo(
            "Helena não desistiu, pois precisava concluir o projeto.",
            "Helena apresentou o plano ao conselho.",
        )

        self.assertEqual(resultado.schema_version, "1.0.0")
        self.assertEqual(resultado.execucao.versao_motor, "1.1.0.dev3")
        self.assertEqual(resultado.execucao.parametros.resolvedor_referencias, "participantes_discursivos_v1")
        self.assertGreaterEqual(resultado.execucao.duracao_ms, 0)
        self.assertEqual(
            resultado.execucao.parametros.estrategia_centralidade,
            "heuristica_explicavel_v1",
        )
        self.assertEqual(
            resultado.execucao.parametros.estrategia_sintese,
            "extrativa_conteudo_essencial_v1",
        )
        self.assertEqual(
            resultado.execucao.parametros.estrategia_parafrase,
            "substituicao_discursiva_controlada_v1",
        )
        self.assertEqual(
            resultado.execucao.parametros.metodo_checagem,
            "cobertura_estrutural_v1",
        )
        self.assertEqual(resultado.execucao.parametros.limite_alternativas_ideia_central, 2)
        self.assertTrue(resultado.execucao.parametros.usa_contexto_anterior)
        self.assertEqual(resultado.execucao.custos.chamadas_externas, 0)
        self.assertEqual(resultado.execucao.custos.tokens_entrada, 0)
        self.assertEqual(resultado.execucao.custos.tokens_saida, 0)
        self.assertEqual(resultado.execucao.custos.custo_estimado, 0)
        self.assertIn("Motor heurístico local", resultado.execucao.custos.observacao)

    def test_indica_ausencia_de_contexto_anterior(self) -> None:
        resultado = analisar_paragrafo("Helena concluiu o projeto.")

        self.assertFalse(resultado.execucao.parametros.usa_contexto_anterior)


if __name__ == "__main__":
    unittest.main()
