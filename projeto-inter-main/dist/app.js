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
const analysisAlerts = document.querySelector("#analysis-alerts");
const centralIdea = document.querySelector("#central-idea");
const synthesis = document.querySelector("#synthesis");
const analyzeLabel = analyzeButton.querySelector("span");
const jsonFileInput = document.querySelector("#json-file");
const jsonStatus = document.querySelector("#json-status");
const paragraphPicker = document.querySelector("#paragraph-picker");
const jsonParagraphSelect = document.querySelector("#json-paragraph");
const jsonSummary = document.querySelector("#json-summary");

let activeController = null;
let activeRequestId = 0;
let ingestionController = null;
let loadedDocument = null;
let ingestionResult = null;
let jsonSelectionCurrent = false;
let fillingFromJson = false;

function setBusy(busy) {
  analyzeButton.disabled = busy;
  analyzeLabel.textContent = busy ? "Analisando…" : "Analisar estrutura";
}

function cancelActiveAnalysis() {
  activeRequestId += 1;
  if (activeController) activeController.abort();
  activeController = null;
  setBusy(false);
}

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

function evidenceLabel(evidence) {
  if (!evidence?.intervalo) return "sem intervalo de evidência";
  return `[${evidence.intervalo.inicio}, ${evidence.intervalo.fim})`;
}

function errorMessage(data, fallback) {
  const details = data?.detail;
  if (Array.isArray(details)) {
    return details
      .slice(0, 4)
      .map(item => {
        if (item?.mensagem) return `${item.caminho || "$"}: ${item.mensagem}`;
        return item?.msg || String(item);
      })
      .join(" · ");
  }
  return typeof details === "string" ? details : fallback;
}

function setJsonStatus(message, state = "idle") {
  jsonStatus.textContent = message;
  jsonStatus.dataset.state = state;
}

function resetJsonDocument() {
  if (ingestionController) ingestionController.abort();
  ingestionController = null;
  loadedDocument = null;
  ingestionResult = null;
  jsonSelectionCurrent = false;
  jsonFileInput.value = "";
  jsonParagraphSelect.innerHTML = "";
  paragraphPicker.hidden = true;
  jsonSummary.textContent = "";
  setJsonStatus("nenhum arquivo");
}

function selectJsonParagraph() {
  if (!ingestionResult) return;
  const paragraph = ingestionResult.paragrafos.find(item => item.id === jsonParagraphSelect.value);
  if (!paragraph) return;
  const previous = ingestionResult.paragrafos
    .filter(item => item.ordem < paragraph.ordem)
    .sort((a, b) => b.ordem - a.ordem)[0];
  fillingFromJson = true;
  paragraphInput.value = paragraph.texto;
  contextInput.value = previous?.texto || "";
  contextBox.open = Boolean(previous);
  fillingFromJson = false;
  jsonSelectionCurrent = true;
  setJsonStatus(`${paragraph.rotulo} selecionado`, "valid");
  updateCount();
  cancelActiveAnalysis();
}

async function loadJsonFile() {
  const file = jsonFileInput.files?.[0];
  if (!file) return;
  cancelActiveAnalysis();
  if (ingestionController) ingestionController.abort();
  const controller = new AbortController();
  ingestionController = controller;
  loadedDocument = null;
  ingestionResult = null;
  jsonSelectionCurrent = false;
  paragraphPicker.hidden = true;
  setJsonStatus("validando…", "loading");

  try {
    if (file.size > 25 * 1024 * 1024) throw new Error("O arquivo ultrapassa o limite de 25 MB desta interface.");
    const raw = JSON.parse(await file.text());
    const response = await fetch("/api/documentos/validar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(raw),
      signal: controller.signal
    });
    const data = await response.json();
    if (!response.ok) throw new Error(errorMessage(data, "O JSON não passou pela validação."));
    if (data.schema_version !== "0.5.0") throw new Error(`Versão de ingestão incompatível: ${data.schema_version || "ausente"}.`);

    loadedDocument = raw;
    ingestionResult = data;
    jsonParagraphSelect.innerHTML = data.paragrafos.map(item => `
      <option value="${escapeHtml(item.id)}">${escapeHtml(item.rotulo)} · [${item.intervalo_original.inicio}, ${item.intervalo_original.fim}) · ${[...item.texto].length} caracteres</option>
    `).join("");
    const summary = data.resumo;
    jsonSummary.textContent = `Documento ${data.fonte.documento_id} · ${summary.paragrafos} parágrafos · ${summary.periodos} períodos · ${summary.tokens} tokens · ${summary.artefatos} vetores de ${summary.dimensao_vetores} dimensões`;
    paragraphPicker.hidden = false;
    setJsonStatus("JSON válido", "valid");
    selectJsonParagraph();
  } catch (error) {
    if (error.name === "AbortError") return;
    resetJsonDocument();
    setJsonStatus(error instanceof SyntaxError ? "JSON malformado" : "arquivo rejeitado", "error");
    renderError(error instanceof SyntaxError ? "O arquivo não contém JSON válido." : error.message);
  } finally {
    if (ingestionController === controller) ingestionController = null;
  }
}

function renderAlerts(alerts) {
  const items = Array.isArray(alerts) ? alerts : [];
  analysisAlerts.hidden = items.length === 0;
  analysisAlerts.querySelector("ul").innerHTML = items
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function renderCentralIdea(idea, essentialIds) {
  if (!idea || idea.estado === "indeterminada") {
    centralIdea.innerHTML = `
      <header><div><h3 id="central-idea-title">Ideia central</h3><p>Hipótese revisável apoiada no texto original.</p></div></header>
      <p class="quiet-message">O registro atual não foi suficiente para propor uma ideia central.</p>
    `;
    return;
  }
  const evidence = idea.evidencias?.[0];
  const alternatives = (idea.alternativas || []).map((item, index) => `
    <article class="central-alternative">
      <div><span>Alternativa ${index + 1}</span><strong>${Math.round(item.pontuacao * 100)} pontos</strong></div>
      <blockquote>“${escapeHtml(item.texto)}”</blockquote>
      <small>${item.proposicao_ids.map(id => escapeHtml(id)).join(" · ")} · ${escapeHtml(evidenceLabel(item.evidencias?.[0]))}</small>
    </article>
  `).join("");
  centralIdea.innerHTML = `
    <header>
      <div><h3 id="central-idea-title">Ideia central proposta</h3><p>Seleção extrativa; permanece aberta à revisão.</p></div>
      <span>${Math.round(idea.confianca * 100)}% confiança</span>
    </header>
    <blockquote class="central-statement">“${escapeHtml(idea.texto)}”<small>${escapeHtml(evidenceLabel(evidence))}</small></blockquote>
    <div class="essential-row"><strong>Conteúdo essencial</strong>${essentialIds.map(id => `<span>${escapeHtml(id)}</span>`).join("")}</div>
    <ul class="central-reasons">${idea.razoes.map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
    ${alternatives ? `<details class="central-alternatives"><summary>Examinar ${idea.alternativas.length} ${idea.alternativas.length === 1 ? "alternativa" : "alternativas"}</summary><div>${alternatives}</div></details>` : ""}
  `;
}

function renderSynthesis(item, paraphrases) {
  if (!item || item.estado === "indeterminada") {
    synthesis.innerHTML = `
      <header><div><h3 id="synthesis-title">Síntese</h3><p>Texto apoiado no conteúdo essencial.</p></div></header>
      <p class="quiet-message">Não há conteúdo essencial suficiente para gerar a síntese.</p>
    `;
    return;
  }
  const coverage = item.cobertura;
  const coverageGroup = (label, ids) => `
    <div><dt>${escapeHtml(label)}</dt><dd>${ids.length ? ids.map(id => `<span>${escapeHtml(id)}</span>`).join("") : `<em>nenhum</em>`}</dd></div>
  `;
  const paraphraseCards = paraphrases.map(paraphrase => `
    <article class="paraphrase-card">
      <header><strong>${escapeHtml(paraphrase.id)}</strong><span>${Math.round(paraphrase.confianca * 100)}% confiança</span></header>
      <blockquote>“${escapeHtml(paraphrase.texto)}”</blockquote>
      <ul>${paraphrase.transformacoes.map(transformation => `
        <li>
          <strong>“${escapeHtml(transformation.original.texto)}” → “${escapeHtml(transformation.substituicao)}”</strong>
          <small>${escapeHtml(evidenceLabel(transformation.original))} · preserva ${[...transformation.preserva_operador_ids, ...transformation.preserva_relacao_ids].map(id => escapeHtml(id)).join(" · ")}</small>
        </li>
      `).join("")}</ul>
    </article>
  `).join("");
  synthesis.innerHTML = `
    <header>
      <div><h3 id="synthesis-title">Síntese extrativa</h3><p>Períodos originais selecionados pelo conteúdo essencial.</p></div>
      <span>${Math.round(item.confianca * 100)}% confiança</span>
    </header>
    <blockquote class="synthesis-text">${escapeHtml(item.texto)}</blockquote>
    <p class="synthesis-evidence">${item.evidencias.map(evidence => escapeHtml(evidenceLabel(evidence))).join(" · ")}</p>
    <dl class="coverage-grid">
      ${coverageGroup("Proposições", coverage.proposicao_ids)}
      ${coverageGroup("Operadores", coverage.operador_ids)}
      ${coverageGroup("Relações", coverage.relacao_ids)}
      ${coverageGroup("Participantes", coverage.mencao_ids)}
    </dl>
    ${item.alertas.length ? `<ul class="synthesis-alerts">${item.alertas.map(alert => `<li>${escapeHtml(alert)}</li>`).join("")}</ul>` : ""}
    <section class="paraphrase-section" aria-label="Paráfrases verificáveis">
      <h4>Paráfrases opcionais</h4>
      ${paraphraseCards || `<p class="paraphrase-state">Nenhuma equivalência discursiva segura se aplica a esta síntese.</p>`}
    </section>
  `;
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
      <div><strong>${escapeHtml(humanize(item.subtipo))}</strong><small>${escapeHtml(item.tipo)} · “${escapeHtml(item.marcador)}” · ${Math.round(item.confianca * 100)}% · ${escapeHtml(evidenceLabel(item.evidencia))}</small></div>
      <span class="scope-list">${item.escopo.map(id => escapeHtml(id)).join(" · ")}</span>
    </li>
  `).join("");
  const frames = data.quadros_atribuicao.map(item => `
    <li class="graph-item attribution-item">
      <span class="graph-id">${escapeHtml(item.id)}</span>
      <div><strong>${escapeHtml(humanize(item.modo))}</strong><small>${escapeHtml(item.fonte.rotulo)} · ${escapeHtml(item.estado)} · ${Math.round(item.confianca * 100)}%</small></div>
      <span class="scope-list">${item.escopo.map(id => escapeHtml(id)).join(" · ")}</span>
    </li>
  `).join("");
  const relations = data.relacoes.map(item => `
    <li class="relation-item">
      <span class="relation-endpoint">${escapeHtml(endpoint(item.origem_id))}</span>
      <span class="relation-type">${escapeHtml(humanize(item.tipo))}<small>${item.marcador ? `“${escapeHtml(item.marcador)}” · ` : ""}${Math.round(item.confianca * 100)}% · ${escapeHtml(evidenceLabel(item.evidencia))}</small></span>
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
        ${resolution.evidencias.length ? `<p><strong>Evidências:</strong> ${resolution.evidencias.map(item => `${escapeHtml(item.mencao_id)} ${escapeHtml(evidenceLabel(item))}`).join(" · ")}</p>` : ""}
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
      <span class="mention-meta">${escapeHtml(mention.caracteristicas.classe_semantica)} · ${Math.round(mention.confianca_deteccao * 100)}% · [${mention.intervalo.inicio}, ${mention.intervalo.fim})${mention.mencao_pai_id ? ` · dentro de ${escapeHtml(mention.mencao_pai_id)}` : ""}</span>
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

function renderPropositions(propositions, frames, essentialIds) {
  const frameById = new Map(frames.map(item => [item.id, item]));
  const essential = new Set(essentialIds || []);
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
      <li class="proposition-card ${essential.has(prop.id) ? "essential" : ""}" style="animation-delay:${Math.min(index * 45, 360)}ms">
        <div class="card-top">
          <span class="proposition-id">${escapeHtml(prop.id)}</span>
          <div class="card-badges">
            ${essential.has(prop.id) ? `<span class="essential-chip">essencial</span>` : ""}
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
  centralIdea.innerHTML = "";
  synthesis.innerHTML = "";
  referenceMap.innerHTML = "";
  mentionMap.innerHTML = "";
  propositionList.innerHTML = `<li class="error-state">${escapeHtml(message)}</li>`;
  renderAlerts([]);
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

  if (activeController) activeController.abort();
  const requestId = ++activeRequestId;
  const controller = new AbortController();
  activeController = controller;
  setBusy(true);

  try {
    const structured = jsonSelectionCurrent && loadedDocument && jsonParagraphSelect.value;
    const endpoint = structured ? "/api/analisar-json" : "/api/analisar";
    const payload = structured
      ? { documento: loadedDocument, paragrafo_id: jsonParagraphSelect.value }
      : { paragrafo: text, contexto_anterior: context || null };
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    const responseData = await response.json();
    if (requestId !== activeRequestId) return;
    if (!response.ok) throw new Error(errorMessage(responseData, "Não foi possível analisar o parágrafo."));
    if (structured && responseData.schema_version !== "0.8.0") {
      throw new Error(`Versão do fluxo estruturado incompatível: ${responseData.schema_version || "ausente"}.`);
    }
    const data = structured ? responseData.analise : responseData;
    if (data.schema_version !== "0.8.0") throw new Error(`Versão de resposta incompatível: ${data.schema_version || "ausente"}.`);

    emptyState.hidden = true;
    analysisOutput.hidden = false;
    renderCentralIdea(data.ideia_central, data.conteudo_essencial_ids);
    renderSynthesis(data.sintese, data.parafrases);
    renderGraph(data);
    renderReferences(data.referentes, data.resolucoes, data.mencoes);
    renderMentions(data.mencoes, data.resolucoes);
    renderAlerts(data.alertas);
    if (data.proposicoes.length) renderPropositions(data.proposicoes, data.quadros_atribuicao, data.conteudo_essencial_ids);
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
      <span class="mini-chip essential">${summary.conteudo_essencial} essenciais</span>
      <span class="mini-chip synthesis">${summary.sintese_caracteres} caracteres na síntese</span>
      <span class="mini-chip synthesis">${summary.parafrases} ${summary.parafrases === 1 ? "paráfrase" : "paráfrases"}</span>
      ${structured ? `<span class="mini-chip source">documento ${escapeHtml(responseData.fonte.documento_id)} · ${escapeHtml(responseData.paragrafo.rotulo)}</span>` : ""}
      <span class="mini-chip">contrato ${escapeHtml(data.schema_version)}</span>
    `;
    resultStats.hidden = false;
  } catch (error) {
    if (error.name === "AbortError") return;
    if (requestId !== activeRequestId) return;
    renderError(error.message || "Falha inesperada durante a análise.");
  } finally {
    if (requestId === activeRequestId) {
      activeController = null;
      setBusy(false);
    }
  }
}

paragraphInput.addEventListener("input", () => {
  updateCount();
  cancelActiveAnalysis();
  if (!fillingFromJson && loadedDocument) {
    jsonSelectionCurrent = false;
    setJsonStatus("texto editado", "edited");
  }
});
contextInput.addEventListener("input", () => {
  cancelActiveAnalysis();
  if (!fillingFromJson && loadedDocument) {
    jsonSelectionCurrent = false;
    setJsonStatus("texto editado", "edited");
  }
});
analyzeButton.addEventListener("click", renderAnalysis);
jsonFileInput.addEventListener("change", loadJsonFile);
jsonParagraphSelect.addEventListener("change", selectJsonParagraph);
exampleButton.addEventListener("click", () => {
  resetJsonDocument();
  paragraphInput.value = exampleParagraph;
  contextInput.value = exampleContext;
  contextBox.open = true;
  updateCount();
  renderAnalysis();
});
clearButton.addEventListener("click", () => {
  cancelActiveAnalysis();
  resetJsonDocument();
  paragraphInput.value = "";
  contextInput.value = "";
  updateCount();
  emptyState.hidden = false;
  analysisOutput.hidden = true;
  resultStats.hidden = true;
  renderAlerts([]);
  paragraphInput.focus();
});

paragraphInput.value = exampleParagraph;
contextInput.value = exampleContext;
contextBox.open = true;
updateCount();

