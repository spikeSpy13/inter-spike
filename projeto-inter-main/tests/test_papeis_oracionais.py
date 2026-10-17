import json
from pathlib import Path
import unittest

from interpretador.extractor import analisar_paragrafo
from interpretador.grafo.validator import validar_grafo
from interpretador.main import analisar_json
from interpretador.models import JsonAnalysisRequest


class PapeisOracionaisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(__file__).resolve().parents[1] / "fixtures/vetorizacao-19.json"
        documento = json.loads(path.read_bytes())
        cls.p1 = analisar_json(JsonAnalysisRequest(documento=documento, paragrafo_id="P1")).analise
        cls.p2 = analisar_json(JsonAnalysisRequest(documento=documento, paragrafo_id="P2")).analise

    def sujeito(self, analise, forma):
        prop = next(p for p in analise.proposicoes if p.forma_textual == forma)
        sujeitos = [p for p in prop.participantes if p.funcao_sintatica == "sujeito"]
        self.assertEqual(len(sujeitos), 1)
        self.assertEqual(prop.sujeito.estado, "identificado")
        self.assertEqual(prop.sujeito.mencao_id, sujeitos[0].mencao_id)
        return prop, sujeitos[0]

    def test_documento19_copo_nao_e_agente_de_acenar(self):
        prop, sujeito = self.sujeito(self.p1, "acenasse")
        self.assertEqual((sujeito.mencao, sujeito.papel), ("ele", "agente"))
        self.assertFalse(any(p.mencao == "um copo" for p in prop.participantes))
        self.assertTrue(prop.sujeito.razoes)
        self.assertTrue(prop.sujeito.evidencias)

    def test_documento19_folha_nao_e_agente_de_ler(self):
        for forma in ("leu", "demonstrar", "deu"):
            with self.subTest(forma=forma):
                _, sujeito = self.sujeito(self.p2, forma)
                self.assertEqual((sujeito.mencao, sujeito.papel), ("Ela", "agente"))

    def test_documento19_relatora_preserva_sujeito_e_fonte(self):
        _, sujeito = self.sujeito(self.p1, "disse")
        self.assertEqual(sujeito.mencao, "Ele")
        fala = next(q for q in self.p1.quadros_atribuicao if q.modo == "fala_citada")
        self.assertEqual(fala.fonte.rotulo, "meu pai")

    def test_texto_livre_coordena_sujeito_sem_promover_objeto(self):
        analise = analisar_paragrafo("Ele pegou um copo e acenou.")
        _, sujeito = self.sujeito(analise, "acenou")
        self.assertEqual(sujeito.mencao, "Ele")
        analise = analisar_paragrafo("Ela pegou a folha e leu.")
        _, sujeito = self.sujeito(analise, "leu")
        self.assertEqual(sujeito.mencao, "Ela")

    def test_novo_sujeito_explicito_prevalece_na_coordenacao(self):
        analise = analisar_paragrafo("Ana leu o livro e João escreveu o relatório.")
        _, sujeito = self.sujeito(analise, "escreveu")
        self.assertEqual(sujeito.mencao, "João")

    def test_tempo_composto_ativo_nao_vira_voz_passiva(self):
        for texto in ("Ana havia assinado o contrato.", "Ana tinha assinado o contrato."):
            with self.subTest(texto=texto):
                _, sujeito = self.sujeito(analisar_paragrafo(texto), "assinado")
                self.assertEqual((sujeito.mencao, sujeito.papel), ("Ana", "agente"))

    def test_passiva_compartilhada_preserva_paciente(self):
        analise = analisar_paragrafo("O contrato foi assinado e enviado por Ana.")
        for forma in ("assinado", "enviado"):
            with self.subTest(forma=forma):
                _, sujeito = self.sujeito(analise, forma)
                self.assertEqual((sujeito.mencao, sujeito.papel), ("O contrato", "paciente"))
        enviado = next(p for p in analise.proposicoes if p.forma_textual == "enviado")
        self.assertTrue(any(p.mencao == "Ana" and p.papel == "agente" and p.funcao_sintatica is None for p in enviado.participantes))

    def test_destinatario_nao_vaza_para_primeira_oracao(self):
        analise = analisar_paragrafo("Ana enviou o documento e Maria enviou a carta para João.")
        primeiro, segundo = analise.proposicoes
        self.assertFalse(any(p.mencao == "João" for p in primeiro.participantes))
        self.assertTrue(any(p.mencao == "João" and p.papel == "destinatario" for p in segundo.participantes))

    def test_sujeito_da_proxima_oracao_nao_vira_objeto_da_anterior(self):
        for texto in ("Ana enviou e João chegou.", "Ana abandonou e João saiu.", "Ana construiu e João reagiu."):
            with self.subTest(texto=texto):
                analise = analisar_paragrafo(texto)
                self.assertFalse(any(p.mencao == "João" for p in analise.proposicoes[0].participantes))
                self.assertTrue(any(p.mencao == "João" and p.funcao_sintatica == "sujeito" for p in analise.proposicoes[1].participantes))

    def test_estado_e_experiencia_nao_recebem_agente_padrao(self):
        _, estado = self.sujeito(analisar_paragrafo("Ana estava exausta."), "estava")
        _, experiencia = self.sujeito(analisar_paragrafo("Ana gostava da viagem."), "gostava")
        self.assertEqual(estado.papel, "tema")
        self.assertEqual(experiencia.papel, "experienciador")

    def test_objeto_presente_nao_oculta_sujeito_indeterminado(self):
        enviei = next(p for p in self.p2.proposicoes if p.forma_textual == "enviei")
        self.assertEqual(enviei.sujeito.estado, "indeterminado")
        self.assertFalse(any(p.funcao_sintatica == "sujeito" for p in enviei.participantes))
        self.assertTrue(any("sujeito indeterminado" in a for a in self.p2.alertas))

    def test_validador_rejeita_desacordo_entre_decisao_e_participante(self):
        analise = analisar_paragrafo("Ana enviou o documento.").model_copy(deep=True)
        prop = analise.proposicoes[0]
        prop.sujeito.mencao_id = next(m.id for m in analise.mencoes if m.texto == "o documento")
        with self.assertRaisesRegex(ValueError, "divergem"):
            validar_grafo(analise.paragrafo, analise.proposicoes, analise.mencoes, analise.referentes,
                          analise.operadores_escopo, analise.quadros_atribuicao, analise.relacoes)


if __name__ == "__main__":
    unittest.main()
