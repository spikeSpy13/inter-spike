# Sujeitos, papéis e fontes de fala — 1.1.0.dev2

Entrega de 17/10/2026. Versão de desenvolvimento que revisa a seleção de sujeitos, os papéis associados e o enquadramento de falas citadas. A versão final 1.1.0 continua sujeita aos critérios do plano de qualidade.

## Correções verificadas

| Caso | Problema da referência | Resultado atual |
|---|---|---|
| Documento 19, P1, “acenasse” | “um copo” como agente. | “ele” como sujeito/agente, herdado da cadeia coordenada sustentada. |
| Documento 19, P2, “leu” | “a folha” como agente. | “Ela” como sujeito/agente; o objeto anterior não substitui o sujeito. |
| Documento 19, P2, “demonstrar” e “deu” | Busca por proximidade não preservava adequadamente a cadeia. | Mantêm “Ela”, com evidências do controle/coordenação. |
| Documento 19, P1, “disse” | “Ainda” na referência 1.0.0; sem sujeito vinculado na dev1. | “Ele” como sujeito; fonte da fala “meu pai”. |
| “Ana havia assinado…” | Tempo composto ativo classificado como passivo. | Ana permanece agente da voz ativa. |
| “O contrato foi assinado e enviado por Ana.” | Auxiliar compartilhado perdido na segunda proposição. | O contrato permanece sujeito/paciente dos dois predicados; Ana é agente de enviar, sem virar sujeito. |
| “Ana enviou e João chegou.” | João podia virar objeto do primeiro verbo. | João é sujeito apenas da oração seguinte. |
| Dois envios com destinatário no segundo | João podia ser atribuído aos dois envios. | Objetos e destinatário permanecem na oração correspondente. |
| Relatora e destinatário, ou duas falas | Fonte escolhida por proximidade ou em outro período. | Apenas sujeito de relatora vinculada ao par de aspas fornece a fonte; destinatário e sujeito citado ficam separados. |

O recorte reproduzido do documento 19 está em [`documento-19-sujeitos-v1.1.0.dev2.json`](../fixtures/revisao-1.1.0/documento-19-sujeitos-v1.1.0.dev2.json), com versão, impressão digital dos arquivos do motor, entrada e decisões. É uma saída observada dos casos selecionados, não um gabarito linguístico completo.

## Como a decisão é representada

- Dependências de sujeito nominal são verificadas com a menção, o período e o escopo da citação.
- Coordenação e alguns complementos com controle sustentado podem herdar um sujeito; a cadeia e seus intervalos ficam registrados.
- O texto livre usa construções locais conservadoras. Uma menção depois do verbo ou um objeto próximo não bastam para determinar um sujeito.
- Árvores de origem conflitantes podem ser revistas em construções específicas sustentadas pelo texto, como a relatora posposta e o nominal da passiva nos exemplos do documento 28. A razão do conflito é registrada.
- Elipses sem menção sustentável, controle incerto e sujeitos oracionais permanecem indeterminados. Não é criado um narrador nominal para preencher esses casos.

O contrato de análise permanece `1.0.0` com extensões opcionais:

- `proposicoes[].sujeito`: estado, método, `mencao_id`, razões, evidências e candidatos;
- `proposicoes[].participantes[].funcao_sintatica`: `sujeito` para a menção selecionada, independente de `papel`;
- `execucao.parametros.seletor_sujeito`: identifica `oracoes_sujeitos_v1`.

O validador do grafo verifica que decisão e participante concordam e que as evidências reproduzem os intervalos originais. O alerta de sujeito indeterminado considera essa decisão mesmo quando há um objeto, destinatário ou agente passivo identificado.

Os papéis distinguem paciente da passiva, tema de estado e experienciador nas famílias cobertas. Verbos sem classificação semântica suficiente mantêm papel neutro. Na interface, cada proposição mostra as razões e as evidências da escolha ou abstenção.

## Validação e limites

- 157 testes aprovados, incluindo HTTP, os documentos 19/28, 20 testes do seletor, 10 de fala e 12 de papéis por oração.
- Preservadas as regressões de relativa com “alguém”, participante da passiva, relatora posposta, modalidade e negação já cobertas.
- Chromium: texto livre, P1/P2 do JSON 19, sujeitos e justificativas visíveis, viewport móvel sem transbordamento e ausência de erros JavaScript.
- Pacote instalado fora do checkout, com módulo de sujeitos e recursos estáticos incluídos.

A seleção continua conservadora. Construções de percepção, relativas complexas, elipse entre períodos e controle ambíguo ainda podem exigir abstenção ou revisão. O corpus reservado anotado e as métricas de precisão/cobertura permanecem pendentes. As contagens de proposições ou sujeitos encontrados não representam acurácia geral.

A próxima frente do plano é revisar correferência e os motivos das pendências; a ampliação dos tipos de relação será avaliada depois sobre a base corrigida.
