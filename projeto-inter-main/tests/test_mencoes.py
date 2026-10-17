import json
from pathlib import Path
import unittest
from unittest.mock import patch

from interpretador.linguistica import adaptar_anotacoes, analisar_texto
from interpretador.referencias.detector import detectar_mencoes


class MentionDetectorTests(unittest.TestCase):
    def test_intervalos_reproduzem_texto_exato(self) -> None:
        texto = "Helena enviou a proposta dela ao gerente do banco."
        mencoes = detectar_mencoes(texto)
        self.assertTrue(mencoes)
        for mencao in mencoes:
            self.assertEqual(
                mencao.texto,
                texto[mencao.intervalo.inicio:mencao.intervalo.fim],
            )

    def test_detecta_possessivo_aninhado(self) -> None:
        texto = "A engenheira revisou a proposta dela."
        mencoes = detectar_mencoes(texto)
        possessiva = next(m for m in mencoes if m.texto.casefold() == "dela")
        self.assertEqual(possessiva.tipo, "pronome_possessivo")
        self.assertIsNotNone(possessiva.mencao_pai_id)

    def test_detecta_descricao_complexa(self) -> None:
        texto = "A burocracia não frearia alguém que construiu toda a carreira."
        mencoes = detectar_mencoes(texto)
        complexas = [m for m in mencoes if m.tipo == "descricao_complexa"]
        self.assertEqual(len(complexas), 1)
        self.assertTrue(complexas[0].texto.startswith("alguém que"))

    def test_pronome_no_inicio_nao_vira_nome_proprio(self) -> None:
        mencoes = detectar_mencoes("Ela enviou a proposta ao gerente.")
        elas = [m for m in mencoes if m.texto == "Ela"]
        self.assertEqual(len(elas), 1)
        self.assertEqual(elas[0].tipo, "pronome_pessoal")
        self.assertTrue(any(m.texto.casefold() == "gerente" for m in mencoes))

    def test_estabiliza_limites_e_detecta_segunda_pessoa(self) -> None:
        texto = "O documento foi enviado ao diretor financeiro, pois o tempo já acabava. Você viu."
        mencoes = detectar_mencoes(texto)
        textos = {m.texto for m in mencoes}
        self.assertIn("diretor financeiro", textos)
        self.assertIn("o tempo", textos)
        self.assertNotIn("o tempo já", textos)
        voce = next(m for m in mencoes if m.texto == "Você")
        self.assertEqual(voce.tipo, "pronome_pessoal")

    def test_funcoes_e_verbos_capitalizados_nao_criam_pessoas(self) -> None:
        texto = (
            'Ainda havia tempo. Será que ele volta? Não saí. '
            'Fiquei atualizando os arquivos. Voltei à sala. '
            'Retornei ao trabalho. Parece que Helena chegou.'
        )
        nomes = {m.texto for m in detectar_mencoes(texto) if m.tipo == "nome_proprio"}
        self.assertEqual(nomes, {"Helena"})

    def test_descricao_nominal_termina_antes_do_predicado(self) -> None:
        mencoes = detectar_mencoes("O estranho é o silêncio.")
        descricoes = {m.texto for m in mencoes if m.tipo == "descricao_nominal"}
        self.assertIn("O estranho", descricoes)
        self.assertIn("o silêncio", descricoes)
        self.assertFalse(any("é" in texto.split() for texto in descricoes))

    def test_preserva_genitivo_e_possessivo_aninhado(self) -> None:
        texto = "A proposta de Helena chegou. A proposta dela fracassou."
        mencoes = detectar_mencoes(texto)
        self.assertTrue(any(m.texto == "A proposta de Helena" for m in mencoes))
        descricao = next(m for m in mencoes if m.texto == "A proposta dela")
        possessivo = next(m for m in mencoes if m.texto == "dela")
        self.assertEqual(possessivo.mencao_pai_id, descricao.id)

    def test_meu_pai_menciona_pessoa_distinta_do_possuidor(self) -> None:
        texto = "Meu pai chegou."
        mencoes = detectar_mencoes(texto)
        pai = next(m for m in mencoes if m.texto == "Meu pai")
        possuidor = next(m for m in mencoes if m.texto == "Meu")
        self.assertEqual(pai.tipo, "descricao_nominal")
        self.assertEqual(pai.caracteristicas.classe_semantica, "pessoa")
        self.assertEqual(pai.caracteristicas.genero, "masculino")
        self.assertEqual(pai.caracteristicas.numero, "singular")
        self.assertEqual(possuidor.tipo, "pronome_possessivo")
        self.assertEqual(possuidor.caracteristicas.genero, "indeterminado")
        self.assertEqual(possuidor.mencao_pai_id, pai.id)

    def test_genitivo_familiar_nao_transforma_casa_em_pessoa(self) -> None:
        mencoes = detectar_mencoes("A casa dos meus pais ficou vazia.")
        casa = next(m for m in mencoes if m.texto == "A casa dos meus pais")
        pais = next(m for m in mencoes if m.texto == "meus pais")
        self.assertNotEqual(casa.caracteristicas.classe_semantica, "pessoa")
        self.assertEqual(pais.caracteristicas.classe_semantica, "pessoa")
        self.assertEqual(pais.mencao_pai_id, casa.id)

    def test_reutiliza_base_linguistica_sem_reanalise_e_preserva_ids(self) -> None:
        texto = "Helena enviou a proposta dela."
        base = analisar_texto(texto)
        esperadas = detectar_mencoes(texto, inicio_id=20)
        with patch(
            "interpretador.referencias.detector.analisar_texto",
            side_effect=AssertionError("Não deve descartar a base fornecida."),
        ):
            mencoes = detectar_mencoes(texto, "paragrafo", 20, base)
        self.assertEqual(mencoes, esperadas)
        self.assertEqual(mencoes[0].id, "M20")

    def test_rejeita_base_de_outro_texto(self) -> None:
        with self.assertRaisesRegex(ValueError, "corresponder exatamente"):
            detectar_mencoes("Helena chegou.", base_linguistica=analisar_texto("Ana chegou."))

    def test_documento19_preserva_nominais_e_rejeita_falsos_nomes(self) -> None:
        arquivo = Path(__file__).resolve().parents[1] / "fixtures" / "vetorizacao-19.json"
        documento = json.loads(arquivo.read_bytes())
        analise = documento["contexto"]["regras"]["analise"]
        anotacao = analise["anotacao"]
        segmentacao = anotacao["segmentacao"]
        bases = adaptar_anotacoes(
            segmentacao["preparacao"]["original"]["texto"], segmentacao,
            anotacao["anotacoes_tokens"], analise["sintaxe"],
        )
        resultados = [detectar_mencoes(base.texto, base_linguistica=base) for base in bases.values()]
        falsos_nomes = {"Ainda", "Não", "Será", "Fiquei", "Voltei", "Retornei", "Parece"}
        for base, mencoes in zip(bases.values(), resultados):
            for mencao in mencoes:
                self.assertEqual(mencao.texto, base.texto[mencao.intervalo.inicio:mencao.intervalo.fim])
                if mencao.tipo == "nome_proprio":
                    self.assertNotIn(mencao.texto, falsos_nomes)
        pai = next(m for m in resultados[0] if m.texto == "meu pai")
        possuidor = next(m for m in resultados[0] if m.intervalo.inicio == pai.intervalo.inicio and m.texto == "meu")
        self.assertEqual(pai.caracteristicas.classe_semantica, "pessoa")
        self.assertEqual(possuidor.mencao_pai_id, pai.id)
        self.assertTrue(any(m.texto == "O estranho" for m in resultados[0]))
        self.assertTrue(any(m.texto == "Helena" and m.tipo == "nome_proprio" for m in resultados[1]))


if __name__ == "__main__":
    unittest.main()
