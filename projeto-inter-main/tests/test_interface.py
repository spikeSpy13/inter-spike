import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InterfaceContractTests(unittest.TestCase):
    def test_estado_oculto_tem_regra_forte(self) -> None:
        css = (ROOT / "dist" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("[hidden] { display: none !important; }", css)

    def test_interface_expoe_grafo_e_etapa_atual(self) -> None:
        html = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")
        javascript = (ROOT / "dist" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="graph-map"', html)
        self.assertIn("Protótipo · etapa 3", html)
        self.assertIn("function renderGraph(data)", javascript)
        self.assertIn("data.operadores_escopo", javascript)
        self.assertIn("data.quadros_atribuicao", javascript)
        self.assertIn("data.relacoes", javascript)


if __name__ == "__main__":
    unittest.main()
