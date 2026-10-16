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

### Etapa 1 — receber e validar

- carregar o JSON sem perder o original;
- confirmar versão, etapa, estado de validação e campos obrigatórios;
- conferir referências entre parágrafos, períodos, unidades, representações e artefatos;
- validar dimensão, finitude e normalização dos vetores;
- criar uma visão interna enxuta para as etapas seguintes;
- produzir erros legíveis quando a entrada for incompatível.

Critério de aceite: a fixture fornecida é aceita; cópias com referência quebrada, vetor de dimensão incorreta ou intervalo inválido são rejeitadas com indicação precisa do problema.

### Etapa 2 — interpretar um parágrafo

- extrair proposições e participantes; **implementado**
- detectar menções e seus intervalos no parágrafo e no contexto anterior; **implementado**
- registrar referentes e alternativas de resolução; **implementado — contrato 0.3.0**
- representar negação, possibilidade, atribuição e relações entre proposições; **implementado — contrato 0.4.0**
- propor a ideia central com evidências e alternativas;
- marcar IDs do conteúdo considerado essencial.

Critério de aceite: cada proposição e cada hipótese relevante aponta para um ou mais intervalos válidos do texto original.

#### Resolução referencial implementada

O motor gera candidatos textualmente anteriores, aplica restrições de classe semântica, gênero, número, encaixamento e papel humano, e calcula uma pontuação explicável. As decisões podem ficar `resolvida`, `ambigua`, `nao_resolvida` ou introduzir um `novo_referente`. Possessivos usam a relação `possuidor`; as demais retomadas usam `identidade`.

Referentes e decisões são validados para impedir IDs inexistentes, uma menção em dois grupos ou evidências divergentes dos intervalos originais. Os limiares atuais são heurísticos e deverão ser calibrados com um conjunto anotado.

#### Grafo proposicional implementado

O contrato `0.4.0` acrescenta papéis semânticos dos participantes, operadores com escopo explícito, quadros de atribuição e relações tipadas. A proximidade deixa de ser suficiente para propagar modalidade ou estado enunciativo: no exemplo de referência, `seria` afeta `P6/P7`, `capaz de` afeta `P7` e as relativas `P8/P9` ficam registradas como informação pressuposta.

As relações e os operadores apontam para intervalos exatos do parágrafo. O validador rejeita escopos inexistentes, extremidades quebradas, proposições sem quadro de atribuição e evidências que não reproduzam o texto original.

### Etapa 3 — gerar textos

- gerar uma síntese a partir do registro interpretativo;
- oferecer paráfrases opcionais como saídas independentes;
- consultar o original durante a geração.

Critério de aceite: síntese e paráfrases preservam negação, modalidade, participantes e relações essenciais selecionadas.

### Etapa 4 — checar fidelidade

- procurar afirmações sem apoio;
- verificar perda de conteúdo essencial;
- devolver alertas explicáveis e um estado de checagem;
- nunca converter “sem alertas detectados” em certificado de correção.

Critério de aceite: alterações controladas que introduzam uma afirmação nova ou removam uma relação essencial geram alertas.

### Etapa 5 — expor o aplicativo

- encapsular o fluxo em uma API Python;
- adicionar interface para envio do JSON e inspeção do resultado;
- mostrar evidências junto de cada interpretação;
- registrar versão do motor, parâmetros, duração e custos.

## Contrato preliminar de saída

O formato será fechado após a Etapa 1, mas deverá conter pelo menos:

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
    "estado": "nao_executada"
  }
}
```

Cada evidência deverá usar as mesmas coordenadas da entrada: base zero, início inclusivo, fim exclusivo e unidade em pontos de código Unicode.

## Fora do primeiro ciclo

- interpretar documentos longos de uma só vez;
- treinar ou recalcular embeddings;
- certificar semanticamente uma interpretação;
- substituir revisão humana na validação empírica.
