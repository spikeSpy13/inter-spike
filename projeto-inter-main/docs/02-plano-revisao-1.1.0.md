# Plano de revisão — versão 1.1.0

Data: 17/10/2026. Estado: em implementação; terceira entrega disponível em `1.1.0.dev3`. A publicação final `1.1.0` continua condicionada aos critérios deste plano.

Base: motor 1.0.0, commit `ac47662`, PDF “Interpretador de Proposições f.pdf” e JSON original `vetorizacao-19.json`, recebido e validado em 17/10/2026. O objetivo desta revisão é melhorar a qualidade linguística e explicitar os limites da análise, preservando evidências, API, interface e execução local. A reprodução dos dois parágrafos, as respostas completas e o catálogo inicial estão no [registro do documento 19](03-documento-19-linha-de-base.md).

## Resultado observado e diagnóstico

O PDF registra 11 proposições, 28 menções, 14 referentes, duas resoluções, 12 menções pronominais sem referente, quatro operadores, nenhuma relação e uma síntese de 109 caracteres. As duas resoluções apresentadas ligam “dele” a “Ainda” e “Não”, classificados incorretamente como pessoas. Portanto, aumentar a quantidade de resoluções não basta: é necessário avaliar se os vínculos estão corretos.

| Achado | Causa confirmada ou limite observado | Resultado esperado da revisão |
|---|---|---|
| `voltasse → voltr`, `acenasse → acenr`, `gostasse → gostr` | A remoção de sufixos em `extractor.py` elimina a vogal temática. O mesmo mecanismo erra plurais como `chegaram`. | Lemas válidos, com origem identificada; incerteza explícita quando a forma não for reconhecida. |
| “Ainda”, “Não” e “Será” classificados como pessoas | A detecção de nomes usa maiúscula e uma lista limitada de exclusões; todo nome próprio recebe classe pessoa. | Categoria gramatical e evidência de entidade orientam a decisão; capitalização isolada não cria pessoa. |
| “um copo” como agente de “acenasse”; “Ainda” como agente de “disse” | Busca por proximidade, seleção de nomes pospostos e atribuição padrão de agente não respeitam suficientemente a estrutura das orações. | Sujeitos e papéis vinculados à oração correta, inclusive em coordenação e discurso citado. |
| 12 menções sem referente; duas resoluções incorretas | Primeira pessoa é bloqueada por exoforia; candidatos falsos contaminam possessivos. | Vínculos sustentados por evidência e pendências com motivos distintos. |
| Nenhuma relação proposicional | O grafo cobre sete tipos e examina principalmente predicados consecutivos. Contraste com “mas”, temporalidade com “até que” e coordenação afirmativa não estão cobertos. | Relações explícitas anotadas são recuperadas com tipo, direção e extremidades corretos. |
| “tinha enxugado” representado por `ter`; predicados ausentes | O reconhecimento lexical limitado também prejudica a identificação de auxiliares e verbos principais. | Predicado lexical reconhecido; auxiliares e traços de tempo/modo preservados sem duplicação indevida. |
| “voltasse” recebe negação de “não saí” | A janela textual permite que o marcador atravesse o limite de oração. | Negação associada ao predicado sob seu escopo; subordinadas mantêm sua polaridade própria. |
| Síntese apresentada com aspas abertas | A segmentação de geração não consome aspas de fechamento. O defeito também foi reproduzido em exemplos mínimos independentes. | Recortes completos com delimitadores e atribuição preservados, sem alterar o original. |
| Ideia central exibida com 63%; zero alertas de fidelidade | A pontuação é heurística. A checagem compara a saída com um registro que pode já conter erros. | Qualidade da interpretação e fidelidade da geração ficam visíveis como avaliações distintas. |
| P2 tem apenas um predicado reconhecido, “leu”, com “a folha” como agente e pontuação central 0,90 | A entrada completa revelou omissões verbais e erro de sujeito; a pontuação não leva suficientemente em conta a cobertura da extração. | Cobertura verbal medida, sujeito compartilhado correto e revisão explícita quando a base da centralidade for insuficiente. |
| A origem também prevê `saí` como PROPN, `gostasse` sem lematização e `Helena` como LOC | As camadas de morfologia, sintaxe, entidades e regras são previsões de modelo, não um gabarito. | Diagnosticar conflitos e registrar a origem e o motivo das decisões; integridade estrutural e correção linguística são verificadas separadamente. |

A validação do código revelou uma causa transversal: a fixture de vetorização já contém lemas, classes gramaticais, morfologia e dependências sintáticas. A ingestão atual não encaminha essas anotações ao motor; `analisar_json` passa apenas o parágrafo e o contexto como texto. Aproveitar essas informações requer um adaptador validado, pois as anotações de origem também podem ser incompletas ou incorretas.

## Ordem de execução

Progresso da primeira entrega: adaptador, validação estrutural, compartilhamento lexical, diagnósticos e regressões dos documentos 19/28 implementados. Também foram corrigidos recortes de aspas e casos específicos de vazamento de negação, e bloqueadas relações entre períodos distintos. A anotação do corpus reservado, a revisão geral de sujeitos/correferência e os novos tipos de relação permanecem pendentes. Evidências e limites estão no [relatório da entrega](04-entrega-adaptador-linguistico.md).

Progresso da segunda entrega: sujeitos explícitos e compartilhados, abstenção justificada, distinção entre sujeito e papel semântico, vozes ativa/passiva, limites dos argumentos e fontes de fala foram revisados para os casos cobertos. Os alvos “um copo”/“acenasse”, “a folha”/“leu” e o sujeito de “disse” estão corrigidos e testados. A revisão não esgota construções sintáticas ambíguas. O [relatório de sujeitos e papéis](05-sujeitos-e-papeis-oracionais.md) registra os resultados e os limites.

Progresso da terceira entrega: primeira pessoa narrativa, primeira pessoa em citação e retomadas de terceira pessoa com um único antecedente humano compatível foram revisadas. As pendências agora distinguem causas por código e explicação textual. No documento 19, o narrador permanece separado de “meu pai”, e `ela/Ela/dela` no segundo parágrafo apontam para Helena. O [relatório de referências](06-resolucao-referencial.md) registra os controles e limites.

### 1. Fixar a referência e a avaliação

Entregas:

- Registrar a saída 1.0.0 e um catálogo dos erros, com trechos, intervalos e decisões esperadas.
- Criar casos mínimos para cada falha, acompanhados de variações e controles negativos.
- Preparar um corpus piloto de pelo menos 30 parágrafos variados: 20 para desenvolvimento e 10 reservados para avaliação. Manter versões do mesmo exemplo no mesmo conjunto.
- Anotar predicados/lemas, menções, sujeitos, papéis, vínculos referenciais, escopos, relações e conteúdo essencial aceitável. Registrar ambiguidades e divergências da revisão humana.

Critério de aceite: cada problema tem um caso reproduzível e uma expectativa revisável; os exemplos reservados são definidos antes dos ajustes. As métricas da versão 1.0.0 são medidas como linha de base.

Situação dos dados: o JSON original do documento 19 foi incorporado sem alteração em `fixtures/vetorizacao-19.json`. O motor 1.0.0 reproduziu o P1 do PDF e também foi executado sobre P2 com P1 como contexto. As respostas completas e o catálogo de regressões estão registrados. Ainda faltam os casos mínimos automatizados, a anotação revisada e o corpus piloto com conjunto reservado. O documento 19 e suas variações pertencem ao conjunto de desenvolvimento, pois já foram inspecionados.

### 2. Criar a base linguística compartilhada

Entregas:

- Criar um adaptador interno de tokens, lemas, classes, morfologia, dependências e períodos para a entrada estruturada.
- Validar IDs, cabeças sintáticas, recortes e conversão entre coordenadas globais do documento e locais do parágrafo, incluindo o contexto anterior.
- Definir precedência e registrar a proveniência: anotação de origem validada ou regra local. Tratar conflitos e ausência de dados explicitamente.
- Preservar separadamente predição recebida, diagnóstico e correção. Cobrir os conflitos reais da origem: `saí` como nome próprio, `gostasse` sem lema correto, `peguei` com traços divergentes, `exigia → exiger`, aspas como PROPN e `Helena` como local. Árvores sintáticas íntegras também exigem revisão quando atribuem conteúdo citado ou coordenação a cabeças inadequadas.
- Usar a mesma representação no detector de menções e no extrator. Manter o fluxo de texto livre com análise local e cobertura declarada.
- Corrigir famílias conjugacionais, auxiliares e formas desconhecidas. Distinguir nomes de pessoas, outros nomes próprios e palavras funcionais em início de período ou fala.

Critério de aceite: `voltasse`, `acenasse` e `gostasse` produzem `voltar`, `acenar` e `gostar`; `chegaram` e `trabalhavam` também têm lemas corretos. “Ainda”, “Não” e “Será” não viram pessoas nos usos relatados. “tinha enxugado” preserva `enxugar` como predicado lexical. Todos os intervalos continuam reproduzindo o original.

Arquivos principais: `ingestao.py`, `main.py`, `extractor.py`, `referencias/detector.py` e modelos internos.

### 3. Corrigir orações, participantes, fala e operadores

Entregas:

- Identificar limites de oração e sujeitos explícitos antes de recorrer à proximidade textual.
- Tratar sujeito compartilhado na coordenação, sujeito omitido, oração relativa e voz passiva com justificativa verificável.
- Separar sujeito sintático e papel semântico; preservar indeterminação quando o papel não puder ser sustentado.
- Restringir a identificação de falante à oração relatora e aos limites da citação.
- Corrigir escopo de negação e modalidade em subordinadas e coordenadas.
- Compartilhar a segmentação entre extração e geração, incluindo aspas de fechamento no recorte correto.

Critério de aceite: em “Maria disse que João assinou o contrato”, Maria é o sujeito de dizer. Em “Ele pegou um copo e acenou”, o copo não se torna agente de acenar. Em “Não saí até que ele voltasse”, o retorno não recebe automaticamente a negação de sair. Citações completas preservam suas aspas, fonte e intervalos.

Arquivos principais: `extractor.py`, `grafo/participantes.py`, `grafo/atribuicoes.py`, `grafo/operadores.py` e `geracao.py`.

### 4. Revisar resolução referencial

Entregas:

- Resolver primeira pessoa em relação ao participante discursivo ou à fonte da fala quando o enquadramento estiver estabelecido. O narrador é um papel discursivo; sua identidade externa não deve ser inventada.
- Reconhecer antecedentes nominais presentes na entrada completa, como “meu pai”, distinguindo o possuidor de primeira pessoa e a pessoa mencionada antes de analisar “Ele/ele/dele”.
- Vincular possessivos ao possuidor compatível e distinguir gênero do possuidor e do objeto possuído.
- Tratar repetições de pronomes sob o mesmo escopo e mudanças de falante.
- Diferenciar ausência de antecedente, ambiguidade, exoforia, fonte de fala desconhecida e cobertura insuficiente do método.
- Rever candidatos e limiares usando os exemplos anotados, com atenção às ligações falsas.

Critério de aceite: nenhuma ligação de “dele” a “Ainda” ou “Não” nos casos de referência. Cada vínculo aceito apresenta evidência e motivo; casos legitimamente ambíguos ou sem antecedente permanecem explícitos. Reduzir a contagem de pendências, isoladamente, não é critério de sucesso.

Arquivos principais: `referencias/`, `grafo/atribuicoes.py` e modelos de referência.

### 5. Ampliar o grafo proposicional

Entregas:

- Acrescentar os tipos exigidos pelas anotações do corpus, priorizando contraste/adversidade, limite temporal, coordenação afirmativa e vínculo entre relato e conteúdo citado.
- Definir o significado e a direção de cada relação antes da implementação. “Até que” não deve implicar causalidade automaticamente.
- Selecionar extremidades por estrutura e escopo; um predicado intermediário não pode impedir um vínculo sustentado pelas anotações.
- Indicar cobertura parcial quando uma construção identificada ainda não puder ser analisada com segurança.
- Atualizar validadores, seleção de conteúdo essencial e cobertura de geração para os tipos incorporados.

Critério de aceite: os casos anotados com “mas”, “até que”, coordenação e relato recuperam as relações esperadas. Os testes conferem tipo, direção, extremidades e evidência. Controles com proposições independentes continuam sem relações. Não haverá meta de produzir ao menos uma aresta em todo parágrafo.

Arquivos principais: `grafo/relacoes.py`, `grafo/models.py`, `grafo/validator.py`, `centralidade.py` e `geracao.py`.

### 6. Revisar ideia central, síntese, checagem e interface

Entregas:

- Reavaliar a centralidade com o registro linguístico corrigido. A alternativa escolhida deve preservar o núcleo narrativo anotado, admitindo leituras concorrentes justificadas.
- Expor pontuação, margem entre alternativas e caráter não calibrado. Aumentar o número exibido não é objetivo da revisão.
- Criar avaliação da qualidade do registro interpretativo e manter a checagem de fidelidade das saídas, com estados e achados próprios por camada.
- Propagar problemas relevantes da interpretação para a revisão da ideia central e da síntese. Zero achados de geração não deve ocultar problemas do registro.
- Mostrar na interface motivos das pendências, limites de cobertura, origem das anotações e resultados de cada camada. Corrigir a concordância dos alertas.

Critério de aceite: falhas controladas de lema, participante, referência ou escopo são identificadas pelas regras de qualidade previstas, mesmo quando a síntese reproduz o registro. Aspas e atribuição são preservadas. A tela não apresenta pontuação heurística como probabilidade de acerto nem ausência de achados como garantia semântica.

Arquivos principais: `centralidade.py`, `geracao.py`, `fidelidade.py`, `models.py`, `dist/app.js` e `dist/index.html`.

## Medição e critérios para publicar

| Dimensão | Medida |
|---|---|
| Predicados e lemas | Precisão e cobertura dos predicados; proporção de lemas corretos e de formas desconhecidas. |
| Menções | Precisão e cobertura por tipo, com contagem separada de falsos nomes próprios. |
| Participantes e escopos | Proporção de sujeitos/papéis corretos e correspondência do conjunto de proposições sob cada operador. |
| Referências | Precisão dos vínculos aceitos, cobertura dos vínculos resolvíveis, ligações falsas e acerto de abstenção nos casos ambíguos ou exofóricos. |
| Relações | Precisão, cobertura e F1 por tipo, exigindo extremidades e direção corretas. |
| Centralidade e síntese | Revisão humana de conteúdo essencial, participantes, negação, relações e integridade das citações; registrar alternativas aceitáveis. |
| Checagem | Detecção de falhas inseridas deliberadamente e falsos alertas em saídas válidas, separada por camada. |
| Desempenho | Mediana e percentil 95 em entradas e máquina fixadas; consumo e dependências declarados. Os 19,588 ms do PDF são uma execução isolada. |

Antes da medição, fixar o protocolo de pareamento: menções e predicados por intervalos exatos; relações por tipo, direção e extremidades correspondentes; referências por vínculos esperados. IDs como `P1` e `R2` podem mudar entre versões e não serão usados isoladamente como identidade de comparação. Registrar contagens, denominadores, casos não aplicáveis e abstenções; eventual medida por sobreposição deve ser apresentada separadamente.

As metas numéricas de qualidade serão fixadas após medir a linha de base no conjunto de desenvolvimento e antes de abrir o conjunto reservado. O piloto não sustenta alegação de acurácia geral em português. Os 76 testes aprovados da versão 1.0.0 são uma base de regressão de software, não uma medida de precisão linguística.

A publicação da versão 1.1.0 depende de:

1. Todos os casos de regressão conhecidos corrigidos ou explicitamente tratados como indeterminados quando houver motivo linguístico, sem ocultar erros determinísticos.
2. Suíte existente preservada e ampliada com testes de comportamento, controles negativos, entrada estruturada, texto livre, API e interface. Mudanças intencionais no contrato têm suas expectativas atualizadas e documentadas.
3. Comparação 1.0.0 × candidata documentada no corpus reservado, com atendimento às metas fixadas previamente. Regressões materiais bloqueiam a publicação até serem corrigidas ou até uma revisão explícita e documentada do escopo e dos critérios; apenas explicá-las no relatório não basta.
4. Intervalos e IDs válidos em todas as evidências e relações geradas.
5. Pacote instalado e fluxo completo validados; versão do motor, proveniência e parâmetros registrados corretamente.

## Entregas e limites desta versão

Executar os seis blocos em alterações pequenas, mantendo o fluxo verificável a cada bloco. A ordem é: referência de avaliação → base linguística → estrutura das orações → referências → grafo → saídas e revisão.

`1.1.0` é a versão proposta do aplicativo. Antes de ampliar enums, estados ou campos, revisar a compatibilidade do contrato e dos clientes. Preferir extensões opcionais; mudanças incompatíveis exigem migração e versionamento apropriado. API, interface, OpenAPI, pacote, documentação e testes devem concordar sobre as versões suportadas.

Continuam fora do escopo: interpretar documentos longos integralmente, treinar embeddings, certificar equivalência semântica geral e introduzir serviços pagos como dependência obrigatória. Qualquer componente linguístico adicional deve ter instalação reproduzível, licença e custo avaliados.

Entregas já registradas: entrada original do documento 19, linha de base dos dois parágrafos, catálogo inicial, adaptador linguístico, seleção de sujeitos e fontes de fala, e resolução referencial explicável, com testes de comportamento. Os agentes incorretos de “acenasse” e “leu” foram corrigidos; narrador, pai e Helena permanecem em cadeias distintas e fundamentadas. A próxima entrega deve ampliar as relações proposicionais, mantendo o corpus de avaliação e as construções sintáticas ainda não cobertas como itens explícitos do plano.
