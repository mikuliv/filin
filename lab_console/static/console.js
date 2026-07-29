"use strict";

const one = (selector, root = document) => root.querySelector(selector);
const all = (selector, root = document) => [...root.querySelectorAll(selector)];

document.addEventListener("DOMContentLoaded", () => {
  const logout = one("#logout");
  if (logout) logout.addEventListener("click", async () => {
    await fetch("/api/console/v1/logout", {method: "POST", headers: {"Content-Type": "application/json", "X-CSRF-Token": logout.dataset.csrf}, body: "{}"});
    location.href = "/login";
  });

  const sidebarToggle = one(".sidebar-toggle");
  if (sidebarToggle) sidebarToggle.addEventListener("click", () => {
    if (innerWidth <= 1120) document.body.classList.toggle("sidebar-open");
    else document.body.classList.toggle("sidebar-collapsed");
  });
  one(".refresh-button")?.addEventListener("click", () => location.reload());

  all(".tab-list [data-tab-target]").forEach(button => button.addEventListener("click", () => {
    all(".tab-list [data-tab-target]").forEach(x => { x.classList.remove("active"); x.setAttribute("aria-selected", "false"); });
    all(".tab-panel").forEach(x => x.classList.remove("active"));
    button.classList.add("active"); button.setAttribute("aria-selected", "true"); one("#" + button.dataset.tabTarget)?.classList.add("active");
  }));

  all("[data-raw-panel]").forEach(panel => {
    const content = one("[data-raw-content]", panel); const original = content?.textContent || "";
    one("[data-copy-raw]", panel)?.addEventListener("click", async event => { await navigator.clipboard.writeText(original); event.currentTarget.textContent = "Скопировано"; });
    one("[data-raw-search]", panel)?.addEventListener("input", event => {
      const query = event.target.value.trim().toLowerCase();
      content.textContent = query ? original.split("\n").filter(line => line.toLowerCase().includes(query)).join("\n") || "Совпадений нет" : original;
    });
  });

  all("[data-stage-filters] button").forEach(button => button.addEventListener("click", () => {
    all("[data-stage-filters] button").forEach(x => x.classList.remove("active")); button.classList.add("active");
    all("[data-stage-line]").forEach(card => card.hidden = button.dataset.filter !== "all" && card.dataset.stageLine !== button.dataset.filter);
  }));

  all("[data-bundle-toggle]").forEach(button => button.addEventListener("click", () => {
    const detail = one(`[data-bundle-detail="${button.dataset.bundleToggle}"]`); detail.hidden = !detail.hidden; button.textContent = detail.hidden ? "Подробнее" : "Скрыть";
  }));

  all("[data-table-search]").forEach(input => input.addEventListener("input", () => {
    const query = input.value.toLowerCase(); all(`#${input.dataset.tableSearch} tbody tr:not(.bundle-detail)`).forEach(row => row.hidden = !row.textContent.toLowerCase().includes(query));
  }));

  let timelineScale = 1;
  const timeline = one("[data-timeline-canvas] svg");
  const applyTimeline = () => { if (timeline) timeline.style.transform = `scaleX(${timelineScale})`; if (timeline) timeline.style.transformOrigin = "left center"; };
  all("[data-timeline-zoom]").forEach(button => button.addEventListener("click", () => { timelineScale = Math.min(2.2, Math.max(.7, timelineScale + (button.dataset.timelineZoom === "in" ? .15 : -.15))); applyTimeline(); }));
  one("[data-timeline-all]")?.addEventListener("click", () => { timelineScale = 1; applyTimeline(); });
  all("[data-timeline-layer]").forEach(input => input.addEventListener("change", () => { const layer = one(`[data-layer="${input.dataset.timelineLayer}"]`); if (layer) layer.style.display = input.checked ? "" : "none"; }));

  const viewport = one("[data-graph-viewport]"); let graphScale = 1; let graphX = 0; let graphY = 0; let dragging = false; let start = [0,0];
  const applyGraph = () => { if (viewport) viewport.setAttribute("transform", `translate(${graphX} ${graphY}) scale(${graphScale})`); };
  all("[data-graph-zoom]").forEach(button => button.addEventListener("click", () => { graphScale = Math.min(2.5, Math.max(.5, graphScale + (button.dataset.graphZoom === "in" ? .15 : -.15))); applyGraph(); }));
  one("[data-graph-reset]")?.addEventListener("click", () => { graphScale = 1; graphX = 0; graphY = 0; applyGraph(); all("[data-graph-canvas] .graph-node").forEach(n => n.classList.remove("selected")); });
  const graphCanvas = one("[data-graph-canvas]");
  graphCanvas?.addEventListener("pointerdown", e => { if (e.target.closest(".graph-node")) return; dragging = true; start = [e.clientX - graphX, e.clientY - graphY]; graphCanvas.setPointerCapture(e.pointerId); });
  graphCanvas?.addEventListener("pointermove", e => { if (!dragging) return; graphX = e.clientX - start[0]; graphY = e.clientY - start[1]; applyGraph(); });
  graphCanvas?.addEventListener("pointerup", () => dragging = false);
  all("[data-graph-canvas] .graph-node").forEach(node => {
    const select = () => { all("[data-graph-canvas] .graph-node").forEach(n => n.classList.remove("selected")); node.classList.add("selected"); one("[data-node-title]").textContent = node.querySelector(".node-label")?.textContent || "Узел"; one("[data-node-type-value]").textContent = node.dataset.nodeType; one("[data-node-id-value]").textContent = node.dataset.nodeId; };
    node.addEventListener("click", select); node.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") select(); });
  });
  all("[data-graph-type]").forEach(input => input.addEventListener("change", () => all(`[data-node-type="${input.dataset.graphType}"]`).forEach(node => node.style.display = input.checked ? "" : "none")));
  one("[data-graph-edges]")?.addEventListener("change", e => all(".graph-edge").forEach(edge => edge.style.display = e.target.checked ? "" : "none"));
  one("[data-graph-search]")?.addEventListener("input", event => { const q = event.target.value.toLowerCase(); all("[data-graph-canvas] .graph-node").forEach(node => node.style.opacity = !q || node.dataset.nodeId.toLowerCase().includes(q) ? "1" : ".12"); });

  all("[data-comparison]").forEach(button => button.addEventListener("click", () => {
    let value = {}; try { value = JSON.parse(button.dataset.comparison || "{}"); } catch (_) { value = {}; }
    const labels = {equally_supported:"Опора одинакова",better_supported:"Строка сильнее",less_supported:"Строка слабее",incomparable:"Несопоставимы",insufficient_data:"Мало данных"};
    one("[data-comparison-title]").textContent = button.getAttribute("aria-label");
    one("[data-comparison-id]").textContent = value.comparison_id || "диагональ";
    one("[data-comparison-result]").textContent = labels[value.comparison_result] || "та же гипотеза";
    one("[data-comparison-basis]").textContent = value.comparison_basis ? "Проверены подтверждения, противоречия и открытые разрывы по прозрачному правилу сопоставления." : "Сравнение гипотезы с самой собой не выполняется.";
    const decisive = (value.decisive_assessment_ids || []).length;
    one("[data-comparison-explanation]").textContent = value.comparison_result === "equally_supported" && decisive === 0 ? "Ни у одной гипотезы в паре нет решающего сведения, которое давало бы ей преимущество. Это не делает гипотезы одинаковыми или истинными." : `Решающих оценок в этой паре: ${decisive}. Результат остаётся относительным и не является окончательным выводом.`;
    one("[data-comparison-limit]").textContent = (value.limitations || ["Не является рейтингом или окончательным решением."]).join("; ");
  }));
});

document.addEventListener("DOMContentLoaded", () => {
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const one = (selector, root = document) => root.querySelector(selector);
  const caseToken = location.pathname.split("/").filter(Boolean)[2] || "";
  const api = async (url, method = "GET", body = null, csrf = "") => {
    const options = { method, headers: {} };
    if (body !== null) { options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); }
    if (csrf) options.headers["X-CSRF-Token"] = csrf;
    const response = await fetch(url, options);
    const value = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    if (!response.ok) throw new Error(value.detail || `HTTP ${response.status}`);
    return value;
  };

  const applyCaseCatalog = () => {
    const cards = all("[data-case-card]");
    const values = Object.fromEntries(all("[data-case-filter]").map(x => [x.dataset.caseFilter, x.value]));
    cards.forEach(card => { card.hidden = Object.entries(values).some(([key, value]) => value && card.dataset[key] !== value); });
    const sort = one("[data-case-sort]")?.value || "name";
    const key = { gaps:"gapCount", hypotheses:"hypothesisCount", reviewed:"reviewed" }[sort] || sort;
    cards.sort((a,b) => sort === "name" ? a.dataset[key].localeCompare(b.dataset[key], "ru") : (Number(b.dataset[key]) || 0) - (Number(a.dataset[key]) || 0));
    cards.forEach(card => one("[data-case-grid]")?.append(card));
    const empty = one("[data-case-empty]"); if (empty) empty.hidden = cards.some(card => !card.hidden);
  };
  all("[data-case-filter],[data-case-sort]").forEach(x => x.addEventListener("change", applyCaseCatalog));

  all("[data-review-start]").forEach(button => button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await api(`/api/console/v1/cases/${caseToken}/reviews`, "POST", { case_id:button.dataset.caseId, card_id:button.dataset.cardId, source_bundle_sha256:button.dataset.bundleSha, source_semantic_sha256:button.dataset.semanticSha }, button.dataset.csrf);
      location.assign(`/ui/cases/${caseToken}/review`);
    } catch (error) { button.disabled = false; button.textContent = error.message; }
  }));
  const progressPanel = one("[data-review-progress]");
  if (progressPanel) {
    const step = progressPanel.dataset.section === "review" || progressPanel.dataset.section === "export" ? "decision" : progressPanel.dataset.section;
    const completed = JSON.parse(progressPanel.dataset.completed || "[]");
    if (step !== "decision" && !completed.includes(step)) completed.push(step);
    api(`/api/console/v1/reviews/${progressPanel.dataset.reviewId}/progress`, "PATCH", { current_step:step, completed_step_ids:completed, unresolved_item_ids:JSON.parse(progressPanel.dataset.unresolved || "[]") }, progressPanel.dataset.csrf).catch(() => {});
  }

  const caseTimeline = one("[data-case-timeline]");
  const caseTimelineItems = all("[data-timeline-item]");
  const timelineMilliseconds = value => new Date(value).getTime();
  const timelineDomain = caseTimelineItems.flatMap(item => [timelineMilliseconds(item.dataset.observation), timelineMilliseconds(item.dataset.delivery)]);
  const timelineMinimum = timelineDomain.length ? Math.min(...timelineDomain) : 0;
  const timelineMaximum = timelineDomain.length ? Math.max(...timelineDomain) : timelineMinimum;
  const timelinePosition = value => timelineMaximum === timelineMinimum ? 50 : 7 + ((timelineMilliseconds(value) - timelineMinimum) / (timelineMaximum - timelineMinimum)) * 86;
  const formatDelay = milliseconds => `${(milliseconds / 1000).toLocaleString("ru-RU", {minimumFractionDigits:3, maximumFractionDigits:3})} с`;
  const applyTimelineMode = mode => {
    if (!caseTimeline) return;
    caseTimeline.dataset.timelineMode = mode;
    const notes = {
      observation:"Положение рассчитано по исходному времени наблюдения.",
      delivery:"Положение пересчитано по времени поступления события в лабораторный контур.",
      comparison:"Основная точка — наблюдение, светлая точка — доставка; линия между ними показывает задержку, а не причинность."
    };
    one("[data-timeline-mode-note]").textContent = notes[mode];
    caseTimelineItems.forEach(item => {
      const observation = item.dataset.observation;
      const delivery = item.dataset.delivery;
      const observationPosition = timelinePosition(observation);
      const deliveryPosition = timelinePosition(delivery);
      const displayedPosition = mode === "delivery" ? deliveryPosition : observationPosition;
      const delay = timelineMilliseconds(delivery) - timelineMilliseconds(observation);
      item.style.left = `${displayedPosition}%`;
      item.style.setProperty("--delivery-shift", `${Math.max(-90, Math.min(90, (deliveryPosition - observationPosition) * caseTimeline.clientWidth / 100))}px`);
      item.classList.toggle("comparison", mode === "comparison");
      one("[data-event-label]", item).textContent = mode === "delivery" ? `Доставка ${item.dataset.eventIndex}` : mode === "comparison" ? `Событие ${item.dataset.eventIndex} · задержка ${formatDelay(delay)}` : `Наблюдение ${item.dataset.eventIndex}`;
      one("[data-time-label]", item).textContent = mode === "comparison" ? `${observation.slice(11,23)} → ${delivery.slice(11,23)}` : (mode === "delivery" ? delivery : observation).slice(11,23);
    });
  };
  all("[data-timeline-modes] button").forEach(button => button.addEventListener("click", () => {
    all("[data-timeline-modes] button").forEach(x => x.classList.remove("active")); button.classList.add("active"); applyTimelineMode(button.dataset.mode);
  }));
  if (caseTimeline) {
    applyTimelineMode("observation");
    window.addEventListener("resize", () => applyTimelineMode(caseTimeline.dataset.timelineMode || "observation"));
  }
  all("[data-timeline-item]").forEach(button => button.addEventListener("click", () => {
    const value = JSON.parse(button.dataset.timelineItem); const panel = one("[data-timeline-explanation]");
    panel.innerHTML = `<p class="eyebrow">Почему элемент расположен здесь</p><h3>${value.timeline_item_id}</h3><p>Наблюдение: ${value.observation_time}<br>Доставка: ${value.delivery_time}<br>Clock domain: ${value.clock_domain}<br>Точность: ${value.precision}<br>Основание порядка: ${value.ordering_basis}</p><p class="limitation">Порядок не доказывает причинность.</p>`;
  }));

  const graphDetailDefault = `<p class="eyebrow">Свойства</p><h3>Выберите узел или ребро</h3><p>Соседи будут подсвечены, остальной граф — приглушён. Повторный клик или клик по пустому месту снимает выделение.</p><button class="button secondary" data-graph-path disabled>Показать путь к гипотезе</button>`;
  const clearCaseGraphSelection = () => {
    all("[data-node],[data-edge]").forEach(x => x.classList.remove("selected", "dim"));
    const detail = one("[data-graph-detail]");
    if (detail) detail.innerHTML = graphDetailDefault;
  };
  const applyCaseGraphMode = button => {
    clearCaseGraphSelection();
    all("[data-graph-modes] button").forEach(x => x.classList.remove("active")); button.classList.add("active");
    const visible = { simplified:["fact","gap"], facts:["fact"], facts_temporal:["fact","event"], facts_structural:["fact","group"], gaps:["fact","gap"], hypotheses:["fact","gap","hypothesis"], full:["fact","event","group","gap","hypothesis"] }[button.dataset.mode];
    const visibleIds = new Set();
    all("[data-node]").forEach(node => { const value=JSON.parse(node.dataset.node); const shown=visible.includes(value.type); node.style.display=shown?"":"none"; if(shown) visibleIds.add(value.id); });
    all("[data-edge]").forEach(edge => { const value=JSON.parse(edge.dataset.edge); edge.style.display=visibleIds.has(value.left)&&visibleIds.has(value.right)?"":"none"; });
  };
  all("[data-graph-modes] button").forEach(button => button.addEventListener("click", () => applyCaseGraphMode(button)));
  const initialGraphMode = one("[data-graph-modes] button.active");
  if (initialGraphMode) applyCaseGraphMode(initialGraphMode);
  const selectGraph = target => {
    if (target.classList.contains("selected")) { clearCaseGraphSelection(); return; }
    const value = JSON.parse(target.dataset.node || target.dataset.edge); const isNode = Boolean(target.dataset.node);
    all("[data-node],[data-edge]").forEach(x => { x.classList.remove("selected"); x.classList.add("dim"); }); target.classList.remove("dim"); target.classList.add("selected");
    if (isNode) all("[data-edge]").filter(x => { const e=JSON.parse(x.dataset.edge), source=e.source||e.left, target=e.target||e.right; return source===value.id || target===value.id; }).forEach(x => x.classList.remove("dim"));
    one("[data-graph-detail]").innerHTML = `<p class="eyebrow">${isNode ? "Узел" : "Ребро"}</p><h3>${value.label || value.id}</h3><pre>${JSON.stringify(value,null,2)}</pre><p class="limitation">Отношение не является утверждением о причинности.</p><button class="button secondary" data-graph-path>Показать путь к гипотезе</button>`;
    const pathButton = one("[data-graph-path]");
    pathButton.disabled = !isNode;
    pathButton.addEventListener("click", () => {
      const nodes = new Map(all("[data-node]").map(element => { const node=JSON.parse(element.dataset.node); return [node.id,{...node,element}]; }));
      const edges = all("[data-edge]").map(element => { const edge=JSON.parse(element.dataset.edge); return {...edge,source:edge.source||edge.left,target:edge.target||edge.right,element}; });
      const target = [...nodes.values()].find(node => node.type === "hypothesis");
      const queue=[[value.id,[]]], visited=new Set([value.id]); let path=[];
      while(queue.length){ const [id,used]=queue.shift(); if(target&&id===target.id){path=used;break;} for(const edge of edges){const next=edge.source===id?edge.target:edge.target===id?edge.source:null;if(next&&!visited.has(next)){visited.add(next);queue.push([next,[...used,edge]]);}} }
      all("[data-node],[data-edge]").forEach(x=>x.classList.add("dim"));
      const ids=new Set([value.id]); path.forEach(edge=>{edge.element.classList.remove("dim");ids.add(edge.source);ids.add(edge.target);}); ids.forEach(id=>nodes.get(id)?.element.classList.remove("dim"));
      pathButton.textContent = path.length ? `Путь показан: ${path.length} связей` : "Связный путь отсутствует";
    });
  };
  all("[data-node],[data-edge]").forEach(target => { target.addEventListener("click",()=>selectGraph(target)); target.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" ")selectGraph(target);}); });
  one("[data-v044-graph]")?.addEventListener("click", event => { if (!event.target.closest("[data-node],[data-edge]")) clearCaseGraphSelection(); });
  all("[data-gap-show]").forEach(button => button.addEventListener("click", () => { const impact=one("[data-gap-impact]",button.closest("[data-gap-card]")); impact.hidden=!impact.hidden; button.textContent=impact.hidden?"Показать влияние":"Скрыть влияние"; }));
  all("[data-v044-comparison]").forEach(button => button.addEventListener("click", () => {
    const value=JSON.parse(button.dataset.v044Comparison);
    one("[data-comparison-detail]").innerHTML=`<p class="eyebrow">Объяснение ячейки</p><h3>${value.result_label}</h3><p class="comparison-pair"><strong>${value.left_ref}</strong> ${value.left_name}<br><strong>${value.right_ref}</strong> ${value.right_name}</p><p class="comparison-result">${value.result_explanation}</p><h4>Почему такой результат</h4><p>${value.evidence_summary}</p><dl><div><dt>Основание</dt><dd>${value.basis_label}</dd></div><div><dt>Ограничение</dt><dd>${(value.limitations||["Не является окончательным выводом."]).join("; ")}</dd></div></dl><details><summary>Технические сведения</summary><div><b>Правило:</b> ${value.comparison_basis}<br><b>ID:</b> ${value.comparison_id}</div></details>`;
  }));
  one("[data-differences-only]")?.addEventListener("change", event => all("[data-v044-comparison]").forEach(button => { button.closest("td").style.opacity=event.target.checked && JSON.parse(button.dataset.v044Comparison).comparison_result==="equally_supported"?".18":"1"; }));

  all("[data-review-check]").forEach(input => input.addEventListener("change", async () => { try { await api(`/api/console/v1/reviews/${input.dataset.reviewId}/checks`,"POST",{item_id:input.dataset.itemId,checked:input.checked},input.dataset.csrf); } catch(error) { input.checked=!input.checked; alert(error.message); } }));
  all("[data-review-item]").forEach(button => button.addEventListener("click", async () => { try { await api(`/api/console/v1/reviews/${button.dataset.reviewId}/${button.dataset.entityType}s/${button.dataset.entityId}/state`,"POST",{state:button.dataset.state},button.dataset.csrf); button.textContent="Сохранено"; button.disabled=true; } catch(error) { button.textContent=error.message; } }));
  one("[data-review-note]")?.addEventListener("click", async event => { const button=event.currentTarget; try { await api(`/api/console/v1/reviews/${button.dataset.reviewId}/notes`,"POST",{text:one("[data-review-note-text]").value},button.dataset.csrf); location.reload(); } catch(error) { button.textContent=error.message; } });
  one("[data-review-complete]")?.addEventListener("click", async event => { const button=event.currentTarget; const message=one("[data-review-message]"); try { await api(`/api/console/v1/reviews/${button.dataset.reviewId}/complete`,"POST",{operator_summary:one("[data-review-summary]").value,next_manual_step:one("[data-review-next]").value,limitations:["Лабораторные синтетические данные; окончательное определение отсутствует."]},button.dataset.csrf); message.textContent="Рассмотрение завершено без окончательного определения."; location.assign(`/ui/cases/${caseToken}/export`); } catch(error) { message.textContent=error.message; } });
  one("[data-review-export]")?.addEventListener("click", async event => { const button=event.currentTarget; try { const value=await api(`/api/console/v1/reviews/${button.dataset.reviewId}/export`,"POST",{},button.dataset.csrf); const output=one("[data-export-result]"); output.hidden=false; output.textContent=JSON.stringify(value,null,2); } catch(error) { button.textContent=error.message; } });
  one("[data-run-filter]")?.addEventListener("change", event => all("[data-run-card]").forEach(card => { card.hidden = Boolean(event.target.value && card.dataset.status !== event.target.value); }));
  one("[data-run-create]")?.addEventListener("click", async event => {
    const root=event.currentTarget.closest("[data-run-wizard]"), template=one("[data-run-template]",root), selected=template.selectedOptions[0], message=one("[data-run-message]",root); event.currentTarget.disabled=true;
    try { const run=await api("/api/console/v1/lab-runs","POST",{template_id:template.value,candidate_token:one("[data-run-candidate]",root).value,input_token:one("[data-run-input]",root).value,run_kind:selected.dataset.kind,environment_profile:selected.dataset.environment},root.dataset.csrf); await api(`/api/console/v1/lab-runs/${run.run_token}/validate`,"POST",{},root.dataset.csrf); const dry=await api(`/api/console/v1/lab-runs/${run.run_token}/dry-run`,"POST",{},root.dataset.csrf); message.textContent=dry.passed?"Пробный запуск без выполнения пройден. План готов к явному подтверждению.":"Пробный запуск без выполнения отклонён."; if(confirm("План проверен. Выполнить разрешённое автономное воспроизведение?")){await api(`/api/console/v1/lab-runs/${run.run_token}/execute`,"POST",{confirmed:true,recovery_boundary:null},root.dataset.csrf);location.assign(`/ui/lab-runs/${run.run_token}`);}}
    catch(error){message.textContent=error.message;event.currentTarget.disabled=false;}
  });
  one("[data-comparison-submit]")?.addEventListener("click", async event => { const root=event.currentTarget.closest("[data-comparison-create]"),message=one("[data-comparison-message]",root); event.currentTarget.disabled=true; try{const value=await api("/api/console/v1/run-comparisons","POST",{left_run_token:one("[data-left-run]",root).value,right_run_token:one("[data-right-run]",root).value},root.dataset.csrf);location.assign(`/ui/run-comparisons/${value.comparison_token}`);}catch(error){message.textContent=error.message;event.currentTarget.disabled=false;} });
  one("[data-comparison-export-submit]")?.addEventListener("click", async event => { const root=event.currentTarget.closest("[data-comparison-export]"),message=one("[data-comparison-export-message]",root),result=one("[data-comparison-export-result]",root); event.currentTarget.disabled=true; try{const value=await api(`/api/console/v1/run-comparisons/${root.dataset.comparisonToken}/export`,"POST",{},root.dataset.csrf);result.textContent=JSON.stringify(value,null,2);result.hidden=false;message.textContent="Экспорт подготовлен локально; исходные запуски не изменены.";}catch(error){message.textContent=error.message;}finally{event.currentTarget.disabled=false;} });
  one("[data-proposal-submit]")?.addEventListener("click", async event => { const root=event.currentTarget.closest("[data-proposal-create]"),message=one("[data-proposal-message]",root); event.currentTarget.disabled=true; try{const value=await api("/api/console/v1/candidate-proposals","POST",{data_catalog_id:one("[data-proposal-data]",root).value,split_id:one("[data-proposal-split]",root).value,recipe_id:one("[data-proposal-recipe]",root).value},root.dataset.csrf);await api(`/api/console/v1/candidate-proposals/${value.proposal_token}/validate`,"POST",{},root.dataset.csrf);const dry=await api(`/api/console/v1/candidate-proposals/${value.proposal_token}/dry-run`,"POST",{},root.dataset.csrf);message.textContent=dry.passed?"Пробный запуск без выполнения пройден. Черновик создан без назначения идентификатора кандидата.":"Пробный запуск без выполнения отклонён.";location.assign(`/ui/candidate-proposals/${value.proposal_token}`);}catch(error){message.textContent=error.message;event.currentTarget.disabled=false;} });
  one("[data-review-comparison-start]")?.addEventListener("click", async event => { const root=event.currentTarget.closest("[data-create-comparison-review]"),message=one("[data-review-comparison-message]",root); event.currentTarget.disabled=true; try{const value=await api(`/api/console/v1/run-comparisons/${root.dataset.comparisonToken}/reviews`,"POST",{},root.dataset.csrf);location.assign(`/ui/comparison-reviews/${value.review_id}`);}catch(error){message.textContent=error.message;event.currentTarget.disabled=false;} });
  one("[data-comparison-review-save]")?.addEventListener("click", async event => { const root=event.currentTarget.closest("[data-comparison-review-form]"),message=one("[data-comparison-review-message]",root); event.currentTarget.disabled=true; try{const value=await api(`/api/console/v1/comparison-reviews/${root.dataset.reviewId}/complete`,"POST",{operator_summary:one("[data-comparison-review-summary]",root).value,recommended_manual_action:one("[data-comparison-review-action]",root).value,completed_steps:["provenance","comparability","inputs","candidate","environment","metrics","classes","episodes","cards","gaps","explanations","questions","decision"],reviewed_dimensions:["provenance","comparability","inputs","environment","metrics","classes","episodes","cards","gaps","hypotheses"],unresolved_differences:[],limitations:["Лабораторные синтетические данные; решение о кандидате отсутствует."]},root.dataset.csrf);message.textContent=value.status;location.reload();}catch(error){message.textContent=error.message;event.currentTarget.disabled=false;} });
  all("[data-help-open]").forEach(button => button.addEventListener("click",()=>one("[data-help-drawer]").hidden=false)); one("[data-help-close]")?.addEventListener("click",()=>one("[data-help-drawer]").hidden=true);
});
