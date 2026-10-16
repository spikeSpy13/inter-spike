import unittest

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


if __name__ == "__main__":
    unittest.main()
