import copy
import json
from pathlib import Path
import unittest

from interpretador.extractor import analisar_paragrafo
from interpretador.geracao import _periodos
from interpretador.ingestao import ErroIngestao, validar_documento
from interpretador.main import analisar_json
from interpretador.models import JsonAnalysisRequest


ROOT = Path(__file__).resolve().parents[1]


class Documento19RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entrada = json.loads((ROOT / "fixtures/vetorizacao-19.json").read_bytes())
        cls.documento = validar_documento(cls.entrada)
        cls.respostas = {
            label: analisar_json(JsonAnalysisRequest(documento=cls.entrada, paragrafo_id=label))
            for label in ("P1", "P2")
        }

    def test_preserva_original_e_coordenadas_do_segundo_paragrafo(self) -> None:
        primeiro, segundo = self.documento.paragrafos
        self.assertEqual(self.documento.texto_original[885:889], "\r\n\r\n")
        self.assertEqual(segundo.base_linguistica.inicio_original, 889)
        terminei = segundo.base_linguistica.token_em(30, 38)
        self.assertEqual(terminei.texto, "terminei")
        self.assertEqual(self.documento.texto_original[919:927], terminei.texto)
        resposta = self.respostas["P2"].analise
        self.assertEqual(resposta.analise_linguistica.contexto_anterior.texto, primeiro.texto)
        self.assertEqual(resposta.analise_linguistica.paragrafo.texto, segundo.texto)

    def test_corrige_lemas_sem_apagar_predicoes_recebidas(self) -> None:
        analise = self.respostas["P1"].analise
        lemas = {item.forma_textual: item.predicado for item in analise.proposicoes}
        for forma, lema in {"voltasse": "voltar", "acenasse": "acenar", "gostasse": "gostar", "saí": "sair"}.items():
            with self.subTest(forma=forma):
                self.assertEqual(lemas[forma], lema)
        token = analise.analise_linguistica.paragrafo.token_em(767, 775)
        self.assertEqual(token.recebida["morfologia"]["lema"], "gostasse")
        self.assertEqual(token.lema, "gostar")
        self.assertTrue(any(item.token_id == token.id for item in analise.analise_linguistica.paragrafo.diagnosticos))

    def test_palavras_funcionais_nao_criam_pessoas_ou_antecedentes(self) -> None:
        analise = self.respostas["P1"].analise
        falsas = {"Ainda", "Não", "Será"}
        self.assertFalse(any(item.tipo == "nome_proprio" and item.texto in falsas for item in analise.mencoes))
        self.assertFalse(any(item.rotulo in falsas for item in analise.referentes))
        self.assertTrue(any(item.texto == "meu pai" and item.caracteristicas.classe_semantica == "pessoa" for item in analise.mencoes))

    def test_primeira_pessoa_e_terceira_pessoa_tem_referentes_distintos(self) -> None:
        analise = self.respostas["P1"].analise
        mencoes = {item.id: item for item in analise.mencoes}
        narrador = next(item for item in analise.referentes if item.tipo == "participante_discursivo")
        pai = next(item for item in analise.referentes if item.rotulo == "meu pai")
        self.assertEqual(narrador.rotulo, "narrador")
        self.assertTrue({"eu", "meu", "minha"} <= {mencoes[item].texto.casefold() for item in narrador.mencoes})
        self.assertTrue({"ele", "dele"} <= {mencoes[item].texto.casefold() for item in pai.mencoes})
        self.assertFalse(set(narrador.mencoes) & set(pai.mencoes))

    def test_pronomes_de_helena_no_segundo_paragrafo_sao_resolvidos(self) -> None:
        analise = self.respostas["P2"].analise
        mencoes = {item.id: item for item in analise.mencoes}
        helena = next(item for item in analise.referentes if item.rotulo == "Helena")
        superficies = {
            mencoes[item].texto.casefold()
            for item in helena.mencoes
            if mencoes[item].origem == "paragrafo"
        }
        self.assertTrue({"ela", "dela"} <= superficies)
        pendentes = [
            item for item in analise.resolucoes
            if item.estado in {"ambigua", "nao_resolvida"}
            and mencoes[item.mencao_id].origem == "paragrafo"
        ]
        self.assertEqual(pendentes, [])

    def test_auxiliar_nao_substitui_predicado_lexical(self) -> None:
        formas = {p.forma_textual for p in self.respostas["P1"].analise.proposicoes}
        self.assertIn("enxugado", formas)
        self.assertNotIn("tinha", formas)

    def test_negacao_nao_atravessa_subordinada_temporal(self) -> None:
        analise = self.respostas["P1"].analise
        sair = next(p for p in analise.proposicoes if p.forma_textual == "saí")
        voltar = next(p for p in analise.proposicoes if p.forma_textual == "voltasse")
        self.assertEqual(sair.operadores.negacao, "não")
        self.assertIsNone(voltar.operadores.negacao)

    def test_reconhece_verbos_de_p2_e_abstem_participios_descritivos(self) -> None:
        analise = self.respostas["P2"].analise
        formas = {p.forma_textual for p in analise.proposicoes}
        self.assertTrue({"terminei", "enviei", "chamou", "leu"} <= formas)
        self.assertTrue({"lascada", "parado"}.isdisjoint(formas))
        self.assertTrue(any(item.codigo == "participio_descritivo_omitido" for item in analise.analise_linguistica.paragrafo.diagnosticos))

    def test_segmentacao_compartilhada_preserva_aspas_de_fechamento(self) -> None:
        texto = self.documento.paragrafos[0].texto
        self.assertIn((252, 362), _periodos(texto))
        for texto in ['Ana disse: "Eu volto amanhã." Beatriz leu.', 'Ana disse: “Eu volto amanhã.” Beatriz leu.']:
            with self.subTest(texto=texto):
                recortes = [texto[inicio:fim] for inicio, fim in _periodos(texto)]
                self.assertEqual(len(recortes), 2)
                self.assertIn(recortes[0][-1], {'"', '”'})
                self.assertEqual(recortes[1], "Beatriz leu.")

    def test_entrada_sem_anotacoes_tem_fallback_auditavel(self) -> None:
        entrada = copy.deepcopy(self.entrada)
        analise = entrada["contexto"]["regras"]["analise"]
        analise["anotacao"].pop("anotacoes_tokens")
        analise.pop("sintaxe")
        documento = validar_documento(entrada)
        base = documento.paragrafos[0].base_linguistica
        self.assertEqual(base.origem, "heuristica_local")
        self.assertTrue(any(d.codigo == "anotacoes_ausentes" for d in base.diagnosticos))

    def test_anotacao_estruturalmente_invalida_retorna_erro_de_ingestao(self) -> None:
        entrada = copy.deepcopy(self.entrada)
        itens = entrada["contexto"]["regras"]["analise"]["anotacao"]["anotacoes_tokens"]
        itens.append(copy.deepcopy(itens[0]))
        with self.assertRaises(ErroIngestao) as captura:
            validar_documento(entrada)
        self.assertTrue(any(p.codigo == "identificador_duplicado" and "anotacoes_tokens" in p.caminho for p in captura.exception.problemas))

    def test_texto_livre_compartilha_lemas_e_avisa_limites(self) -> None:
        analise = analisar_paragrafo("Ana acenasse, João voltasse e Maria gostasse da viagem.")
        self.assertEqual({p.predicado for p in analise.proposicoes}, {"acenar", "voltar", "gostar"})
        self.assertEqual(analise.analise_linguistica.paragrafo.origem, "heuristica_local")
        self.assertTrue(any("revisão" in alerta for alerta in analise.alertas))


if __name__ == "__main__":
    unittest.main()
