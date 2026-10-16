const exampleContext = `Quando Helena finalmente se sentou no banco da praça, percebeu que o gerente do banco não havia assinado o contrato de financiamento por pura cautela. Durante toda a reunião matinal, ele bombardeou a proposta dela com argumentos pesados, embora nenhuma falha técnica tivesse sido encontrada nos cálculos pelos auditores externos. "Claro, porque perder três semanas revisando planilhas é exatamente o meu conceito de eficiência", murmurou a engenheira para si mesma, enquanto a bateria do seu celular morria lentamente sob a sombra das árvores.`;
const exampleParagraph = `Apesar daquele revés temporário, a profissional não abandonou o campo de batalha nem desistiu de buscar novos recursos para o projeto solar. No fim da tarde, o documento atualizado foi enviado por ela ao diretor financeiro através de um mensageiro expresso, pois o tempo já estava se esgotando. Você realmente acredita que uma simples burocracia bancária seria capaz de frear alguém que construiu toda a carreira transformando crises em combustível?`;

const paragraphInput = document.querySelector("#paragraph");
const contextInput = document.querySelector("#previous-context");
const contextBox = document.querySelector(".context-box");
const charCount = document.querySelector("#char-count");
const analyzeButton = document.querySelector("#analyze");
const exampleButton = document.querySelector("#example");
const clearButton = document.querySelector("#clear");
const emptyState = document.querySelector("#empty-state");
const analysisOutput = document.querySelector("#analysis-output");
const propositionList = document.querySelector("#proposition-list");
const graphMap = document.querySelector("#graph-map");
const referenceMap = document.querySelector("#reference-map");
const mentionMap = document.querySelector("#mention-map");
const resultStats = document.querySelector("#result-stats");

function updateCount() {
  const count = [...paragraphInput.value].length;
  charCount.textContent = `${count} ${count === 1 ? "caractere" : "caracteres"}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function typeLabel(type) {
  return ({
    nome_proprio: "nome próprio",
    descricao_nominal: "descrição",
    descricao_complexa: "descrição complexa",
    pronome_pessoal: "pronome",
    pronome_possessivo: "possessivo"
  })[type] || type;
}

function stateLabel(state) {
  return ({
    resolvida: "resolvida",
    ambigua: "ambígua",
    nao_resolvida: "não resolvida",
    novo_referente: "novo referente"
  })[state] || state;
}

function humanize(value) {
  return String(value || "").replaceAll("_", " ");
}

function renderGraph(data) {
  const propById = new Map(data.proposicoes.map(item => [item.id, item]));
  const referentById = new Map(data.referentes.map(item => [item.id, item]));
  const endpoint = id => {
    const prop = propById.get(id);
    if (prop) return `${id} · ${prop.predicado}`;
    const referent = referentById.get(id);
    return referent ? `${id} · ${referent.rotulo}` : id;
  };
  const operators = data.operadores_escopo.map(item => `
    <li class="graph-item operator-item ${escapeHtml(item.tipo)}">
      <span class="graph-id">${escapeHtml(item.id)}</span>
      <div><strong>${escapeHtml(humanize(item.subtipo))}</strong><small>${escapeHtml(item.tipo)} · “${escapeHtml(item.marcador)}”</small></div>
      <span class="scope-list">${item.escopo.map(id => escapeHtml(id)).join(" · ")}</span>
    </li>
  `).join("");
  const frames = data.quadros_atribuicao.map(item => `
    <li class="graph-item attribution-item">
      <span class="graph-id">${escapeHtml(item.id)}</span>
      <div><strong>${escapeHtml(humanize(item.modo))}</strong><small>${escapeHtml(item.fonte.rotulo)} · ${escapeHtml(item.estado)}</small></div>
      <span class="scope-list">${item.escopo.map(id => escapeHtml(id)).join(" · ")}</span>
    </li>
  `).join("");
  const relations = data.relacoes.map(item => `
    <li class="relation-item">
      <span class="relation-endpoint">${escapeHtml(endpoint(item.origem_id))}</span>
      <span class="relation-type">${escapeHtml(humanize(item.tipo))}${item.marcador ? `<small>“${escapeHtml(item.marcador)}”</small>` : ""}</span>
      <span class="relation-arrow" aria-hidden="true">→</span>
      <span class="relation-endpoint">${escapeHtml(endpoint(item.destino_id))}</span>
    </li>
  `).join("");

  graphMap.innerHTML = `
    <header>
      <div>
        <h3 id="graph-title">Grafo proposicional</h3>
        <p>Escopos e relações calculados sem propagação automática por proximidade.</p>
      </div>
      <span>${data.relacoes.length} ${data.relacoes.length === 1 ? "relação" : "relações"}</span>
    </header>
    <div class="graph-columns">
      <section><h4>Operadores</h4><ul class="graph-list">${operators || `<li class="quiet-message">Nenhum operador marcado.</li>`}</ul></section>
      <section><h4>Atribuição</h4><ul class="graph-list">${frames || `<li class="quiet-message">Nenhum quadro formado.</li>`}</ul></section>
    </div>
    <section class="relations-section">
      <h4>Relações</h4>
      <ul class="relation-list">${relations || `<li class="quiet-message">Nenhuma relação marcada.</li>`}</ul>
    </section>
  `;
}

function renderReferenceCard(referent, mentionById, resolutionByMention) {
  const mentionChips = referent.mencoes.map(id => {
    const mention = mentionById.get(id);
    const resolution = resolutionByMention.get(id);
    if (!mention) return "";
    const relation = resolution?.tipo_relacao === "possuidor" ? `<small>possuidor</small>` : "";
    return `<li><span>${escapeHtml(id)}</span> “${escapeHtml(mention.texto)}” ${relation}</li>`;
  }).join("");
  return `
    <article class="referent-card ${referent.mencoes.length > 1 ? "linked" : "singleton"}">
      <div class="referent-heading">
        <span class="referent-id">${escapeHtml(referent.id)}</span>
        <span class="referent-confidence">${Math.round(referent.confianca * 100)}%</span>
      </div>
      <h4>${escapeHtml(referent.rotulo)}</h4>
      <p>${escapeHtml(referent.classe_semantica)} · ${referent.mencoes.length} ${referent.mencoes.length === 1 ? "menção" : "menções"}</p>
      <ul>${mentionChips}</ul>
    </article>
  `;
}

function renderDecision(resolution, mentionById, referentById) {
  const mention = mentionById.get(resolution.mencao_id);
  if (!mention) return "";
  const target = resolution.referente_id ? referentById.get(resolution.referente_id) : null;
  const alternatives = resolution.alternativas.map(item => {
    const referent = referentById.get(item.referente_id);
    return `<li><strong>${escapeHtml(item.referente_id)}</strong> — ${escapeHtml(referent?.rotulo || "candidato")} · ${Math.round(item.pontuacao * 100)}%</li>`;
  }).join("");
  return `
    <details class="reference-decision ${escapeHtml(resolution.estado)}">
      <summary>
        <span><strong>${escapeHtml(resolution.mencao_id)}</strong> “${escapeHtml(mention.texto)}”</span>
        <span class="decision-state">${escapeHtml(stateLabel(resolution.estado))}${target ? ` → ${escapeHtml(target.id)}` : ""}</span>
      </summary>
      <div class="decision-body">
        <p><strong>Relação:</strong> ${escapeHtml(resolution.tipo_relacao)} · ${Math.round(resolution.confianca * 100)}% de confiança</p>
        <ul class="reason-list">${resolution.razoes.map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
        ${alternatives ? `<div class="alternatives"><strong>Alternativas consideradas</strong><ul>${alternatives}</ul></div>` : ""}
      </div>
    </details>
  `;
}

function renderReferences(referents, resolutions, mentions) {
  const mentionById = new Map(mentions.map(item => [item.id, item]));
  const resolutionByMention = new Map(resolutions.map(item => [item.mencao_id, item]));
  const referentById = new Map(referents.map(item => [item.id, item]));
  const linked = referents.filter(item => item.mencoes.length > 1);
  const singletons = referents.filter(item => item.mencoes.length === 1);
  const decisions = resolutions.filter(item => item.estado !== "novo_referente");
  const pending = decisions.filter(item => item.estado === "ambigua" || item.estado === "nao_resolvida");

  referenceMap.innerHTML = `
    <header>
      <div>
        <h3 id="reference-title">Referentes formados</h3>
        <p>Menções agrupadas por identidade; possessivos indicam o possuidor.</p>
      </div>
      <span>${referents.length} ${referents.length === 1 ? "referente" : "referentes"}</span>
    </header>
    <div class="referent-grid">
      ${linked.map(item => renderReferenceCard(item, mentionById, resolutionByMention)).join("") || `<p class="quiet-message">Nenhuma cadeia referencial foi formada.</p>`}
    </div>
    ${singletons.length ? `
      <details class="singleton-section">
        <summary>Ver ${singletons.length} ${singletons.length === 1 ? "referente individual" : "referentes individuais"}</summary>
        <div class="referent-grid singleton-grid">${singletons.map(item => renderReferenceCard(item, mentionById, resolutionByMention)).join("")}</div>
      </details>
    ` : ""}
    ${pending.length ? `<div class="pending-note"><strong>${pending.length} ${pending.length === 1 ? "decisão pendente" : "decisões pendentes"}</strong> permanecem visíveis para revisão.</div>` : ""}
    ${decisions.length ? `
      <details class="decision-section">
        <summary>Examinar justificativas e alternativas</summary>
        <div class="decision-list">${decisions.map(item => renderDecision(item, mentionById, referentById)).join("")}</div>
      </details>
    ` : ""}
  `;
}

function renderMentionGroup(title, mentions, sourceLabel, resolutionByMention) {
  if (!mentions.length) return "";
  const items = mentions.map(mention => {
    const resolution = resolutionByMention.get(mention.id);
    const referent = resolution?.referente_id
      ? `<span class="mention-reference">${escapeHtml(resolution.referente_id)}</span>`
      : `<span class="mention-reference pending">${escapeHtml(stateLabel(resolution?.estado || "nao_resolvida"))}</span>`;
    return `
    <li class="mention-item ${mention.mencao_pai_id ? "nested" : ""}">
      <span class="mention-id">${escapeHtml(mention.id)}</span>
      <span class="mention-text">“${escapeHtml(mention.texto)}” ${referent}</span>
      <span class="mention-type">${escapeHtml(typeLabel(mention.tipo))}</span>
      <span class="mention-meta">${escapeHtml(mention.caracteristicas.classe_semantica)} · [${mention.intervalo.inicio}, ${mention.intervalo.fim})${mention.mencao_pai_id ? ` · dentro de ${escapeHtml(mention.mencao_pai_id)}` : ""}</span>
    </li>
  `}).join("");
  return `
    <section class="mention-source">
      <h4>${escapeHtml(title)} <small>${escapeHtml(sourceLabel)}</small></h4>
      <ul class="mention-list">${items}</ul>
    </section>
  `;
}

function renderMentions(mentions, resolutions) {
  const fromContext = mentions.filter(item => item.origem === "contexto_anterior");
  const fromParagraph = mentions.filter(item => item.origem === "paragrafo");
  const resolutionByMention = new Map(resolutions.map(item => [item.mencao_id, item]));
  mentionMap.innerHTML = `
    <header>
      <div>
        <h3 id="mention-title">Menções detectadas</h3>
        <p>Cada menção mostra o referente atribuído ou o estado pendente.</p>
      </div>
      <span>${mentions.length} ${mentions.length === 1 ? "menção" : "menções"}</span>
    </header>
    ${renderMentionGroup("Contexto anterior", fromContext, "apoio referencial", resolutionByMention)}
    ${renderMentionGroup("Parágrafo principal", fromParagraph, "origem das proposições", resolutionByMention)}
  `;
}

function renderPropositions(propositions, frames) {
  const frameById = new Map(frames.map(item => [item.id, item]));
  propositionList.innerHTML = propositions.map((prop, index) => {
    const frame = frameById.get(prop.atribuicao_id);
    const negation = prop.operadores.negacao ? `sim — marcador “${prop.operadores.negacao}”` : "não detectada";
    const modality = prop.operadores.modalidade ? humanize(prop.operadores.modalidade) : "não marcada";
    const negationClass = prop.operadores.negacao ? "operator-alert" : "operator-none";
    const modalityClass = prop.operadores.modalidade ? "operator-alert" : "operator-none";
    const participantText = prop.participantes.length
      ? prop.participantes.map(participant => `<span class="participant-line"><strong>${escapeHtml(humanize(participant.papel))}</strong> · ${escapeHtml(participant.mencao)}</span>`).join("")
      : `<span class="operator-alert">não localizado</span>`;
    const mentionText = prop.participantes.length
      ? prop.participantes.map(participant => `<span class="participant-line">${escapeHtml(participant.mencao_id)} · [${participant.intervalo.inicio}, ${participant.intervalo.fim})</span>`).join("")
      : `<span class="operator-none">sem menção vinculada</span>`;
    const referentText = prop.participantes.length
      ? prop.participantes.map(participant => `<span class="participant-line ${participant.referente_id ? "reference-value" : "operator-none"}">${escapeHtml(humanize(participant.papel))}: ${participant.referente_id ? escapeHtml(participant.referente_id) : "não resolvido"}</span>`).join("")
      : `<span class="operator-none">não resolvido</span>`;
    const attributionState = frame?.estado || prop.atribuicao.estado;
    return `
      <li class="proposition-card" style="animation-delay:${Math.min(index * 45, 360)}ms">
        <div class="card-top">
          <span class="proposition-id">${escapeHtml(prop.id)}</span>
          <div class="card-badges">
            <span class="status-chip ${escapeHtml(attributionState)}">${escapeHtml(attributionState)}</span>
            <span class="polarity-chip ${escapeHtml(prop.polaridade)}">${escapeHtml(prop.polaridade)}</span>
            <span class="confidence">${Math.round(prop.confianca * 100)}% confiança</span>
          </div>
        </div>
        <h3 class="proposition-title">${escapeHtml(prop.descricao)}</h3>
        <dl class="field-grid">
          <div class="field">
            <dt>Predicado</dt>
            <dd>${escapeHtml(prop.predicado)} <span class="operator-none">(“${escapeHtml(prop.forma_textual)}”)</span></dd>
          </div>
          <div class="field">
            <dt>Participante principal</dt>
            <dd>${participantText}</dd>
          </div>
          <div class="field">
            <dt>Menção vinculada</dt>
            <dd>${mentionText}</dd>
          </div>
          <div class="field">
            <dt>Referente</dt>
            <dd>${referentText}</dd>
          </div>
          <div class="field">
            <dt>Atribuição</dt>
            <dd>${escapeHtml(frame?.fonte.rotulo || prop.atribuicao.fonte)} · ${escapeHtml(humanize(frame?.modo || prop.atribuicao.modo))}${prop.atribuicao_id ? ` · ${escapeHtml(prop.atribuicao_id)}` : ""}</dd>
          </div>
          <div class="field">
            <dt>Negação</dt>
            <dd class="${negationClass}">${escapeHtml(negation)}</dd>
          </div>
          <div class="field">
            <dt>Modalidade</dt>
            <dd class="${modalityClass}">${escapeHtml(modality)}</dd>
          </div>
          <div class="field">
            <dt>Polaridade</dt>
            <dd>${escapeHtml(prop.polaridade)}</dd>
          </div>
        </dl>
        <blockquote class="evidence">“${escapeHtml(prop.evidencia.texto)}”<span>[${prop.evidencia.intervalo.inicio}, ${prop.evidencia.intervalo.fim})</span></blockquote>
      </li>
    `;
  }).join("");
}

function renderError(message) {
  emptyState.hidden = true;
  analysisOutput.hidden = false;
  graphMap.innerHTML = "";
  referenceMap.innerHTML = "";
  mentionMap.innerHTML = "";
  propositionList.innerHTML = `<li class="error-state">${escapeHtml(message)}</li>`;
  resultStats.hidden = true;
}

async function renderAnalysis() {
  const text = paragraphInput.value.trim();
  const context = contextInput.value.trim();
  if (!text) {
    renderError("Insira um parágrafo antes de iniciar a análise.");
    paragraphInput.focus();
    return;
  }

  const label = analyzeButton.querySelector("span");
  const originalLabel = label.textContent;
  analyzeButton.disabled = true;
  label.textContent = "Analisando…";

  try {
    const response = await fetch("/api/analisar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paragrafo: text, contexto_anterior: context || null })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail?.[0]?.msg || data.detail || "Não foi possível analisar o parágrafo.");

    emptyState.hidden = true;
    analysisOutput.hidden = false;
    renderGraph(data);
    renderReferences(data.referentes, data.resolucoes, data.mencoes);
    renderMentions(data.mencoes, data.resolucoes);
    if (data.proposicoes.length) renderPropositions(data.proposicoes, data.quadros_atribuicao);
    else propositionList.innerHTML = `<li class="error-state">${escapeHtml(data.alertas[0] || "Nenhuma proposição identificada.")}</li>`;

    const summary = data.resumo;
    resultStats.innerHTML = `
      <span class="mini-chip">${summary.proposicoes} proposições</span>
      <span class="mini-chip">${summary.mencoes} menções</span>
      <span class="mini-chip">${summary.referentes} referentes</span>
      <span class="mini-chip">${summary.resolucoes_resolvidas} resolvidas</span>
      ${summary.resolucoes_ambiguas ? `<span class="mini-chip warning">${summary.resolucoes_ambiguas} ambíguas</span>` : ""}
      <span class="mini-chip">${summary.operadores} operadores</span>
      <span class="mini-chip">${summary.relacoes} relações</span>
      <span class="mini-chip">${summary.negacoes} negações</span>
      <span class="mini-chip">${summary.atribuicoes_marcadas} atribuídas</span>
    `;
    resultStats.hidden = false;
  } catch (error) {
    renderError(error.message || "Falha inesperada durante a análise.");
  } finally {
    analyzeButton.disabled = false;
    label.textContent = originalLabel;
  }
}

paragraphInput.addEventListener("input", updateCount);
analyzeButton.addEventListener("click", renderAnalysis);
exampleButton.addEventListener("click", () => {
  paragraphInput.value = exampleParagraph;
  contextInput.value = exampleContext;
  contextBox.open = true;
  updateCount();
  renderAnalysis();
});
clearButton.addEventListener("click", () => {
  paragraphInput.value = "";
  contextInput.value = "";
  updateCount();
  emptyState.hidden = false;
  analysisOutput.hidden = true;
  resultStats.hidden = true;
  paragraphInput.focus();
});

paragraphInput.value = exampleParagraph;
contextInput.value = exampleContext;
contextBox.open = true;
updateCount();

