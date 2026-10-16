import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import URLError
from urllib.request import Request, urlopen

from interpretador.main import app, health
from interpretador.models import AnalysisRequest
from interpretador.main import analisar


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with socket.socket() as servidor:
            servidor.bind(("127.0.0.1", 0))
            cls.porta = servidor.getsockname()[1]
        raiz = Path(__file__).resolve().parents[1]
        ambiente = os.environ.copy()
        ambiente["PYTHONPATH"] = str(raiz / "src")
        ambiente["PYTHONDONTWRITEBYTECODE"] = "1"
        cls.processo = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "interpretador.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.porta),
            ],
            cwd=raiz,
            env=ambiente,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        limite = time.monotonic() + 8
        while time.monotonic() < limite:
            if cls.processo.poll() is not None:
                saida = cls.processo.stdout.read() if cls.processo.stdout else ""
                raise RuntimeError(f"Servidor de teste encerrou antes de iniciar:\n{saida}")
            try:
                with urlopen(f"http://127.0.0.1:{cls.porta}/health", timeout=0.3) as resposta:
                    if resposta.status == 200:
                        return
            except URLError:
                time.sleep(0.05)
        raise RuntimeError("Servidor de teste não ficou pronto no tempo esperado.")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.processo.terminate()
        try:
            cls.processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.processo.kill()
            cls.processo.wait(timeout=5)

    def requisitar(self, caminho: str, payload: dict | None = None):
        dados = json.dumps(payload).encode() if payload is not None else None
        requisicao = Request(
            f"http://127.0.0.1:{self.porta}{caminho}",
            data=dados,
            headers={"Content-Type": "application/json"} if dados else {},
        )
        return urlopen(requisicao, timeout=3)

    def test_health(self) -> None:
        self.assertEqual(health(), {"status": "ok"})

    def test_endpoint_de_analise(self) -> None:
        resultado = analisar(AnalysisRequest(paragrafo="Helena percebeu o problema."))
        self.assertEqual(resultado.schema_version, "0.6.0")
        self.assertGreaterEqual(resultado.resumo.proposicoes, 1)
        self.assertGreaterEqual(resultado.resumo.referentes, 1)
        self.assertIsInstance(resultado.operadores_escopo, list)
        self.assertIsInstance(resultado.quadros_atribuicao, list)
        self.assertIsInstance(resultado.relacoes, list)
        self.assertEqual(resultado.ideia_central.estado, "proposta")
        self.assertTrue(resultado.conteudo_essencial_ids)

    def test_rotas_publicadas_no_openapi(self) -> None:
        caminhos = app.openapi()["paths"]
        self.assertIn("/health", caminhos)
        self.assertIn("/api/analisar", caminhos)
        self.assertIn("/api/documentos/validar", caminhos)
        self.assertIn("/api/analisar-json", caminhos)

    def test_fluxo_http_serializa_o_contrato(self) -> None:
        with self.requisitar(
            "/api/analisar",
            {"paragrafo": "Helena percebeu o problema."},
        ) as resposta:
            self.assertEqual(resposta.status, 200)
            payload = json.load(resposta)
        self.assertEqual(payload["schema_version"], "0.6.0")
        self.assertGreaterEqual(payload["resumo"]["proposicoes"], 1)
        self.assertIn("ideia_central", payload)
        self.assertIn("conteudo_essencial_ids", payload)

    def test_http_rejeita_paragrafo_vazio(self) -> None:
        with self.assertRaises(URLError) as erro:
            self.requisitar("/api/analisar", {"paragrafo": "   "})
        self.assertEqual(erro.exception.code, 422)

    def test_http_rejeita_json_incompativel_com_erro_legivel(self) -> None:
        with self.assertRaises(URLError) as erro:
            self.requisitar("/api/documentos/validar", {"schema_version": "2.0.0"})
        self.assertEqual(erro.exception.code, 422)
        payload = json.loads(erro.exception.read())
        self.assertIn("codigo", payload["detail"][0])
        self.assertIn("caminho", payload["detail"][0])
        self.assertIn("mensagem", payload["detail"][0])

    def test_fluxo_http_aceita_fixture_vetorizada_real(self) -> None:
        raiz = Path(__file__).resolve().parents[1]
        documento = json.loads((raiz / "fixtures" / "vetorizacao-28.json").read_text())
        with self.requisitar("/api/documentos/validar", documento) as resposta:
            self.assertEqual(resposta.status, 200)
            payload = json.load(resposta)
        self.assertEqual(payload["schema_version"], "0.5.0")
        self.assertEqual(payload["fonte"]["documento_id"], 28)
        self.assertEqual([item["rotulo"] for item in payload["paragrafos"]], ["P1", "P2"])

    def test_fluxo_http_analisa_paragrafo_selecionado_do_json(self) -> None:
        raiz = Path(__file__).resolve().parents[1]
        documento = json.loads((raiz / "fixtures" / "vetorizacao-28.json").read_text())
        with self.requisitar(
            "/api/analisar-json",
            {"documento": documento, "paragrafo_id": "P2"},
        ) as resposta:
            self.assertEqual(resposta.status, 200)
            payload = json.load(resposta)
        self.assertEqual(payload["schema_version"], "0.6.0")
        self.assertEqual(payload["paragrafo"]["rotulo"], "P2")
        self.assertEqual(payload["analise"]["schema_version"], "0.6.0")
        self.assertGreater(payload["analise"]["resumo"]["proposicoes"], 0)

    def test_interface_e_arquivos_estaticos_sao_servidos(self) -> None:
        with self.requisitar("/") as resposta:
            self.assertEqual(resposta.status, 200)
            pagina = resposta.read().decode()
        with self.requisitar("/static/app.js") as resposta:
            self.assertEqual(resposta.status, 200)
            script = resposta.read().decode()
        self.assertIn("Interpretador de Proposições", pagina)
        self.assertIn("function renderAnalysis()", script)


if __name__ == "__main__":
    unittest.main()

