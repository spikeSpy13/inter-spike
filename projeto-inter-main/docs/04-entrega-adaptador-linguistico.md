# Primeira entrega da revisão linguística

Data: 17/10/2026. Versão do motor e pacote: `1.1.0.dev1`. Esta é uma versão de desenvolvimento; o plano completo de qualidade da versão 1.1.0 continua em execução.

## Mudanças disponíveis

- Adaptador tipado para tokens, morfologia, dependências e períodos do JSON, preservando os dados recebidos e separando decisões e diagnósticos.
- Validação de IDs, recortes, vínculo token/período/parágrafo, cabeças existentes e ciclos. Anotações malformadas produzem erros legíveis por HTTP 422.
- Conversão global/local que preserva Unicode e as quebras de linha originais; P2 do documento 19 mantém início global 889.
- Léxico compartilhado por extração e detecção de menções. Corrige as famílias conhecidas sem converter qualquer sufixo em verbo; palavras desconhecidas permanecem sem lema verbal inferido.
- Tratamento de conflitos como `saí` classificado como PROPN, `gostasse` sem lema correto e traços incompatíveis em formas de primeira pessoa. As predições originais continuam disponíveis.
- Correção dos falsos nomes funcionais/verbalizados do documento 19 e reconhecimento de “meu pai”, com possessivo aninhado.
- Uso do predicado lexical em “tinha enxugado” e abstenção de ações autônomas para particípios descritivos como “caneca lascada” e “fiquei parado”, com motivo registrado.
- Segmentação compartilhada que inclui aspas finais e proteção contra relações entre períodos distintos.
- Correções pontuais de negação: o infinitivo “buscar” não recebe o `nem` de “desistiu”; “voltasse” não herda o `não` de “não saí… até que”.
- Painel de revisão linguística na interface, com tokens, lemas, classes, origem e diagnósticos. Limites da interpretação ficam explícitos mesmo quando a checagem estrutural da geração não encontra achados.

O contrato de análise permanece `1.0.0`, com o campo opcional `analise_linguistica`. Bases do parágrafo e do contexto ficam separadas, com seus próprios intervalos locais. A versão do motor é independente da versão do contrato. A origem da base e o adaptador são registrados em `execucao.parametros`.

## Comparação do documento 19

A entrada é idêntica à linha de base, verificada por SHA-256. A [resposta da candidata](../fixtures/revisao-1.1.0/documento-19-candidato-v1.1.0.dev1.json) inclui versão e impressão digital dos arquivos do motor; a [resposta 1.0.0](../fixtures/revisao-1.1.0/documento-19-baseline-v1.0.0.json) permanece preservada.

| Saída observada | P1 — 1.0.0 | P1 — dev1 | P2 — 1.0.0 | P2 — dev1 |
|---|---:|---:|---:|---:|
| Proposições extraídas | 11 | 33 | 1 | 25 |
| Relações dos tipos já suportados | 0 | 1 | 0 | 2 |
| Menções não resolvidas, incluindo contexto | 12 | 9 | 19 | 16 |
| Diagnósticos da base do parágrafo | não disponível | 11 | não disponível | 16 |

Essas contagens descrevem o comportamento do motor e não medem acurácia. Em P2, as contagens referenciais incluem P1 como contexto. As novas relações usam tipos já existentes, recuperados após maior cobertura verbal; contraste, limite temporal e coordenação afirmativa ainda exigem implementação e avaliação próprias.

Os lemas `voltar`, `acenar`, `gostar` e `enxugar` são recuperados nos casos relatados. “Ainda”, “Não”, “Será”, “Fiquei”, “Voltei”, “Retornei” e “Parece” deixam de criar nomes próprios humanos nesses usos. O reconhecimento de “meu pai” permite vínculos referenciais antes inviáveis, que ainda precisam de avaliação no corpus revisado.

## Validação desta entrega

- 115 testes aprovados, incluindo testes HTTP reais e regressões dos documentos 19 e 28.
- Testes de anotações ausentes/parciais, cópias independentes da fonte, conflitos lexicais, classes funcionais contextuais, coordenadas, IDs, cabeças e ciclos.
- API validada com serialização da predição recebida e da decisão adotada, além de erro 422 para cabeça sintática inexistente.
- Navegador Chromium: fluxos de texto livre e JSON 19, abertura do painel de lemas e diagnósticos, viewport móvel sem transbordamento horizontal e ausência de erros JavaScript.
- Wheel gerado, instalado em ambiente isolado e executado fora do checkout, incluindo recursos estáticos e análise de P2.

## Limites e próxima entrega

A base linguística amplia a cobertura e torna conflitos observáveis. Ela não resolve toda a interpretação: os papéis de “um copo” em “acenasse” e de “a folha” em “leu” ainda exigem correção. Fontes de fala, primeira pessoa discursiva, coordenação, construções subordinadas e confiança da centralidade precisam de revisão adicional.

A predição de entidades, incluindo `Helena` classificada como LOC na origem, ainda não é consumida pelo adaptador; a decisão atual de menção usa outras regras e não constitui uma auditoria geral de NER. Árvores recebidas continuam sendo hipóteses, mesmo quando passam na validação estrutural.

Ainda não há corpus reservado anotado nem metas de precisão/cobertura aferidas. A suíte aprovada valida os comportamentos especificados, sem sustentar alegação de acurácia geral. A próxima entrega do plano é corrigir sujeitos e papéis por oração, seguida de correferência e ampliação das relações.
