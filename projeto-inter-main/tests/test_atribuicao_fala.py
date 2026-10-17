import unittest

from interpretador.extractor import analisar_paragrafo


class AtribuicaoDeFalaTests(unittest.TestCase):
    def _quadro(self, resultado, predicado="assinar"):
        proposicao = next(item for item in resultado.proposicoes if item.predicado == predicado)
        return next(item for item in resultado.quadros_atribuicao if item.id == proposicao.atribuicao_id)

    def _referente_da_mencao(self, resultado, texto):
        mencao = next(item for item in resultado.mencoes if item.texto.casefold() == texto.casefold())
        return next(item for item in resultado.resolucoes if item.mencao_id == mencao.id).referente_id

    def test_fonte_anteposta_e_posposta_respeita_sujeito_da_relatora(self):
        textos = [
            'Maria disse: "Helena assinou o contrato."',
            'Maria disse: “Helena assinou o contrato.”',
            '"Helena assinou o contrato", afirmou Maria.',
            '“Helena assinou o contrato”, afirmou Maria.',
        ]
        for texto in textos:
            with self.subTest(texto=texto):
                resultado = analisar_paragrafo(texto)
                quadro = self._quadro(resultado)
                self.assertEqual(quadro.modo, "fala_citada")
                self.assertEqual((quadro.fonte.tipo, quadro.fonte.rotulo), ("referente", "Maria"))

    def test_destinatario_da_relatora_nao_vira_falante(self):
        resultado = analisar_paragrafo('Ana disse a Maria: "Helena assinou o contrato."')
        self.assertEqual(self._quadro(resultado).fonte.rotulo, "Ana")

    def test_duas_falas_mantem_fontes_distintas(self):
        resultado = analisar_paragrafo(
            'Ana disse: "Helena assinou o contrato." Maria afirmou: "João chegou."'
        )
        self.assertEqual(self._quadro(resultado, "assinar").fonte.rotulo, "Ana")
        self.assertEqual(self._quadro(resultado, "chegar").fonte.rotulo, "Maria")

    def test_nao_busca_fonte_em_outro_periodo(self):
        textos = [
            'Ana disse. "Helena assinou o contrato."',
            '"Helena assinou o contrato." Maria afirmou que João chegou.',
            '"Helena assinou o contrato."',
        ]
        for texto in textos:
            with self.subTest(texto=texto):
                quadro = self._quadro(analisar_paragrafo(texto))
                self.assertEqual((quadro.modo, quadro.fonte.tipo), ("fala_citada", "nao_resolvida"))

    def test_verbo_de_fala_interno_nao_substitui_relatora_externa(self):
        resultado = analisar_paragrafo('"Ana disse que Helena assinou o contrato", afirmou Maria.')
        self.assertEqual(self._quadro(resultado, "assinar").fonte.rotulo, "Maria")
        self.assertEqual(self._quadro(resultado, "dizer").fonte.rotulo, "Maria")

    def test_pergunta_citada_preserva_fonte(self):
        resultado = analisar_paragrafo('"Helena assinou o contrato?", perguntou Maria.')
        quadro = self._quadro(resultado)
        self.assertEqual((quadro.modo, quadro.fonte.rotulo), ("fala_citada", "Maria"))

    def test_sem_sujeito_relatora_nao_usa_destinatario_como_fonte(self):
        resultado = analisar_paragrafo('Disse para Maria: "Helena assinou o contrato."')
        self.assertEqual(self._quadro(resultado).fonte.tipo, "nao_resolvida")

    def test_possessivo_respeita_fonte_anteposta_e_posposta(self):
        textos = [
            'Ana disse: "Meu contrato foi assinado."',
            '"Meu contrato foi assinado", disse Ana.',
        ]
        for texto in textos:
            for contexto in [False, True]:
                with self.subTest(texto=texto, contexto=contexto):
                    resultado = analisar_paragrafo("Maria chegou.", texto) if contexto else analisar_paragrafo(texto)
                    meu = self._referente_da_mencao(resultado, "Meu")
                    ana = self._referente_da_mencao(resultado, "Ana")
                    self.assertIsNotNone(meu)
                    self.assertEqual(meu, ana)

    def test_pronome_pessoal_de_primeira_pessoa_respeita_fonte_da_citacao(self):
        resultado = analisar_paragrafo('Ana disse: "Eu assinei meu contrato."')
        ana = self._referente_da_mencao(resultado, "Ana")
        self.assertEqual(self._referente_da_mencao(resultado, "Eu"), ana)
        self.assertEqual(self._referente_da_mencao(resultado, "meu"), ana)

    def test_primeira_pessoa_em_citacao_sem_fonte_expoe_pendencia(self):
        resultado = analisar_paragrafo('"Eu assinei meu contrato."')
        for texto in ("Eu", "meu"):
            mencao = next(item for item in resultado.mencoes if item.texto == texto)
            resolucao = next(item for item in resultado.resolucoes if item.mencao_id == mencao.id)
            self.assertEqual(resolucao.estado, "nao_resolvida")
            self.assertEqual(resolucao.motivo_pendencia, "fonte_fala_desconhecida")

    def test_possessivo_sem_enquadramento_continua_sem_fonte(self):
        textos = [
            '"Meu contrato foi assinado." Maria disse.',
            'Ana disse. "Meu contrato foi assinado."',
            'Disse para Maria: "Meu contrato foi assinado."',
        ]
        for texto in textos:
            with self.subTest(texto=texto):
                resultado = analisar_paragrafo(texto)
                self.assertIsNone(self._referente_da_mencao(resultado, "Meu"))

    def test_duas_citacoes_nao_misturam_possessivos(self):
        resultado = analisar_paragrafo(
            'Ana disse: "Meu contrato foi assinado." Maria afirmou: "Minha proposta chegou."'
        )
        self.assertEqual(
            self._referente_da_mencao(resultado, "Meu"),
            self._referente_da_mencao(resultado, "Ana"),
        )
        self.assertEqual(
            self._referente_da_mencao(resultado, "Minha"),
            self._referente_da_mencao(resultado, "Maria"),
        )


if __name__ == "__main__":
    unittest.main()
