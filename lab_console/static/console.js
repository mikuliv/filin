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
  one("[data-graph-reset]")?.addEventListener("click", () => { graphScale = 1; graphX = 0; graphY = 0; applyGraph(); all(".graph-node").forEach(n => n.classList.remove("selected")); });
  const graphCanvas = one("[data-graph-canvas]");
  graphCanvas?.addEventListener("pointerdown", e => { if (e.target.closest(".graph-node")) return; dragging = true; start = [e.clientX - graphX, e.clientY - graphY]; graphCanvas.setPointerCapture(e.pointerId); });
  graphCanvas?.addEventListener("pointermove", e => { if (!dragging) return; graphX = e.clientX - start[0]; graphY = e.clientY - start[1]; applyGraph(); });
  graphCanvas?.addEventListener("pointerup", () => dragging = false);
  all(".graph-node").forEach(node => {
    const select = () => { all(".graph-node").forEach(n => n.classList.remove("selected")); node.classList.add("selected"); one("[data-node-title]").textContent = node.querySelector(".node-label")?.textContent || "Узел"; one("[data-node-type-value]").textContent = node.dataset.nodeType; one("[data-node-id-value]").textContent = node.dataset.nodeId; };
    node.addEventListener("click", select); node.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") select(); });
  });
  all("[data-graph-type]").forEach(input => input.addEventListener("change", () => all(`[data-node-type="${input.dataset.graphType}"]`).forEach(node => node.style.display = input.checked ? "" : "none")));
  one("[data-graph-edges]")?.addEventListener("change", e => all(".graph-edge").forEach(edge => edge.style.display = e.target.checked ? "" : "none"));
  one("[data-graph-search]")?.addEventListener("input", event => { const q = event.target.value.toLowerCase(); all(".graph-node").forEach(node => node.style.opacity = !q || node.dataset.nodeId.toLowerCase().includes(q) ? "1" : ".12"); });

  all("[data-comparison]").forEach(button => button.addEventListener("click", () => {
    let value = {}; try { value = JSON.parse(button.dataset.comparison || "{}"); } catch (_) { value = {}; }
    one("[data-comparison-title]").textContent = button.getAttribute("aria-label");
    one("[data-comparison-id]").textContent = value.comparison_id || "диагональ";
    one("[data-comparison-result]").textContent = value.comparison_result || "та же гипотеза";
    one("[data-comparison-basis]").textContent = value.comparison_basis || "Сравнение гипотезы с самой собой.";
    one("[data-comparison-limit]").textContent = (value.limitations || ["Не является рейтингом или окончательным решением."]).join("; ");
  }));
});
