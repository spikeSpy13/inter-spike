import copy
import json
import math
from pathlib import Path
import unittest

from interpretador.ingestao import ErroIngestao, validar_documento
from interpretador.main import analisar_json, validar_json
from interpretador.models import JsonAnalysisRequest


class IngestaoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "vetorizacao-28.json"
        cls.documento = json.loads(fixture.read_text())

    def assertProblema(self, documento: dict, codigo: str, caminho: str) -> None:
        with self.assertRaises(ErroIngestao) as captura:
            validar_documento(documento)
        problemas = captura.exception.problemas
        self.assertTrue(
            any(item.codigo == codigo and item.caminho == caminho for item in problemas),
            [(item.codigo, item.caminho) for item in problemas],
        )

    def test_fixture_real_e_aceita_sem_perder_original(self) -> None:
        documento = validar_documento(self.documento)
        original = self.documento["contexto"]["regras"]["analise"]["anotacao"]["segmentacao"]["preparacao"]["original"]["texto"]

        self.assertEqual(documento.texto_original, original)
        self.assertEqual(documento.documento_id, 28)
        self.assertEqual(len(documento.paragrafos), 2)
        self.assertEqual(documento.periodos_total, 6)
        self.assertEqual(documento.tokens_total, 170)
        self.assertEqual(documento.representacoes_total, 9)
        self.assertEqual(documento.artefatos_total, 7)
        self.assertEqual(documento.dimensao_vetores, 1024)
        self.assertEqual(documento.paragrafos[1].texto, original[547:996])

    def test_resposta_expoe_paragrafos_e_vinculos_vetoriais(self) -> None:
        resposta = validar_json(self.documento)

        self.assertEqual(resposta.schema_version, "0.5.0")
        self.assertEqual(resposta.fonte.etapa, "09_vetorizacao")
        self.assertEqual([item.rotulo for item in resposta.paragrafos], ["P1", "P2"])
        self.assertEqual(resposta.paragrafos[1].intervalo_original.inicio, 547)
        self.assertTrue(resposta.paragrafos[1].representacao_id)
        self.assertTrue(resposta.paragrafos[1].artefato_id.startswith("sha256:"))

    def test_analise_seleciona_paragrafo_e_contexto_anterior(self) -> None:
        resposta = analisar_json(JsonAnalysisRequest(documento=self.documento, paragrafo_id="P2"))

        self.assertEqual(resposta.schema_version, "0.5.0")
        self.assertEqual(resposta.paragrafo.rotulo, "P2")
        self.assertEqual(resposta.analise.paragrafo, resposta.paragrafo.texto)
        self.assertEqual(resposta.analise.contexto_anterior, validar_documento(self.documento).paragrafos[0].texto)
        self.assertGreater(resposta.analise.resumo.proposicoes, 0)

    def test_rejeita_referencia_de_periodo_quebrada(self) -> None:
        documento = copy.deepcopy(self.documento)
        caminho = "$.contexto.regras.analise.anotacao.segmentacao.paragrafos[0].periodos[0]"
        documento["contexto"]["regras"]["analise"]["anotacao"]["segmentacao"]["paragrafos"][0]["periodos"][0] = "periodo:inexistente"
        self.assertProblema(documento, "referencia_quebrada", caminho)

    def test_rejeita_vetor_com_dimensao_incorreta(self) -> None:
        documento = copy.deepcopy(self.documento)
        documento["artefatos"][0]["valores"].pop()
        self.assertProblema(documento, "vetor_dimensao_incorreta", "$.artefatos[0].valores")

    def test_rejeita_vetor_nao_finito(self) -> None:
        documento = copy.deepcopy(self.documento)
        documento["artefatos"][0]["valores"][10] = math.inf
        self.assertProblema(documento, "vetor_nao_finito", "$.artefatos[0].valores")

    def test_rejeita_vetor_com_norma_l2_incorreta(self) -> None:
        documento = copy.deepcopy(self.documento)
        documento["artefatos"][0]["valores"] = [valor * 2 for valor in documento["artefatos"][0]["valores"]]
        self.assertProblema(documento, "vetor_nao_normalizado", "$.artefatos[0].valores")

    def test_rejeita_representacao_com_artefato_inexistente(self) -> None:
        documento = copy.deepcopy(self.documento)
        documento["representacoes"][0]["artefato_id"] = "sha256:inexistente"
        self.assertProblema(documento, "referencia_quebrada", "$.representacoes[0].artefato_id")

    def test_rejeita_intervalo_fora_do_original(self) -> None:
        documento = copy.deepcopy(self.documento)
        paragrafo = documento["contexto"]["regras"]["analise"]["anotacao"]["segmentacao"]["paragrafos"][0]
        paragrafo["original"]["fim"] = 10_000
        caminho = "$.contexto.regras.analise.anotacao.segmentacao.paragrafos[0].original"
        self.assertProblema(documento, "intervalo_invalido", caminho)

    def test_rejeita_schema_e_etapa_incompativeis(self) -> None:
        documento = copy.deepcopy(self.documento)
        documento["schema_version"] = "2.0.0"
        documento["etapa"] = "08_unidades_contexto"
        with self.assertRaises(ErroIngestao) as captura:
            validar_documento(documento)
        codigos = {item.codigo for item in captura.exception.problemas}
        self.assertIn("schema_incompativel", codigos)
        self.assertIn("etapa_incompativel", codigos)


if __name__ == "__main__":
    unittest.main()
