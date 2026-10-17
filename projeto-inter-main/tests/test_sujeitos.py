import json
from pathlib import Path
import unittest

from interpretador.ingestao import validar_documento
from interpretador.linguistica.base import analisar_texto
from interpretador.referencias.detector import detectar_mencoes
from interpretador.sujeitos import selecionar_sujeito


ROOT = Path(__file__).resolve().parents[1]


def analisar_sujeito(texto, forma, ocorrencia=0):
    base = analisar_texto(texto)
    mencoes = detectar_mencoes(texto, base_linguistica=base)
    token = [item for item in base.tokens if item.normalizado == forma.casefold()][ocorrencia]
    return selecionar_sujeito(base, token, mencoes)


def anotar(base, forma, *, lema=None, pos=None, dependencia=None, cabeca=None):
    token = next(item for item in base.tokens if item.normalizado == forma.casefold())
    if lema is not None:
        token.lema = lema
    if pos is not None:
        token.pos = pos
    token.dependencia = dependencia
    if cabeca is not None:
        token.cabeca_id = next(item.id for item in base.tokens if item.normalizado == cabeca.casefold())
    return token


class SelecaoSujeitoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documentos = {
            numero: validar_documento(json.loads((ROOT / f"fixtures/vetorizacao-{numero}.json").read_bytes()))
            for numero in (19, 28)
        }

    def sujeito_documento(self, numero, paragrafo, forma):
        entrada = self.documentos[numero].paragrafos[paragrafo]
        base = entrada.base_linguistica
        mencoes = detectar_mencoes(entrada.texto, base_linguistica=base)
        token = next(item for item in base.tokens if item.normalizado == forma.casefold())
        resultado = selecionar_sujeito(base, token, mencoes)
        if resultado.mencao:
            self.assertIn(resultado.mencao, mencoes)
            self.assertEqual(resultado.mencao.origem, "paragrafo")
        for inicio, fim in resultado.evidencias:
            self.assertTrue(0 <= inicio < fim <= len(base.texto))
        return resultado

    def test_documento19_coordenacao_nao_promove_objetos(self):
        esperados = ((0, "acenasse", "ele"), (0, "disse", "Ele"),
                     (1, "leu", "Ela"), (1, "demonstrar", "Ela"), (1, "deu", "Ela"))
        for paragrafo, forma, esperado in esperados:
            with self.subTest(forma=forma):
                resultado = self.sujeito_documento(19, paragrafo, forma)
                self.assertEqual(resultado.mencao.texto, esperado)
                self.assertNotIn(resultado.mencao.texto, {"um copo", "a folha", "Ainda"})
                self.assertIn(resultado.metodo, {"dependencia_coordenacao", "dependencia_controle_sujeito"})

    def test_documento19_cadeia_de_controle_e_explicavel(self):
        resultado = self.sujeito_documento(19, 0, "acenasse")
        razoes = " ".join(resultado.razoes)
        self.assertIn("pegar", razoes)
        self.assertIn("voltasse", razoes)
        self.assertGreaterEqual(len(resultado.evidencias), 4)
        self.assertEqual(resultado.candidato_ids, [resultado.mencao.id])

    def test_documento19_nsubj_verbal_recebido_nao_vira_sujeito(self):
        resultado = self.sujeito_documento(19, 1, "tomava")
        self.assertIsNone(resultado.mencao)
        self.assertEqual(resultado.metodo, "abstencao")
        self.assertIn("nominal", " ".join(resultado.razoes))

    def test_documento19_abstem_sujeito_eliptico_sem_inventar_narrador(self):
        resultado = self.sujeito_documento(19, 1, "terminei")
        self.assertIsNone(resultado.mencao)
        self.assertTrue(resultado.razoes)

    def test_fonte28_coordenacao_negativa_e_controle_conservam_profissional(self):
        for forma in ("abandonou", "desistiu", "buscar"):
            with self.subTest(forma=forma):
                self.assertEqual(self.sujeito_documento(28, 1, forma).mencao.texto, "a profissional")

    def test_fonte28_relativo_sujeito_recupera_antecedente(self):
        for forma in ("construiu", "transformando"):
            with self.subTest(forma=forma):
                self.assertEqual(self.sujeito_documento(28, 1, forma).mencao.texto, "alguém")

    def test_fonte28_passiva_preserva_nominal_com_etiqueta_adj_conflitante(self):
        resultado = self.sujeito_documento(28, 0, "encontrada")
        self.assertEqual(resultado.mencao.texto, "nenhuma falha técnica")
        self.assertIn("ADJ", " ".join(resultado.razoes))

    def test_fonte28_relatora_posposta_revisa_objeto_incompativel(self):
        resultado = self.sujeito_documento(28, 0, "murmurou")
        self.assertEqual(resultado.mencao.texto, "a engenheira")
        self.assertEqual(resultado.metodo, "sujeito_posposto_relato")
        self.assertIn("conflita", " ".join(resultado.razoes))

    def test_livre_objeto_nao_substitui_sujeito_da_coordenada(self):
        for texto, forma, esperado in (
            ("Ela pegou a folha, leu o conteúdo.", "leu", "Ela"),
            ("Ana viu João e saiu.", "saiu", "Ana"),
            ("A profissional não abandonou o projeto nem desistiu de buscar recursos.", "desistiu", "A profissional"),
            ("João assinou e Helena enviou o contrato.", "enviou", "Helena"),
            ("Ana percebeu que João leu o contrato e saiu.", "saiu", "João"),
        ):
            with self.subTest(texto=texto):
                self.assertEqual(analisar_sujeito(texto, forma).mencao.texto, esperado)

    def test_livre_auxiliares_reflexivo_e_passiva_nao_cortam_sujeito(self):
        for texto, forma, esperado in (
            ("O tempo já estava se esgotando.", "esgotando", "O tempo"),
            ("Nenhuma falha tivesse sido encontrada.", "encontrada", "Nenhuma falha"),
            ("O contrato foi assinado e enviado por Ana.", "enviado", "O contrato"),
            ("O gerente não havia assinado o contrato.", "assinado", "O gerente"),
        ):
            with self.subTest(texto=texto):
                self.assertEqual(analisar_sujeito(texto, forma).mencao.texto, esperado)

    def test_livre_preserva_nucleo_da_descricao_complexa(self):
        texto = "Alguém que construiu a carreira transformando crises reagiu."
        for forma in ("construiu", "transformando", "reagiu"):
            with self.subTest(forma=forma):
                self.assertEqual(analisar_sujeito(texto, forma).mencao.texto, "Alguém")

    def test_livre_sujeito_da_relativa_nao_vaza_para_oracao_externa(self):
        texto = "A folha que Ana leu reagiu."
        self.assertEqual(analisar_sujeito(texto, "leu").mencao.texto, "Ana")
        self.assertIsNone(analisar_sujeito(texto, "reagiu").mencao)

    def test_livre_relatos_nao_usam_sujeito_de_completiva_ou_citacao(self):
        for texto, esperado in (
            ("Maria disse que João leu.", "Maria"),
            ("Disse que João leu.", None),
            ('"Eu volto", disse Maria.', "Maria"),
            ('"Eu volto", disse.', None),
            ('Ele disse: "João leu".', "Ele"),
            ("Disse uma frase.", None),
        ):
            with self.subTest(texto=texto):
                resultado = analisar_sujeito(texto, "disse")
                self.assertEqual(resultado.mencao.texto if resultado.mencao else None, esperado)

    def test_dependencia_nao_atravessa_aspas_ou_periodos(self):
        for texto, sujeito, alvo in (
            ('Ana disse: "leu o livro".', "Ana", "leu"),
            ('"Ana leu", "saiu".', "Ana", "saiu"),
            ("Ana leu. Saiu.", "Ana", "Saiu"),
        ):
            with self.subTest(texto=texto):
                base = analisar_texto(texto)
                anotar(base, sujeito, pos="PROPN", dependencia="nsubj", cabeca=alvo)
                token = anotar(base, alvo, dependencia="ROOT", cabeca=alvo)
                mencoes = detectar_mencoes(texto, base_linguistica=base)
                self.assertIsNone(selecionar_sujeito(base, token, mencoes).mencao)

    def test_coordenacao_recebida_nao_atravessa_fala_citada(self):
        texto = 'Ana disse: "leu o livro".'
        base = analisar_texto(texto)
        anotar(base, "Ana", pos="PROPN", dependencia="nsubj", cabeca="disse")
        anotar(base, "disse", dependencia="ROOT", cabeca="disse")
        token = anotar(base, "leu", dependencia="conj", cabeca="disse")
        mencoes = detectar_mencoes(texto, base_linguistica=base)
        self.assertIsNone(selecionar_sujeito(base, token, mencoes).mencao)

    def test_complemento_de_pedir_nao_assume_controle_por_ana(self):
        texto = "Ana pediu João para assinar o contrato."
        base = analisar_texto(texto)
        anotar(base, "Ana", pos="PROPN", dependencia="nsubj", cabeca="pediu")
        anotar(base, "pediu", pos="VERB", lema="pedir", dependencia="ROOT", cabeca="pediu")
        anotar(base, "João", pos="PROPN", dependencia="obj", cabeca="pediu")
        token = anotar(base, "assinar", dependencia="xcomp", cabeca="pediu")
        mencoes = detectar_mencoes(texto, base_linguistica=base)
        resultado = selecionar_sujeito(base, token, mencoes)
        self.assertIsNone(resultado.mencao)
        self.assertIn("controle", " ".join(resultado.razoes))

    def test_complemento_tem_sujeito_proprio_quando_anotado(self):
        texto = "Ana pediu João para assinar o contrato."
        base = analisar_texto(texto)
        anotar(base, "Ana", pos="PROPN", dependencia="nsubj", cabeca="pediu")
        anotar(base, "pediu", pos="VERB", lema="pedir", dependencia="ROOT", cabeca="pediu")
        anotar(base, "João", pos="PROPN", dependencia="nsubj", cabeca="assinar")
        token = anotar(base, "assinar", dependencia="xcomp", cabeca="pediu")
        mencoes = detectar_mencoes(texto, base_linguistica=base)
        self.assertEqual(selecionar_sujeito(base, token, mencoes).mencao.texto, "João")

    def test_verbo_de_controle_com_objeto_interveniente_abstem(self):
        texto = "Ana quer João para assinar o contrato."
        base = analisar_texto(texto)
        anotar(base, "Ana", pos="PROPN", dependencia="nsubj", cabeca="quer")
        anotar(base, "quer", dependencia="ROOT", cabeca="quer")
        anotar(base, "João", pos="PROPN", dependencia="obj", cabeca="quer")
        token = anotar(base, "assinar", dependencia="xcomp", cabeca="quer")
        mencoes = detectar_mencoes(texto, base_linguistica=base)
        self.assertIsNone(selecionar_sujeito(base, token, mencoes).mencao)

    def test_contexto_anterior_nao_fornece_mencao_sintatica(self):
        texto = "Leu o livro."
        base = analisar_texto(texto)
        mencoes = detectar_mencoes("Ana leu o livro.", origem="contexto_anterior")
        token = next(item for item in base.tokens if item.normalizado == "leu")
        self.assertIsNone(selecionar_sujeito(base, token, mencoes).mencao)

    def test_nao_muda_mencoes_ou_base_ao_decidir(self):
        base = analisar_texto("Ela pegou a folha, leu o conteúdo.")
        mencoes = detectar_mencoes(base.texto, base_linguistica=base)
        original_base = base.model_dump()
        originais = [item.model_dump() for item in mencoes]
        token = next(item for item in base.tokens if item.normalizado == "leu")
        selecionar_sujeito(base, token, mencoes)
        self.assertEqual(base.model_dump(), original_base)
        self.assertEqual([item.model_dump() for item in mencoes], originais)


if __name__ == "__main__":
    unittest.main()
