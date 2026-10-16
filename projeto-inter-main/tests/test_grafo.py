import unittest

from interpretador.extractor import analisar_paragrafo


CONTEXTO = (
    "Quando Helena finalmente se sentou no banco da praça, percebeu que o gerente do "
    "banco não havia assinado o contrato de financiamento por pura cautela. Durante "
    "toda a reunião matinal, ele bombardeou a proposta dela com argumentos pesados, "
    "embora nenhuma falha técnica tivesse sido encontrada nos cálculos pelos auditores "
    'externos. "Claro, porque perder três semanas revisando planilhas é exatamente o '
    'meu conceito de eficiência", murmurou a engenheira para si mesma, enquanto a '
    "bateria do seu celular morria lentamente sob a sombra das árvores."
)
PARAGRAFO = (
    "Apesar daquele revés temporário, a profissional não abandonou o campo de batalha "
    "nem desistiu de buscar novos recursos para o projeto solar. No fim da tarde, o "
    "documento atualizado foi enviado por ela ao diretor financeiro através de um "
    "mensageiro expresso, pois o tempo já estava se esgotando. Você realmente acredita "
    "que uma simples burocracia bancária seria capaz de frear alguém que construiu toda "
    "a carreira transformando crises em combustível?"
)


class PropositionGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.resultado = analisar_paragrafo(PARAGRAFO, CONTEXTO)

    def _prop(self, predicado: str):
        return next(item for item in self.resultado.proposicoes if item.predicado == predicado)

    def test_envio_registra_papeis_semanticos(self) -> None:
        envio = self._prop("enviar")
        papeis = {(item.papel, item.mencao) for item in envio.participantes}
        self.assertEqual(
            papeis,
            {
                ("paciente", "o documento atualizado"),
                ("agente", "ela"),
                ("destinatario", "diretor financeiro"),
                ("meio", "um mensageiro expresso"),
            },
        )

    def test_negacao_tem_escopo_exato(self) -> None:
        negativas = [item for item in self.resultado.operadores_escopo if item.tipo == "negacao"]
        self.assertEqual([(item.marcador.casefold(), item.escopo) for item in negativas], [("não", ["P1"]), ("nem", ["P2"])])
        self.assertEqual(self._prop("abandonar").polaridade, "negativa")
        self.assertEqual(self._prop("desistir").polaridade, "negativa")

    def test_modalidade_nao_contamina_informacao_de_fundo(self) -> None:
        modais = [item for item in self.resultado.operadores_escopo if item.tipo == "modalidade"]
        self.assertEqual(len(modais), 2)
        por_subtipo = {item.subtipo: item.escopo for item in modais}
        self.assertEqual(por_subtipo["irrealis_condicional"], ["P6", "P7"])
        self.assertEqual(por_subtipo["capacidade_dinamica"], ["P7"])
        self.assertIsNone(self._prop("acreditar").operadores.modalidade)
        self.assertIsNone(self._prop("construir").operadores.modalidade)
        self.assertIsNone(self._prop("transformar").operadores.modalidade)

    def test_atribuicao_separa_pergunta_e_pressuposicao(self) -> None:
        pergunta = next(item for item in self.resultado.quadros_atribuicao if item.modo == "pergunta")
        fundo = next(item for item in self.resultado.quadros_atribuicao if item.modo == "pressuposicao")
        self.assertEqual(pergunta.escopo, ["P5", "P6", "P7"])
        self.assertEqual(fundo.escopo, ["P8", "P9"])
        self.assertEqual(fundo.estado, "pressuposta")

    def test_fonte_da_citacao_resolve_primeira_pessoa(self) -> None:
        meu = next(item for item in self.resultado.mencoes if item.texto.casefold() == "meu")
        resolucao = next(item for item in self.resultado.resolucoes if item.mencao_id == meu.id)
        helena = next(item for item in self.resultado.referentes if item.rotulo == "Helena")
        self.assertEqual(resolucao.referente_id, helena.id)
        self.assertEqual(resolucao.estado, "resolvida")
        self.assertGreaterEqual(resolucao.confianca, 0.9)

    def test_relacoes_formam_grafo_esperado(self) -> None:
        tipos = {item.tipo for item in self.resultado.relacoes}
        self.assertEqual(len(self.resultado.relacoes), 7)
        self.assertEqual(
            tipos,
            {
                "coordenacao_negativa",
                "concessao",
                "justificativa_causal",
                "conteudo_atitudinal",
                "complemento_modal",
                "caracterizacao_referente",
                "modo_processo",
            },
        )

    def test_evidencias_de_operadores_e_relacoes_sao_exatas(self) -> None:
        itens = [*self.resultado.operadores_escopo, *self.resultado.relacoes]
        for item in itens:
            intervalo = item.evidencia.intervalo
            self.assertEqual(item.evidencia.texto, PARAGRAFO[intervalo.inicio:intervalo.fim])

    def test_alternativas_humanas_nao_incluem_objetos(self) -> None:
        engenheira = next(item for item in self.resultado.mencoes if item.texto.casefold() == "a engenheira")
        resolucao = next(item for item in self.resultado.resolucoes if item.mencao_id == engenheira.id)
        ids_objetos = {
            item.id for item in self.resultado.referentes
            if item.classe_semantica in {"objeto", "lugar", "evento", "desconhecida"}
        }
        self.assertFalse(ids_objetos & {item.referente_id for item in resolucao.alternativas})

    def test_fala_citada_tem_fonte_e_quadro_consistentes(self) -> None:
        resultado = analisar_paragrafo('"Helena assinou o contrato", afirmou Maria.')
        assinar = next(item for item in resultado.proposicoes if item.predicado == "assinar")
        afirmar = next(item for item in resultado.proposicoes if item.predicado == "afirmar")
        quadro_fala = next(
            item for item in resultado.quadros_atribuicao
            if item.id == assinar.atribuicao_id
        )
        quadro_relato = next(
            item for item in resultado.quadros_atribuicao
            if item.id == afirmar.atribuicao_id
        )
        self.assertEqual((quadro_fala.modo, quadro_fala.estado), ("fala_citada", "citada"))
        self.assertEqual((quadro_fala.fonte.tipo, quadro_fala.fonte.rotulo), ("referente", "Maria"))
        self.assertEqual((quadro_relato.modo, quadro_relato.estado), ("assercao_narrativa", "afirmada"))
        self.assertEqual(afirmar.participantes[0].mencao, "Maria")

    def test_vozes_ativa_e_passiva_preservam_papeis(self) -> None:
        ativa = analisar_paragrafo("Ana enviou o documento ao diretor.")
        papeis_ativos = {
            (item.papel, item.mencao)
            for item in ativa.proposicoes[0].participantes
        }
        self.assertEqual(
            papeis_ativos,
            {("agente", "Ana"), ("paciente", "o documento"), ("destinatario", "diretor")},
        )

        passiva = analisar_paragrafo("O contrato foi assinado por Ana.")
        papeis_passivos = {
            (item.papel, item.mencao)
            for item in passiva.proposicoes[0].participantes
        }
        self.assertEqual(
            papeis_passivos,
            {("paciente", "O contrato"), ("agente", "Ana")},
        )

    def test_descricao_relativa_nao_engole_oracao_principal(self) -> None:
        resultado = analisar_paragrafo("Alguém que construiu a carreira reagiu.")
        construir = next(item for item in resultado.proposicoes if item.predicado == "construir")
        reagir = next(item for item in resultado.proposicoes if item.predicado == "reagir")
        quadro_construir = next(item for item in resultado.quadros_atribuicao if item.id == construir.atribuicao_id)
        quadro_reagir = next(item for item in resultado.quadros_atribuicao if item.id == reagir.atribuicao_id)
        self.assertEqual(quadro_construir.estado, "pressuposta")
        self.assertEqual(quadro_reagir.estado, "afirmada")

    def test_possessivo_na_citacao_do_paragrafo_aponta_para_falante(self) -> None:
        resultado = analisar_paragrafo('"Meu contrato foi assinado", disse Ana.')
        meu = next(item for item in resultado.mencoes if item.texto.casefold() == "meu")
        ana = next(item for item in resultado.mencoes if item.texto == "Ana")
        resolucao_meu = next(item for item in resultado.resolucoes if item.mencao_id == meu.id)
        resolucao_ana = next(item for item in resultado.resolucoes if item.mencao_id == ana.id)
        self.assertEqual(resolucao_meu.referente_id, resolucao_ana.referente_id)
        self.assertEqual(resolucao_meu.estado, "resolvida")
        quadro = next(item for item in resultado.quadros_atribuicao if item.modo == "fala_citada")
        self.assertEqual(quadro.fonte.rotulo, "Ana")


if __name__ == "__main__":
    unittest.main()
