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
        self.assertIn("Protótipo · paráfrases verificáveis · v0.8.0", html)
        self.assertIn('id="json-file"', html)
        self.assertIn('id="json-paragraph"', html)
        self.assertIn('fetch("/api/documentos/validar"', javascript)
        self.assertIn('"/api/analisar-json"', javascript)
        self.assertIn("function renderGraph(data)", javascript)
        self.assertIn("data.operadores_escopo", javascript)
        self.assertIn("data.quadros_atribuicao", javascript)
        self.assertIn("data.relacoes", javascript)
        self.assertIn('id="analysis-alerts"', html)
        self.assertIn('id="central-idea"', html)
        self.assertIn("function renderCentralIdea(idea, essentialIds)", javascript)
        self.assertIn("data.conteudo_essencial_ids", javascript)
        self.assertIn('id="synthesis"', html)
        self.assertIn("function renderSynthesis(item, paraphrases)", javascript)
        self.assertIn("renderSynthesis(data.sintese, data.parafrases)", javascript)
        self.assertIn('class="paraphrase-card"', javascript)
        self.assertIn("paraphrase.transformacoes", javascript)
        self.assertIn("renderAlerts(data.alertas)", javascript)
        self.assertIn("AbortController", javascript)
        self.assertIn('data.schema_version !== "0.8.0"', javascript)


if __name__ == "__main__":
    unittest.main()
