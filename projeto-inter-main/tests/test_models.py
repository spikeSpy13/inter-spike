import unittest

from pydantic import ValidationError

from interpretador.models import AnalysisRequest, Span


class ModelValidationTests(unittest.TestCase):
    def test_intervalo_exige_fim_posterior_ao_inicio(self) -> None:
        with self.assertRaises(ValidationError):
            Span(inicio=10, fim=2)
        with self.assertRaises(ValidationError):
            Span(inicio=4, fim=4)

    def test_entrada_preserva_espacos_do_original(self) -> None:
        entrada = AnalysisRequest(
            paragrafo="  Maria leu o livro.  ",
            contexto_anterior="  Helena chegou.  ",
        )
        self.assertEqual(entrada.paragrafo, "  Maria leu o livro.  ")
        self.assertEqual(entrada.contexto_anterior, "  Helena chegou.  ")

    def test_contexto_somente_com_espacos_vira_nulo(self) -> None:
        entrada = AnalysisRequest(paragrafo="Texto válido.", contexto_anterior="   ")
        self.assertIsNone(entrada.contexto_anterior)


if __name__ == "__main__":
    unittest.main()
