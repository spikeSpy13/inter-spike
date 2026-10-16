# Interpretador fundamentado

Aplicativo para receber a saída da etapa `09_vetorizacao` e produzir interpretações rastreáveis ao texto original.

O primeiro recorte do produto é deliberadamente pequeno: interpretar **um parágrafo**, propor sua ideia central e gerar uma síntese fiel, sempre acompanhadas de evidências e alertas de checagem.

## Estado atual

O projeto está na **Etapa 3 — grafo proposicional e escopo**. O motor e a API são escritos em Python; a interface funcional está em `dist/`. Os anexos originais foram preservados em:

- `fixtures/vetorizacao-28.json`: exemplo real de entrada;
- `docs/referencias/arquitetura_interpretacao_fundamentada_v1.pdf`: referência conceitual.

O plano e os critérios de aceite estão em [`docs/01-escopo-e-etapas.md`](docs/01-escopo-e-etapas.md).

## Interface atual

A página recebe um parágrafo principal, um contexto anterior opcional e chama a API Python local. Ela produz proposições, menções, grupos de referentes `R1/R2` e um grafo com operadores, quadros de atribuição e relações. Cada decisão mostra confiança, razões, alternativas e evidências. Possessivos registram uma relação de possuidor, sem confundir o possuidor com o objeto possuído. Os participantes recebem papéis semânticos como agente, paciente, destinatário e meio.

Esta versão continua sendo um extrator heurístico demonstrativo. Resoluções ambíguas ou sem antecedente permanecem explícitas; confiança não representa uma probabilidade calibrada.

### Contrato `0.4.0`

A resposta de `POST /api/analisar` inclui:

- `mencoes`: ocorrências com intervalos exatos;
- `referentes`: agrupamentos de menções;
- `resolucoes`: decisão, tipo de relação, razões, alternativas e evidências;
- `proposicoes[].participantes[]`: papéis semânticos vinculados a menções e referentes;
- `operadores_escopo`: negação e modalidade com marcador e proposições afetadas;
- `quadros_atribuicao`: fonte, modo, estado e conteúdo atribuído;
- `relacoes`: arestas explicáveis entre proposições e referentes.

## Baixar e executar

Depois de clonar o repositório, entre na pasta do projeto e execute:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e .
uvicorn interpretador.main:app --reload
```

Abra `http://127.0.0.1:8000`. A documentação da API fica em `http://127.0.0.1:8000/docs`.

## Testar

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

No PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

## Princípio de arquitetura

A interpretação não será inferida dos números do embedding isoladamente. O aplicativo usará o texto original, a análise estrutural e os vínculos presentes no JSON como fonte primária; os vetores servirão como sinal auxiliar para recuperação, associação e priorização. Toda afirmação relevante deverá apontar para trechos do original.

