# Interpretador fundamentado

Aplicativo para receber a saída da etapa `09_vetorizacao` e produzir interpretações rastreáveis ao texto original.

O primeiro recorte do produto é deliberadamente pequeno: interpretar **um parágrafo**, propor sua ideia central e gerar uma síntese fiel com paráfrases opcionais, sempre acompanhadas de evidências e alertas de checagem.

## Estado atual

O projeto concluiu as cinco etapas do primeiro ciclo. A versão `1.0.0` recebe e valida a vetorização, interpreta um parágrafo, gera textos, checa sua fidelidade e expõe todo o fluxo pela API e pela interface. Cada resposta também registra a versão do motor, as estratégias e os parâmetros usados, a duração medida e os custos da execução. O motor e a API são escritos em Python; a interface funcional está em `dist/`. Os anexos originais foram preservados em:

- `fixtures/vetorizacao-28.json`: exemplo real de entrada;
- `docs/referencias/arquitetura_interpretacao_fundamentada_v1.pdf`: referência conceitual.

O plano e os critérios de aceite estão em [`docs/01-escopo-e-etapas.md`](docs/01-escopo-e-etapas.md).

## Interface atual

A página aceita o arquivo JSON de `09_vetorizacao`, valida sua estrutura e permite selecionar um parágrafo. O texto livre e o contexto anterior continuam disponíveis. A análise produz proposições, menções, grupos de referentes `R1/R2`, um grafo com operadores, quadros de atribuição e relações, além da ideia central proposta, da síntese extrativa e das paráfrases aplicáveis. A checagem mostra seu estado, os alvos verificados, eventuais achados e a limitação do método. O painel de execução identifica o motor e mostra duração, parâmetros, chamadas externas, tokens e custo estimado.

Esta versão continua sendo um extrator heurístico demonstrativo. Resoluções ambíguas ou sem antecedente permanecem explícitas; confiança não representa uma probabilidade calibrada.

### Base proposicional `0.4.0`

Os campos introduzidos nesse contrato permanecem na resposta atual de `POST /api/analisar`:

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
- `POST /api/analisar`: mantém o fluxo de texto livre e retorna o contrato de análise atual.

### Ideia central `0.6.0`

O contrato de análise `0.6.0` agrupa proposições apoiadas pelo mesmo trecho e pontua os grupos com sinais explícitos do registro: relações discursivas, atribuição, polaridade, posição e recorrência de participantes. A melhor hipótese fica em `ideia_central`; até duas leituras concorrentes permanecem em `alternativas`; `conteudo_essencial_ids` identifica as proposições que a próxima etapa deverá preservar.

A hipótese usa um trecho do original como formulação, e todas as evidências são validadas contra seus intervalos. A pontuação é heurística e não representa probabilidade calibrada nem certificação de correção.

### Síntese extrativa `0.7.0`

O contrato de análise `0.7.0` gera `sintese` a partir dos IDs de conteúdo essencial. A estratégia `extrativa_conteudo_essencial_v1` seleciona períodos completos do texto original que cobrem as proposições essenciais e as evidências de seus operadores e relações. O resultado declara a cobertura em `proposicao_ids`, `operador_ids`, `relacao_ids` e `mencao_ids`; o validador rejeita intervalos divergentes, texto acrescentado e perda dos elementos essenciais.

Quando não há conteúdo essencial, a síntese fica `indeterminada`. Períodos não contíguos, contexto adicional e baixa confiança da ideia central geram alertas para revisão.

### Paráfrases verificáveis `0.8.0`

O contrato de análise `0.8.0` preenche `parafrases` somente quando uma equivalência discursiva aprovada se aplica a um marcador confirmado pelo grafo. A estratégia `substituicao_discursiva_controlada_v1` cobre coordenação negativa (`nem` → `e também não`) e justificativa causal (`pois` ↔ `porque`). Cada saída declara o trecho substituído, o novo marcador, os operadores e relações preservados, a cobertura herdada da síntese e sua confiança.

O validador reconstrói a paráfrase a partir do original e das transformações declaradas. Ele rejeita equivalências desconhecidas, texto adicional, transformações sobre predicados ou participantes e qualquer perda de cobertura. Quando nenhuma regra segura é aplicável, `parafrases` fica vazia; isso evita forçar uma reformulação sem suporte do contrato atual.

### Checagem de fidelidade `0.9.0`

O contrato de análise `0.9.0` acrescenta `checagem`, com os estados `sem_alertas_detectados`, `revisao_necessaria` e `indeterminada`. O método `cobertura_estrutural_v1` confere evidências, texto reconstruível, proposições, operadores, relações, participantes e transformações de cada saída. Cada achado registra um código estável, o alvo, uma mensagem e os IDs afetados.

Afirmações acrescentadas, cobertura removida, evidências divergentes e transformações desconhecidas produzem alertas. O estado `sem_alertas_detectados` significa apenas que as regras atuais não encontraram essas falhas; o próprio contrato declara que a checagem não certifica equivalência semântica geral.

### Primeiro ciclo `1.0.0`

O contrato de análise `1.0.0` acrescenta `execucao`. Esse registro informa `versao_motor`, `duracao_ms`, os parâmetros das estratégias de centralidade, síntese, paráfrase e checagem, e se o contexto anterior foi usado. O bloco `custos` separa chamadas externas, tokens de entrada e saída e custo estimado em dólares.

O motor atual é heurístico e local. Por isso, cada análise informa zero chamadas externas, zero tokens externos e custo estimado `USD 0.000000`; a duração em milissegundos é medida para cada execução. A interface apresenta esses mesmos dados e permite inspecionar todos os parâmetros utilizados.

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

