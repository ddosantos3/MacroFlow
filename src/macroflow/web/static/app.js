const state = {
  dashboard: null,
};

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));
};

const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${formatNumber(value, 2)}%`;
};

const drawChart = (container, series) => {
  if (!container) return;
  if (!series || !series.length) {
    container.innerHTML = "<p class='muted'>Sem histórico suficiente para desenhar o gráfico.</p>";
    return;
  }

  const width = 760;
  const height = 210;
  const padding = 18;
  const values = series.flatMap((point) => [point.close, point.ema_fast, point.ema_slow]).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const scaleX = (index) => padding + (index / Math.max(series.length - 1, 1)) * (width - padding * 2);
  const scaleY = (value) => {
    if (max === min) return height / 2;
    return height - padding - ((value - min) / (max - min)) * (height - padding * 2);
  };

  const toPath = (key) => series
    .map((point, index) => `${index === 0 ? "M" : "L"} ${scaleX(index)} ${scaleY(point[key])}`)
    .join(" ");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="closeGradient" x1="0" x2="1">
          <stop offset="0%" stop-color="#d7c06e"/>
          <stop offset="100%" stop-color="#f4efb5"/>
        </linearGradient>
      </defs>
      <path d="${toPath("close")}" fill="none" stroke="url(#closeGradient)" stroke-width="2.4" stroke-linecap="round"></path>
      <path d="${toPath("ema_fast")}" fill="none" stroke="#90f3b4" stroke-width="1.8" stroke-linecap="round" opacity="0.95"></path>
      <path d="${toPath("ema_slow")}" fill="none" stroke="#f67d8d" stroke-width="1.8" stroke-linecap="round" opacity="0.88"></path>
    </svg>
  `;
};

const renderMacroGrid = (macro) => {
  const grid = document.getElementById("macro-grid");
  if (!grid) return;
  const items = [
    { label: "DXY", value: formatNumber(macro.dxy_fred, 2), detail: `RSI14 ${formatNumber(macro.dxy_rsi14, 2)}` },
    { label: "US10Y", value: formatNumber(macro.us10y_fred, 2), detail: `Delta 5d ${formatNumber(macro.us10y_delta_5d, 2)}` },
    { label: "SPX 4H", value: formatNumber(macro.spx_delta_5x4h, 2), detail: "Variação 5x4h" },
    { label: "Filtro", value: macro.nao_operar ? "TRAVADO" : "LIBERADO", detail: macro.motivo_nao_operar },
  ];
  grid.innerHTML = items.map((item) => `
    <div class="decision-stat">
      <p class="metric-label">${item.label}</p>
      <strong>${item.value}</strong>
      <p class="muted">${item.detail}</p>
    </div>
  `).join("");
};

const renderSourceHealth = (healthItems) => {
  const host = document.getElementById("source-health");
  const okCount = healthItems.filter((item) => item.ok).length;
  document.getElementById("metric-health").textContent = `${okCount}/${healthItems.length || 0}`;
  if (!host) return;
  host.innerHTML = healthItems.map((item) => `
    <div class="health-row">
      <div>
        <strong><span class="status-dot ${item.ok ? "status-ok" : "status-bad"}"></span>${item.source}</strong>
        <p class="muted">${item.message}</p>
      </div>
      <span class="tag ${item.ok ? "" : "subtle"}">${item.last_updated || "sem timestamp"}</span>
    </div>
  `).join("");
};

const renderDecisionCard = (decision) => {
  const wrapper = document.createElement("article");
  wrapper.className = "decision-card panel";
  wrapper.innerHTML = `
    <div class="decision-top">
      <div>
        <p class="eyebrow">${decision.asset}</p>
        <h3>${decision.label}</h3>
        <p class="muted">${decision.stage_reason}</p>
      </div>
      <span class="tag">${decision.execution_status}</span>
    </div>
    <div class="decision-metrics">
      <div class="decision-stat">
        <p class="metric-label">Macro x Técnico</p>
        <strong>${decision.macro_direction} / ${decision.technical_direction}</strong>
        <p class="muted">${decision.macro_aligned ? "convergente" : "desalinhado"}</p>
      </div>
      <div class="decision-stat">
        <p class="metric-label">Entrada / Stop</p>
        <strong>${formatNumber(decision.entry_price, 4)} / ${formatNumber(decision.stop_price, 4)}</strong>
        <p class="muted">MME21 como stop móvel</p>
      </div>
      <div class="decision-stat">
        <p class="metric-label">Risco / Quantidade</p>
        <strong>${formatNumber(decision.position_sizing?.risco_por_unidade, 4)} / ${formatNumber(decision.position_sizing?.quantidade, 2)}</strong>
        <p class="muted">${decision.position_sizing?.observacao || "Sizing indisponível"}</p>
      </div>
    </div>
    <div class="chart-box"></div>
    <div class="decision-metrics">
      <div class="decision-stat">
        <p class="metric-label">Preço</p>
        <strong>${formatNumber(decision.price, 4)}</strong>
        <p class="muted">Variação ${formatPercent(decision.change_pct)}</p>
      </div>
      <div class="decision-stat">
        <p class="metric-label">PMD / MME9</p>
        <strong>${formatNumber(decision.pmd, 4)} / ${formatNumber(decision.ema_fast, 4)}</strong>
        <p class="muted">Touch: ${decision.touch_detected_at || "-"}</p>
      </div>
      <div class="decision-stat">
        <p class="metric-label">MME21 / Confirmação</p>
        <strong>${formatNumber(decision.ema_slow, 4)} / ${decision.confirmation_at || "-"}</strong>
        <p class="muted">${decision.exit_condition}</p>
      </div>
    </div>
  `;
  drawChart(wrapper.querySelector(".chart-box"), decision.history || []);
  return wrapper;
};

const renderDashboard = (dashboard) => {
  state.dashboard = dashboard;
  const macro = dashboard.macro_context;
  document.getElementById("headline-status").textContent = macro.nao_operar ? "Não operar" : "Operável";
  document.getElementById("headline-time").textContent = dashboard.generated_at || "-";
  document.getElementById("sidebar-headline").textContent = dashboard.summary?.headline || "Sem headline";
  document.getElementById("metric-regime").textContent = macro.regime || "-";
  document.getElementById("metric-regime-detail").textContent = macro.motivo_nao_operar || "Sem motivo";
  document.getElementById("metric-score").textContent = macro.score ?? "-";
  document.getElementById("metric-decision").textContent = dashboard.summary?.has_actionable_trade ? "Setup ativo" : "Em observação";
  document.getElementById("metric-decision-detail").textContent = macro.nao_operar ? macro.motivo_nao_operar : "Macro e técnico exibidos por ativo";
  document.getElementById("metric-health").textContent = "-";
  document.getElementById("macro-tag").textContent = macro.headline || "Sem headline";
  document.getElementById("terminal-report").textContent = dashboard.terminal_report || "Sem relatório.";
  document.getElementById("excel-path").textContent = dashboard.summary?.excel_path || "-";

  renderMacroGrid(macro);
  renderSourceHealth(dashboard.source_health || []);

  const grid = document.getElementById("decisions-grid");
  grid.innerHTML = "";
  (dashboard.asset_decisions || []).forEach((decision) => grid.appendChild(renderDecisionCard(decision)));
};

const loadDashboard = async () => {
  const response = await fetch("/api/dashboard");
  const dashboard = await response.json();
  renderDashboard(dashboard);
};

const refreshDashboard = async () => {
  const button = document.getElementById("refresh-button");
  button.disabled = true;
  button.textContent = "Atualizando...";
  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao atualizar");
    renderDashboard(payload.state);
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Atualizar dados";
  }
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("refresh-button")?.addEventListener("click", refreshDashboard);
  loadDashboard();
});
