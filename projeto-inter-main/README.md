# Interpretador fundamentado

Aplicativo para receber a saída da etapa `09_vetorizacao` e produzir interpretações rastreáveis ao texto original.

O primeiro recorte do produto é deliberadamente pequeno: interpretar **um parágrafo**, propor sua ideia central e gerar uma síntese fiel, sempre acompanhadas de evidências e alertas de checagem.

## Estado atual

O projeto concluiu a **Etapa 1 — ingestão e validação** e continua na **Etapa 2 — interpretação de um parágrafo**. A versão `0.5.0` recebe diretamente o JSON de `09_vetorizacao`, oferece os parágrafos válidos para seleção e executa sobre eles o grafo proposicional estabilizado em `0.4.1`. O motor e a API são escritos em Python; a interface funcional está em `dist/`. Os anexos originais foram preservados em:

- `fixtures/vetorizacao-28.json`: exemplo real de entrada;
- `docs/referencias/arquitetura_interpretacao_fundamentada_v1.pdf`: referência conceitual.

O plano e os critérios de aceite estão em [`docs/01-escopo-e-etapas.md`](docs/01-escopo-e-etapas.md).

## Interface atual

A página aceita o arquivo JSON de `09_vetorizacao`, valida sua estrutura e permite selecionar um parágrafo. O texto livre e o contexto anterior continuam disponíveis. A análise produz proposições, menções, grupos de referentes `R1/R2` e um grafo com operadores, quadros de atribuição e relações. Cada decisão mostra confiança, razões, alternativas e evidências. Possessivos registram uma relação de possuidor, sem confundir o possuidor com o objeto possuído. Os participantes recebem papéis semânticos como agente, paciente, destinatário e meio.

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

### Estabilização `0.4.1`

A versão do aplicativo `0.4.1` mantém o contrato de resposta `0.4.0` e corrige escopo de negação em coordenações, quadros de fala citada, papéis em voz ativa e passiva, modalidade com verbos auxiliares e validação dos intervalos. A interface passou a mostrar alertas, evidências, confiança e a versão do contrato. A suíte inclui testes HTTP reais e casos de regressão além do parágrafo de referência.

### Ingestão `0.5.0`

O contrato de ingestão `0.5.0` valida `schema_version`, etapa e estado da origem; preserva o texto original; confere intervalos em pontos de código Unicode; verifica vínculos entre parágrafos, períodos, tokens, unidades, representações e artefatos; e rejeita vetores com dimensão, finitude ou norma L2 incompatíveis. Os erros retornam código, caminho JSON e mensagem legível.

- `POST /api/documentos/validar`: valida o documento e lista os parágrafos disponíveis;
- `POST /api/analisar-json`: valida novamente a origem e analisa o parágrafo selecionado;
- `POST /api/analisar`: mantém o fluxo de texto livre do contrato `0.4.0`.

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

