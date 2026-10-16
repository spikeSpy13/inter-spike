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
        self.assertIn("Protótipo · etapas 1–2 · v0.5.0", html)
        self.assertIn('id="json-file"', html)
        self.assertIn('id="json-paragraph"', html)
        self.assertIn('fetch("/api/documentos/validar"', javascript)
        self.assertIn('"/api/analisar-json"', javascript)
        self.assertIn("function renderGraph(data)", javascript)
        self.assertIn("data.operadores_escopo", javascript)
        self.assertIn("data.quadros_atribuicao", javascript)
        self.assertIn("data.relacoes", javascript)
        self.assertIn('id="analysis-alerts"', html)
        self.assertIn("renderAlerts(data.alertas)", javascript)
        self.assertIn("AbortController", javascript)
        self.assertIn('data.schema_version !== "0.4.0"', javascript)


if __name__ == "__main__":
    unittest.main()
