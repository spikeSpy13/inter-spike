# Escopo e etapas

## Objetivo do primeiro ciclo

Receber um JSON da etapa `09_vetorizacao`, selecionar um parágrafo e devolver:

1. um registro interpretativo estruturado;
2. uma ideia central proposta;
3. uma síntese fiel;
4. as evidências no texto original;
5. alertas e o estado da checagem.

Paráfrases ficam opcionais. O sistema deve tratar interpretações e ideias centrais como hipóteses revisáveis, não como verdades certificadas.

## O que existe na amostra

A fixture `vetorizacao-28.json` está íntegra e declara `schema_version: 1.0.0`, `etapa: 09_vetorizacao` e validação concluída. Ela contém:

- o texto original completo, com 996 pontos de código Unicode;
- 2 parágrafos, 6 períodos e 170 tokens;
- morfologia, sintaxe, entidades, regras linguísticas e 6 janelas de contexto;
- 9 representações: 2 de parágrafo, 6 contextuais e 1 do documento;
- 7 artefatos vetoriais normalizados, de 1.024 dimensões, gerados com `intfloat/multilingual-e5-large`;
- intervalos com início inclusivo e fim exclusivo.

Algumas representações compartilham o mesmo artefato quando o recorte textual é idêntico. Portanto, o vínculo deve ser resolvido por `artefato_id`, e não pela posição nos arrays.

## Sequência de implementação

O protótipo foi desenvolvido primeiro pelo fluxo de texto colado. A estabilização `0.4.1` consolidou o grafo proposicional; a versão `0.5.0` ligou a ingestão estruturada à fixture `09_vetorizacao`; a versão `0.6.0` completou a seleção explicável da ideia central e do conteúdo essencial; a versão `0.7.0` passou a gerar uma síntese extrativa; a versão `0.8.0` acrescentou paráfrases opcionais; e a versão `0.9.0` implementou a checagem explicável de fidelidade.

### Etapa 1 — receber e validar

**Implementada — contrato de ingestão `0.5.0`.**

- carregar o JSON sem perder o original;
- confirmar versão, etapa, estado de validação e campos obrigatórios;
- conferir referências entre parágrafos, períodos, unidades, representações e artefatos;
- validar dimensão, finitude e normalização dos vetores;
- criar uma visão interna enxuta para as etapas seguintes;
- produzir erros legíveis quando a entrada for incompatível.

Critério de aceite: a fixture fornecida é aceita; cópias com referência quebrada, vetor de dimensão incorreta ou intervalo inválido são rejeitadas com indicação precisa do problema. **Atendido por testes automatizados.**

### Etapa 2 — interpretar um parágrafo

**Implementada — contrato de análise `0.6.0`.**

- extrair proposições e participantes; **implementado**
- detectar menções e seus intervalos no parágrafo e no contexto anterior; **implementado**
- registrar referentes e alternativas de resolução; **implementado — contrato 0.3.0**
- representar negação, possibilidade, atribuição e relações entre proposições; **implementado — contrato 0.4.0**
- propor a ideia central com evidências e alternativas; **implementado — contrato 0.6.0**
- marcar IDs do conteúdo considerado essencial. **implementado — contrato 0.6.0**

Critério de aceite: cada proposição e cada hipótese relevante aponta para um ou mais intervalos válidos do texto original. **Atendido por testes automatizados.**

#### Ideia central e conteúdo essencial

O seletor `heuristica_explicavel_v1` agrupa proposições que compartilham o mesmo trecho de evidência. A pontuação considera relações discursivas, estado de atribuição, polaridade, posição e recorrência de participantes. A hipótese principal preserva até duas alternativas, registra suas razões e mantém a formulação como recorte do original. Pontuação e confiança ordenam hipóteses para revisão; não são probabilidades calibradas.

#### Resolução referencial implementada

O motor gera candidatos textualmente anteriores, aplica restrições de classe semântica, gênero, número, encaixamento e papel humano, e calcula uma pontuação explicável. As decisões podem ficar `resolvida`, `ambigua`, `nao_resolvida` ou introduzir um `novo_referente`. Possessivos usam a relação `possuidor`; as demais retomadas usam `identidade`.

Referentes e decisões são validados para impedir IDs inexistentes, uma menção em dois grupos ou evidências divergentes dos intervalos originais. Os limiares atuais são heurísticos e deverão ser calibrados com um conjunto anotado.

#### Grafo proposicional implementado

O contrato `0.4.0` acrescenta papéis semânticos dos participantes, operadores com escopo explícito, quadros de atribuição e relações tipadas. A proximidade deixa de ser suficiente para propagar modalidade ou estado enunciativo: no exemplo de referência, `seria` afeta `P6/P7`, `capaz de` afeta `P7` e as relativas `P8/P9` ficam registradas como informação pressuposta.

As relações e os operadores apontam para intervalos exatos do parágrafo. O validador rejeita escopos inexistentes, extremidades quebradas, proposições sem quadro de atribuição e evidências que não reproduzam o texto original.

### Etapa 3 — gerar textos

**Implementada — contrato de análise `0.8.0`.**

- gerar uma síntese a partir do registro interpretativo; **implementado — contrato 0.7.0**
- oferecer paráfrases opcionais como saídas independentes; **implementado — contrato 0.8.0**
- consultar o original durante a geração. **implementado — contrato 0.7.0**

Critério de aceite: síntese e paráfrases preservam negação, modalidade, participantes e relações essenciais selecionadas. **Atendido por testes automatizados para a síntese e para as equivalências de paráfrase suportadas.**

#### Síntese extrativa implementada

A estratégia `extrativa_conteudo_essencial_v1` seleciona períodos completos do original que contêm as proposições essenciais. Ela também exige cobertura das evidências de operadores e relações ligados a essas proposições e dos intervalos dos participantes. O contrato registra os IDs cobertos, os intervalos literais, a confiança herdada da ideia central e alertas de revisão. O validador rejeita texto sem apoio ou perda de qualquer elemento declarado como essencial.

#### Paráfrases controladas implementadas

A estratégia `substituicao_discursiva_controlada_v1` só produz uma saída quando o grafo confirma uma equivalência suportada: coordenação negativa (`nem` → `e também não`) ou justificativa causal (`pois` ↔ `porque`). A paráfrase herda toda a cobertura da síntese e registra cada transformação com seu intervalo original e os IDs semânticos preservados. O validador reconstrói a saída, impede alterações em participantes e predicados e rejeita texto não declarado. A ausência de uma regra segura resulta em uma lista vazia, conforme o caráter opcional desta saída.

### Etapa 4 — checar fidelidade

**Implementada — contrato de análise `0.9.0`.**

- procurar afirmações sem apoio; **implementado**
- verificar perda de conteúdo essencial; **implementado**
- devolver alertas explicáveis e um estado de checagem; **implementado**
- nunca converter “sem alertas detectados” em certificado de correção. **implementado**

Critério de aceite: alterações controladas que introduzam uma afirmação nova ou removam uma relação essencial geram alertas. **Atendido por testes automatizados.**

#### Checagem estrutural implementada

O método `cobertura_estrutural_v1` verifica a síntese e cada paráfrase. Ele compara o texto reconstruível, as evidências e a cobertura declarada com proposições, operadores, relações e participantes essenciais. Também reaplica o validador de transformações das paráfrases. Os achados identificam o alvo, o código da falha e os IDs afetados; os estados possíveis são `sem_alertas_detectados`, `revisao_necessaria` e `indeterminada`.

O contrato inclui explicitamente a limitação de que essa checagem não certifica equivalência semântica geral. Uma saída sem alertas detectados continua sujeita à revisão humana e à ampliação futura das regras.

### Etapa 5 — expor o aplicativo

- encapsular o fluxo em uma API Python;
- adicionar interface para envio do JSON e inspeção do resultado;
- mostrar evidências junto de cada interpretação;
- registrar versão do motor, parâmetros, duração e custos.

## Contrato preliminar de saída

O contrato de ingestão foi fechado em `0.5.0`. A saída completa das etapas seguintes deverá conter pelo menos:

```json
{
  "fonte": {
    "documento_id": 28,
    "paragrafo_id": "P1"
  },
  "registro": {
    "proposicoes": [],
    "referentes": [],
    "relacoes": [],
    "ideia_central": {},
    "conteudo_essencial_ids": []
  },
  "sintese": {},
  "parafrases": [],
  "evidencias": [],
  "alertas": [],
  "checagem": {
    "estado": "sem_alertas_detectados",
    "achados": [],
    "limitacoes": []
  }
}
```

Cada evidência deverá usar as mesmas coordenadas da entrada: base zero, início inclusivo, fim exclusivo e unidade em pontos de código Unicode.

## Fora do primeiro ciclo

- interpretar documentos longos de uma só vez;
- treinar ou recalcular embeddings;
- certificar semanticamente uma interpretação;
- substituir revisão humana na validação empírica.
