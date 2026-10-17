# Documento 19 — linha de base para a revisão 1.1.0

Registro de 17/10/2026. Motor executado: `1.0.0`, commit `ac47662b9014da1974bd47cf015f4fe55f5abbd5`.

Este documento registra resultados observados e expectativas iniciais de revisão técnica. As respostas salvas contêm erros conhecidos e não constituem um gabarito de correção linguística. A anotação do corpus e sua revisão humana continuam previstas no [plano da versão 1.1.0](02-plano-revisao-1.1.0.md).

## Entrada e reprodução

- Arquivo original preservado: [`fixtures/vetorizacao-19.json`](../fixtures/vetorizacao-19.json), 3.811.685 bytes.
- SHA-256: `cf4f74b418c5028f1c2b6688d06ae7f5eda0aa38a9ce1918082efc38d2d2dd2b`.
- Respostas completas dos dois parágrafos e resultado da ingestão: [`documento-19-baseline-v1.0.0.json`](../fixtures/revisao-1.1.0/documento-19-baseline-v1.0.0.json).
- Ingestão aceita pelo validador atual: schema da fonte `1.0.0`, etapa `09_vetorizacao`, 1.802 pontos de código Unicode, dois parágrafos, 16 períodos, 359 tokens, 19 representações e 19 artefatos de 1.024 dimensões.

P1 ocupa `[0, 885)`; P2 ocupa `[889, 1802)`. Entre eles há `\r\n\r\n`. A entrada foi copiada sem normalizar as quebras de linha. A conversão entre intervalo local de P2 e intervalo global soma 889 ao início e ao fim.

O P1 reproduziu as contagens, a ideia central, a pontuação e a síntese apresentados no PDF. Duração é uma medição variável e está explicitamente excluída da comparação determinística; os 19,588 ms do PDF não são uma meta de desempenho.

## Resultados do motor atual

| Medida | P1 | P2, com P1 como contexto |
|---|---:|---:|
| Caracteres do parágrafo | 885 | 913 |
| Proposições | 11 | 1 |
| Menções no parágrafo | 28 | 34 |
| Menções no contexto | 0 | 28 |
| Referentes no resultado completo | 14 | 38 |
| Resoluções aceitas, incluindo contexto | 2 | 5 |
| Menções não resolvidas, incluindo contexto | 12 | 19 |
| Operadores | 4 | 0 |
| Relações | 0 | 0 |
| Caracteres da síntese | 109 | 102 |
| Pontuação exibida da ideia central | 0,63 | 0,90 |
| Achados de fidelidade estrutural | 0 | 0 |

Em P2, o resumo inclui menções e resoluções do contexto anterior: das 19 pendências, 12 pertencem a P1 e sete a P2. Das cinco resoluções aceitas, duas são do contexto e três do parágrafo atual. Esses totais não medem precisão.

As duas resoluções de P1 são defeituosas: `dele [550, 554)` foi ligado a “Ainda”; `dele [790, 794)` foi ligado a “Não”. Em P2, o único predicado reconhecido é `leu → ler [574, 577)`, com “a folha” indevidamente como agente.

## Catálogo inicial de regressões

Os intervalos abaixo são locais ao parágrafo, base zero, fim exclusivo, em pontos de código Unicode. Identificadores de proposições e referentes da saída atual são apenas auxiliares de inspeção; não devem ser usados como identidade estável entre versões.

| Caso | Evidência da entrada | Resultado observado em 1.0.0 | Expectativa inicial para a revisão |
|---|---|---|---|
| R19-01 — lemas | P1: `voltasse [608,616)`, `acenasse [649,657)`, `gostasse [767,775)` | `voltr`, `acenr`, `gostr`. | Reconhecer `voltar`, `acenar`, `gostar`, com proveniência e evidências. |
| R19-02 — falsos nomes | P1: `Ainda [326,331)`, `Será [672,676)`, `Não [754,757)` | Nomes próprios classificados como pessoas. | Preservar funções adverbial/verbal e evitar referentes humanos falsos nesses usos. |
| R19-03 — sujeito do relato | P1: `disse [318,323)` | Agente “Ainda”, localizado dentro do conteúdo citado. | Recuperar o sujeito compartilhado da sequência “Ele passou… olhou… e disse”, respeitando a fronteira da fala. |
| R19-04 — sujeito coordenado | P1: `um copo [628,635)` e `acenasse [649,657)` | O copo vira agente de acenar. | Não promover objeto de pegar a sujeito de acenar; analisar a cadeia coordenada e seu sujeito. |
| R19-05 — possessivos | P1: `dele [550,554)` e `[790,794)` | Vínculos com “Ainda” e “Não”. | Rejeitar os vínculos falsos e avaliar o antecedente humano presente no texto. |
| R19-06 — antecedente nominal | P1: `meu pai [229,236)` | Não há menção nominal correspondente; apenas “meu” é detectado. | Reconhecer a pessoa introduzida por “meu pai”, separando-a do possuidor; avaliar as retomadas “Ele/ele/dele”. |
| R19-07 — auxiliar e predicado | P1: `tinha enxugado [301,315)` | Predicado `ter`; `enxugar` não é extraído. | Preservar `enxugar` como predicado lexical e representar o auxiliar sem duplicação indevida. |
| R19-08 — negação e omissão | P1: `não saí [577,584)` e `voltasse [608,616)` | “saí” não é extraído; “voltasse” recebe a negação. | Reconhecer sair e associar o operador ao seu escopo, preservando a subordinada temporal. |
| R19-09 — relações explícitas | P1: contrastes com `mas`, locução `até que` e coordenação com `e`. | Lista de relações vazia. | Anotar e recuperar os vínculos explícitos, com direção e extremidades corretas; manter abstenção nas construções indeterminadas. |
| R19-10 — citação | P1: período completo `[252,362)`. | A síntese usa `[252,361)` e deixa a aspa aberta. | Incluir o delimitador final já presente na segmentação original. |
| R19-11 — primeira pessoa | P1: ocorrências de `eu`, `meu`, `meus`, `minha`; mudanças de escopo de fala. | Pendências genéricas sem distinção suficiente de causas. | Representar o participante discursivo quando houver enquadramento suficiente; preservar exoforia e ambiguidade justificadas. |
| R19-12 — cobertura em P2 | P2: `terminei [30,38)`, `enviei [65,71)`, `atualizando [119,130)`, `chamou [255,261)` e demais predicados. | Apenas “leu” é reconhecido no parágrafo. | Medir e corrigir cobertura verbal usando a anotação revisada, com controle de falsos predicados. |
| R19-13 — sujeito em P2 | P2: “Ela pegou a folha, leu…”, com `leu [574,577)`. | Agente “a folha”. | Recuperar “Ela” como sujeito compartilhado; manter a folha no papel compatível com sua oração. |
| R19-14 — falsos nomes em P2 | P2: `Fiquei [112,118)`, `Voltei [487,493)`, `Retornei [658,666)`, `Parece [800,806)`. | Criam nomes próprios humanos. | Reconhecer usos verbais e não criar pessoas pela capitalização. |
| R19-15 — centralidade | P2: ideia central “leu sem demonstrar qualquer reação e”. | Pontuação 0,90, sem alternativa, apesar da extração de apenas um predicado. | Detectar cobertura insuficiente e reavaliar a hipótese com o registro corrigido; não interpretar pontuação como probabilidade de acerto. |
| R19-16 — checagem | P1/P2: participantes, lemas e relações com problemas conhecidos. | Zero achados de fidelidade estrutural. | Avaliar qualidade da interpretação em camada própria e propagar os achados relevantes para a revisão das saídas. |

Essas expectativas não definem uma interpretação única do texto nem obrigam a resolver todo pronome ou a gerar uma relação em todo exemplo. O documento 19 é material de desenvolvimento já inspecionado; seus parágrafos e variações não devem entrar no conjunto reservado de avaliação.

## Anotações de origem: pistas e conflitos

Defina `A = $.contexto.regras.analise` e `M = A.anotacao`. Há 359 anotações morfológicas em `M.anotacoes_tokens`, 359 entradas em `A.sintaxe`, uma entidade em `A.entidades` e 131 hipóteses em `$.contexto.regras.ocorrencias`. Esses números não são uma contagem de relações proposicionais corretas.

As anotações ajudam em casos como `Ainda` ADV, `voltasse → voltar`, `acenasse → acenar`, auxiliar `tinha` vinculado a `enxugado` e objeto `copo` vinculado a `pegar`. Porém, a própria fonte declara `A.processamento.natureza = "previsoes_do_modelo"` e adverte que validade estrutural não certifica correção linguística.

| Caso de conflito | Local na fonte | Predição recebida | Revisão necessária |
|---|---|---|---|
| R19-F01 | `M.anotacoes_tokens[124]` | `saí`: PROPN, lema `saí`. | Confrontar com o uso verbal de `sair`, primeira pessoa no contexto. |
| R19-F02 | `M.anotacoes_tokens[161]` | `gostasse`: lema `gostasse`. | Reconhecer `gostar`; forma superficial não serve como lema correto nesse caso. |
| R19-F03 | `M.anotacoes_tokens[84]` | `peguei`: lema `peguei`, subjuntivo presente, terceira pessoa. | Rever lema e traços em “Eu… peguei”. |
| R19-F04 | `M.anotacoes_tokens[49]` | `exigia → exiger`. | Reconhecer `exigir`. |
| R19-F05 | `M.anotacoes_tokens[77]` | Aspa final classificada PROPN. | Preservar o delimitador pelo texto; impedir criação de entidade. |
| R19-F06 | `A.entidades[0]` | `Helena` classificada LOC. | Usar o contexto “a diretora de operações” para revisar a classe de entidade. |
| R19-F07 | `M.anotacoes_tokens[249]` e `[264]` | `deixei → deixeir`, `arrumei → arrumeir`. | Rever famílias verbais também nas predições recebidas. |
| R19-F08 | `A.sintaxe[70]` | `tem` da citação ligado como `advcl` a `passou`. | Rever o vínculo do conteúdo citado com o verbo de relato. |
| R19-F09 | `A.sintaxe[137]` | `acenasse` coordenado a `pegar`. | Avaliar o nível de coordenação e o sujeito no período; não assumir que a árvore recebida é um gabarito. |

O adaptador deverá distinguir anotação recebida, diagnóstico de conflito e eventual correção, com proveniência e motivo. A validação de IDs, recortes e árvores garante integridade; a avaliação linguística exige testes e anotações revisadas separadamente.

## Como reproduzir

Na pasta `projeto-inter-main`, com as dependências instaladas:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
import json
from pathlib import Path
from interpretador.main import analisar_json, validar_json
from interpretador.models import JsonAnalysisRequest

documento = json.loads(Path("fixtures/vetorizacao-19.json").read_bytes())
ingestao = validar_json(documento)
print(ingestao.resumo.model_dump())
for paragrafo in ingestao.paragrafos:
    resposta = analisar_json(JsonAnalysisRequest(
        documento=documento, paragrafo_id=paragrafo.rotulo,
    ))
    analise = resposta.analise
    print(paragrafo.rotulo, analise.resumo.model_dump())
    print("Ideia central:", analise.ideia_central.texto,
          analise.ideia_central.confianca)
    print("Síntese:", analise.sintese.texto)
    print("Alertas:", analise.alertas)
PY
```

As respostas completas salvas identificam a versão e o commit que as produziram. Comparações futuras devem ignorar apenas os campos declarados como variáveis e usar o protocolo de pareamento do plano para avaliar correção. Não criar testes que exijam a preservação dos erros da versão 1.0.0.
