import copy
import json
from pathlib import Path
import unittest

from pydantic import ValidationError

from interpretador.linguistica import (
    BaseLinguistica,
    ErroAnotacao,
    TokenLinguistico,
    adaptar_anotacoes,
    analisar_texto,
    lematizar_palavra,
)


def entrada_minima(texto="Eu voltei. Ela chegou."):
    base = analisar_texto(texto)
    paragrafo_id = "p1"
    segmentacao = {
        "paragrafos": [{"id": paragrafo_id, "texto": texto, "original": {"inicio": 0, "fim": len(texto)}, "periodos": [p.id for p in base.periodos]}],
        "periodos": [], "tokens": [],
    }
    for periodo in base.periodos:
        segmentacao["periodos"].append({
            "id": periodo.id, "texto": periodo.texto, "original": {"inicio": periodo.inicio, "fim": periodo.fim},
            "paragrafo_id": paragrafo_id,
            "tokens": [t.id for t in base.tokens if t.periodo_id == periodo.id],
        })
    morfologia, sintaxe = [], []
    for token in base.tokens:
        comum = {"texto": token.texto, "original": {"inicio": token.inicio, "fim": token.fim},
                 "paragrafo_id": paragrafo_id, "periodo_id": token.periodo_id}
        segmentacao["tokens"].append({"id": token.id, **comum})
        morfologia.append({"token_id": token.id, **comum, "lema": token.lema or token.texto.casefold(),
                           "pos": token.pos or "PRON", "morfologia": {}})
        raiz = next(t for t in base.tokens if t.periodo_id == token.periodo_id and t.pos in {"VERB", "AUX"})
        sintaxe.append({"token_id": token.id, **comum, "cabeca_token_id": raiz.id,
                        "dependencia": "ROOT" if token.id == raiz.id else "dep"})
    return texto, segmentacao, morfologia, sintaxe


class LinguisticaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fontes = {}
        for numero in (19, 28):
            documento = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / f"vetorizacao-{numero}.json").read_bytes())
            analise = documento["contexto"]["regras"]["analise"]
            segmentacao = analise["anotacao"]["segmentacao"]
            cls.fontes[numero] = (segmentacao["preparacao"]["original"]["texto"], segmentacao,
                                  analise["anotacao"]["anotacoes_tokens"], analise["sintaxe"])

    def test_fontes_reais_preservam_tokens_periodos_e_coordenadas(self):
        for numero, total, inicio_p2 in ((19, 359, 889), (28, 170, 547)):
            with self.subTest(numero=numero):
                entrada = self.fontes[numero]
                bases = list(adaptar_anotacoes(*entrada).values())
                self.assertEqual(len(bases), 2)
                self.assertEqual(sum(len(b.tokens) for b in bases), total)
                self.assertEqual(sum(len(b.periodos) for b in bases), len(entrada[1]["periodos"]))
                self.assertEqual(bases[1].inicio_original, inicio_p2)
                for base in bases:
                    for token in base.tokens:
                        self.assertEqual(base.texto[token.inicio:token.fim], token.texto)
                        self.assertEqual(entrada[0][inicio_p2:][token.inicio:token.fim] if base is bases[1] else entrada[0][token.inicio:token.fim], token.texto)
                        self.assertIs(base.token_em(token.inicio, token.fim), token)
                self.assertIsNone(bases[0].token_em(0, 1))

    def test_correcao_lexical_nao_apaga_predicoes_recebidas(self):
        entrada = self.fontes[19]
        original = copy.deepcopy(entrada)
        bases = list(adaptar_anotacoes(*entrada).values())
        self.assertEqual(entrada, original)
        esperados = {"saí": ("sair", "VERB"), "gostasse": ("gostar", "VERB"),
                     "peguei": ("pegar", "VERB"), "exigia": ("exigir", "VERB"),
                     "deixei": ("deixar", "VERB"), "arrumei": ("arrumar", "VERB"),
                     "Fiquei": ("ficar", "VERB"), "Voltei": ("voltar", "VERB"),
                     "Retornei": ("retornar", "VERB"), "Parece": ("parecer", "VERB")}
        encontrados = {t.texto: t for b in bases for t in b.tokens if t.texto in esperados}
        self.assertEqual(set(encontrados), set(esperados))
        for texto, esperado in esperados.items():
            self.assertEqual((encontrados[texto].lema, encontrados[texto].pos), esperado)
        sai = encontrados["saí"]
        self.assertEqual(sai.recebida["morfologia"]["pos"], "PROPN")
        self.assertTrue(any(d.token_id == sai.id and d.codigo == "conflito_pos" for d in bases[0].diagnosticos))
        self.assertTrue(any(d.token_id == encontrados["peguei"].id and d.codigo == "conflito_tracos_morfologicos" for d in bases[0].diagnosticos))
        sai.recebida["morfologia"]["pos"] = "alterada"
        self.assertEqual(entrada, original)

    def test_funcoes_e_delimitadores_recebidos_nao_criam_nomes(self):
        base = next(iter(adaptar_anotacoes(*self.fontes[19]).values()))
        for palavra, pos in (("Ainda", "ADV"), ("Não", "ADV"), ("Será", "VERB")):
            self.assertEqual(next(t.pos for t in base.tokens if t.texto == palavra), pos)
        aspas = [t for t in base.tokens if t.texto == '"']
        self.assertTrue(aspas)
        self.assertTrue(all(t.pos == "PUNCT" for t in aspas))
        self.assertTrue(any(t.recebida["morfologia"]["pos"] == "PROPN" for t in aspas))

    def test_classes_funcionais_ambiguas_preservam_a_fonte(self):
        entrada = self.fontes[19]
        bases = adaptar_anotacoes(*entrada)
        todos = {t.id: t for b in bases.values() for t in b.tokens}
        for anotacao in entrada[2]:
            if anotacao["pos"] in {"ADP", "DET", "PRON", "SCONJ", "CCONJ", "ADV"} and not lematizar_palavra(anotacao["texto"]):
                self.assertEqual(todos[anotacao["token_id"]].pos, anotacao["pos"])

    def test_verbos_lexicais_nao_viram_auxiliares_pela_dependencia(self):
        base = next(iter(adaptar_anotacoes(*self.fontes[19]).values()))
        decidi = next(t for t in base.tokens if t.texto == "decidi")
        self.assertEqual((decidi.pos, decidi.dependencia), ("VERB", "aux"))
        self.assertTrue(any(d.token_id == decidi.id and d.codigo == "conflito_auxiliar_lexical" for d in base.diagnosticos))
        tinha = next(t for t in base.tokens if t.texto == "tinha")
        self.assertEqual(tinha.pos, "AUX")
        self.assertEqual(tinha.dependencia, "aux")

    def test_familias_fechadas_preservam_vogal_e_abstem_desconhecidos(self):
        for forma, lema in {"voltasse": "voltar", "acenasse": "acenar", "gostasse": "gostar",
                            "cantassem": "cantar", "bebesse": "beber", "partisse": "partir",
                            "trabalhavam": "trabalhar", "escreveram": "escrever", "saísse": "sair"}.items():
            self.assertEqual(lematizar_palavra(forma), lema)
        for palavra in ("classe", "passe", "repasse", "comando", "viagem", "conteúdo", "casasse", "inventasse", "xptoaram"):
            self.assertIsNone(lematizar_palavra(palavra))

    def test_local_preserva_cobertura_e_nao_inventa_sintaxe(self):
        base = analisar_texto("Helena sentou e percebeu; ele bombardeou, havia assinado. Eu saí e voltei.")
        self.assertEqual([t.lema for t in base.tokens if t.lema], ["sentar", "perceber", "bombardear", "haver", "assinar", "sair", "voltar"])
        self.assertTrue(all(t.dependencia is None and t.cabeca_id is None for t in base.tokens))
        self.assertEqual(len(base.diagnosticos), 1)
        self.assertEqual(base.diagnosticos[0].codigo, "analise_local_limitada")

    def test_local_preserva_unicode_crlf_e_aspas_finais(self):
        texto = '😀 Ele disse: “Não saí.”\r\n\r\nEu voltei.'
        base = analisar_texto(texto)
        self.assertEqual([p.texto for p in base.periodos], ['😀 Ele disse: “Não saí.”', 'Eu voltei.'])
        saiu = next(t for t in base.tokens if t.texto == "saí")
        self.assertEqual(saiu.inicio, texto.index("saí"))
        self.assertEqual(base.texto[saiu.inicio:saiu.fim], "saí")
        self.assertEqual(base.periodos[1].inicio, texto.index("Eu voltei"))
        self.assertEqual(analisar_texto("").tokens, [])
        self.assertEqual(analisar_texto("   ").periodos, [])

    def test_intervalos_pydantic_rejeitam_booleans_e_recortes_falsos(self):
        for intervalo in ({"inicio": True, "fim": 2}, {"inicio": 2, "fim": 2}, {"inicio": -1, "fim": 2}):
            with self.assertRaises(ValidationError):
                TokenLinguistico(id="t1", texto="eu", **intervalo)
        base = analisar_texto("Eu voltei.")
        dados = base.model_dump()
        dados["tokens"][0]["texto"] = "Ela"
        with self.assertRaises(ValidationError):
            BaseLinguistica.model_validate(dados)

    def test_anotacoes_ausentes_e_parciais_sao_explicitas(self):
        texto, segmentacao, morfologia, sintaxe = entrada_minima()
        base = adaptar_anotacoes(texto, segmentacao, None, None)["p1"]
        self.assertIn("anotacoes_ausentes", [d.codigo for d in base.diagnosticos])
        self.assertEqual(next(t.lema for t in base.tokens if t.texto == "voltei"), "voltar")
        parcial = adaptar_anotacoes(texto, segmentacao, morfologia[:1], sintaxe)["p1"]
        voltei = next(t for t in parcial.tokens if t.texto == "voltei")
        self.assertEqual(voltei.lema, "voltar")
        self.assertEqual(voltei.recebida["sintaxe"], sintaxe[1])
        self.assertTrue(any(d.codigo == "morfologia_ausente" and d.token_id == voltei.id for d in parcial.diagnosticos))

    def assert_erro(self, entrada, codigo):
        with self.assertRaises(ErroAnotacao) as erro:
            adaptar_anotacoes(*entrada)
        self.assertIn(codigo, [p.codigo for p in erro.exception.problemas])
        self.assertTrue(all(p.caminho and p.mensagem for p in erro.exception.problemas))

    def test_anotacoes_malformadas_nao_caem_silenciosamente_no_local(self):
        texto, seg, morf, sintaxe = entrada_minima()
        self.assert_erro((texto, seg, {}, sintaxe), "tipo_invalido")
        self.assert_erro((texto, seg, [*morf, morf[0]], sintaxe), "identificador_duplicado")
        adulterada = copy.deepcopy(morf)
        adulterada[0]["token_id"] = "nao-existe"
        self.assert_erro((texto, seg, adulterada, sintaxe), "referencia_quebrada")
        adulterada = copy.deepcopy(morf)
        adulterada[0]["pos"] = 42
        self.assert_erro((texto, seg, adulterada, sintaxe), "tipo_invalido")
        adulterada = copy.deepcopy(morf)
        adulterada[0]["pos"] = "inventada"
        self.assert_erro((texto, seg, adulterada, sintaxe), "classe_gramatical_invalida")

    def test_segmentacao_rejeita_identidades_e_offsets_divergentes(self):
        texto, seg, morf, sintaxe = entrada_minima()
        adulterada = copy.deepcopy(seg)
        adulterada["tokens"].append(adulterada["tokens"][0])
        self.assert_erro((texto, adulterada, morf, sintaxe), "identificador_duplicado")
        adulterada = copy.deepcopy(seg)
        adulterada["tokens"][0]["original"]["inicio"] = 1
        self.assert_erro((texto, adulterada, morf, sintaxe), "texto_divergente")
        adulterada = copy.deepcopy(seg)
        adulterada["tokens"][0]["periodo_id"] = "ausente"
        self.assert_erro((texto, adulterada, morf, sintaxe), "referencia_quebrada")
        adulterada = copy.deepcopy(seg)
        adulterada["tokens"][0]["trabalho"] = {"inicio": 2, "fim": 4}
        self.assert_erro((texto, adulterada, morf, sintaxe), "coordenadas_trabalho_divergentes")
        adulterada = copy.deepcopy(morf)
        adulterada[0]["original"]["fim"] += 1
        self.assert_erro((texto, seg, adulterada, sintaxe), "anotacao_divergente")

    def test_sintaxe_rejeita_cabecas_inexistentes_fora_do_periodo_e_ciclos(self):
        texto, seg, morf, sintaxe = entrada_minima()
        adulterada = copy.deepcopy(sintaxe)
        adulterada[0]["cabeca_token_id"] = "ausente"
        self.assert_erro((texto, seg, morf, adulterada), "referencia_quebrada")
        adulterada = copy.deepcopy(sintaxe)
        adulterada[0]["cabeca_token_id"] = sintaxe[-1]["token_id"]
        self.assert_erro((texto, seg, morf, adulterada), "cabeca_fora_do_periodo")
        adulterada = copy.deepcopy(sintaxe)
        adulterada[0]["cabeca_token_id"] = adulterada[0]["token_id"]
        self.assert_erro((texto, seg, morf, adulterada), "ciclo_sintatico")
        adulterada = copy.deepcopy(sintaxe)
        adulterada[0]["cabeca_token_id"] = adulterada[1]["token_id"]
        adulterada[1]["cabeca_token_id"] = adulterada[0]["token_id"]
        adulterada[1]["dependencia"] = "dep"
        self.assert_erro((texto, seg, morf, adulterada), "ciclo_sintatico")

    def test_lema_desconhecido_de_fonte_fica_hipotese_ou_abstencao(self):
        texto, seg, morf, sintaxe = entrada_minima("Ela ziguezagueou e chegou.")
        posicao = next(i for i, t in enumerate(morf) if t["texto"] == "ziguezagueou")
        morf[posicao].update(lema="ziguezaguear", pos="VERB")
        base = adaptar_anotacoes(texto, seg, morf, sintaxe)["p1"]
        token = next(t for t in base.tokens if t.texto == "ziguezagueou")
        self.assertEqual(token.lema, "ziguezaguear")
        self.assertIn("lema_recebido_como_hipotese", token.decisoes)
        morf[posicao]["lema"] = "ziguezagueou"
        base = adaptar_anotacoes(texto, seg, morf, sintaxe)["p1"]
        self.assertIsNone(next(t for t in base.tokens if t.texto == "ziguezagueou").lema)
        self.assertIn("lema_verbal_nao_sustentado", [d.codigo for d in base.diagnosticos])


if __name__ == "__main__":
    unittest.main()
