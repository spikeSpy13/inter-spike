# Resolução referencial explicável — 1.1.0.dev3

Data: 17/10/2026. Esta é a terceira entrega intermediária do plano 1.1.0. Ela corrige os casos referenciais conhecidos do documento 19 sem declarar concluída a avaliação geral da versão.

## Comportamento implementado

A primeira pessoa fora de citações forma um referente do tipo `participante_discursivo`, rotulado como `narrador`. Esse rótulo representa o papel no discurso; o motor registra expressamente que não inferiu nome, gênero ou identidade externa. Pronomes pessoais e possessivos de primeira pessoa compartilham essa cadeia ao longo do parágrafo e do contexto anterior.

Em citações, `eu`, `nós`, `meu`, `minha`, `meus` e `minhas` começam pendentes. O vínculo só é aceito quando uma oração relatora adjacente oferece um sujeito textual como fonte. Assim, `Ana disse: "Eu assinei meu contrato"` liga as duas menções a Ana, enquanto `"Eu assinei meu contrato"` conserva as duas pendências.

Para terceira pessoa, um único referente humano nominal compatível fornece evidência adicional. Isso resolve `ela/Ela` para Helena no segundo parágrafo do documento 19. O controle `Ana encontrou Maria. Ela respondeu` continua ambíguo porque os dois referentes permanecem plausíveis.

O contrato de análise continua em `1.0.0` e recebe duas extensões aditivas: `Referent.tipo`, com `entidade_textual` ou `participante_discursivo`, e `ReferenceResolution.motivo_pendencia`. O motivo distingue `ambiguidade`, `ausencia_antecedente`, `candidatos_incompativeis`, `evidencia_insuficiente`, `exoforia` e `fonte_fala_desconhecida`. O validador rejeita pendências sem motivo e decisões concluídas que conservem um motivo de pendência.

## Resultado no documento 19

No primeiro parágrafo, as nove ocorrências de primeira pessoa pertencem ao narrador; `Ele`, `ele` e `dele` pertencem ao referente `meu pai`. Todas as 14 menções pronominais locais ficam resolvidas, sem misturar o narrador e o pai.

No segundo parágrafo, as ocorrências locais de primeira pessoa continuam a cadeia do narrador, e `ela`, `Ela` e `dela` apontam para Helena. As oito menções pronominais locais ficam resolvidas. Essas contagens descrevem o comportamento observado neste documento de desenvolvimento e não constituem uma medida de acurácia geral.

O recorte reproduzível fica em `fixtures/revisao-1.1.0/documento-19-referencias-v1.1.0.dev3.json`. O artefato contém as menções pronominais, as decisões e os referentes participantes das cadeias; ele é uma saída observada da candidata, não um gabarito independente.

## Verificação e limites

A suíte cobre narrativa em primeira pessoa, fala citada com e sem fonte, exoforia de segunda pessoa, ausência de antecedente, ambiguidade com duas pessoas, vínculos de Helena e separação entre narrador e pai. A interface mostra o motivo codificado e as explicações de cada pendência.

O método ainda é heurístico. Mudanças de narrador sem marca textual, discurso indireto livre, citações aninhadas, pronomes demonstrativos, elipse nominal e cadeias longas com vários candidatos exigem anotação e regras adicionais. A próxima entrega do plano amplia as relações proposicionais; a publicação final continua dependente do corpus piloto reservado e das métricas definidas no plano.
