const state = {
  dashboard: null,
  currentTab: "menu-principal",
  currentTimeframe: "4H",
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

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const setActiveTab = (tabId) => {
  state.currentTab = tabId;
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tabId);
  });
};

const getDecisionMap = () => {
  const entries = (state.dashboard?.asset_decisions || []).map((decision) => [decision.asset, decision]);
  return new Map(entries);
};

const renderTimeframeSwitches = () => {
  document.querySelectorAll("[data-timeframe-group]").forEach((host) => {
    host.innerHTML = ["4H", "1D"].map((timeframe) => `
      <button class="timeframe-chip ${state.currentTimeframe === timeframe ? "active" : ""}" data-timeframe="${timeframe}">
        ${timeframe}
      </button>
    `).join("");
  });
  document.querySelectorAll("[data-timeframe]").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentTimeframe = button.dataset.timeframe;
      renderTimeframeSwitches();
      renderChartAssets();
      renderIndicatorAssets();
    });
  });
};

const drawLineChart = (container, series, options = {}) => {
  if (!container) return;
  const validSeries = series.filter((line) => Array.isArray(line.values) && line.values.some(Number.isFinite));
  if (!validSeries.length) {
    container.innerHTML = "<p class='muted'>Sem dados suficientes para desenhar este gráfico.</p>";
    return;
  }

  const width = 760;
  const height = 210;
  const padding = 16;
  const allValues = validSeries.flatMap((line) => line.values).filter(Number.isFinite);
  const min = options.min ?? Math.min(...allValues);
  const max = options.max ?? Math.max(...allValues);
  const totalPoints = Math.max(...validSeries.map((line) => line.values.length));
  const scaleX = (index) => padding + (index / Math.max(totalPoints - 1, 1)) * (width - padding * 2);
  const scaleY = (value) => {
    if (max === min) return height / 2;
    return height - padding - ((value - min) / (max - min)) * (height - padding * 2);
  };
  const makePath = (values) => values
    .map((value, index) => `${index === 0 ? "M" : "L"} ${scaleX(index)} ${scaleY(value)}`)
    .join(" ");

  const thresholdPaths = (options.thresholds || []).map((threshold) => {
    const y = scaleY(threshold.value);
    return `<line x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}" stroke="${threshold.color}" stroke-dasharray="4 4" opacity="0.35"></line>`;
  }).join("");

  const linePaths = validSeries.map((line) => `
    <path d="${makePath(line.values)}" fill="none" stroke="${line.color}" stroke-width="${line.strokeWidth || 2}" stroke-linecap="round" opacity="${line.opacity || 1}"></path>
  `).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      ${thresholdPaths}
      ${linePaths}
    </svg>
  `;
};

const drawCandlestickChart = (container, candles) => {
  if (!container) return;
  if (!candles || !candles.length) {
    container.innerHTML = "<p class='muted'>Sem candles suficientes para este ativo.</p>";
    return;
  }

  const width = 760;
  const height = 240;
  const padding = 18;
  const highs = candles.map((candle) => candle.high).filter(Number.isFinite);
  const lows = candles.map((candle) => candle.low).filter(Number.isFinite);
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const scaleX = (index) => padding + (index / Math.max(candles.length, 1)) * (width - padding * 2);
  const scaleY = (value) => {
    if (max === min) return height / 2;
    return height - padding - ((value - min) / (max - min)) * (height - padding * 2);
  };
  const candleWidth = Math.max(4, (width - padding * 2) / Math.max(candles.length, 1) * 0.52);

  const shapes = candles.map((candle, index) => {
    const x = scaleX(index);
    const openY = scaleY(candle.open);
    const closeY = scaleY(candle.close);
    const highY = scaleY(candle.high);
    const lowY = scaleY(candle.low);
    const rising = candle.close >= candle.open;
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(Math.abs(closeY - openY), 2);
    const color = rising ? "#92efb4" : "#f27e8c";
    return `
      <line x1="${x}" y1="${highY}" x2="${x}" y2="${lowY}" stroke="${color}" stroke-width="1.2" opacity="0.82"></line>
      <rect x="${x - candleWidth / 2}" y="${bodyTop}" width="${candleWidth}" height="${bodyHeight}" rx="2" fill="${color}" opacity="0.88"></rect>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      ${shapes}
    </svg>
  `;
};

const renderOverview = (overview) => {
  document.getElementById("overview-title").textContent = overview.title || "Menu Principal";
  document.getElementById("overview-subtitle").textContent = overview.subtitle || "";
  const cardsHost = document.getElementById("overview-cards");
  cardsHost.innerHTML = (overview.cards || []).map((card) => `
    <article class="overview-card">
      <p class="metric-label">${escapeHtml(card.label)}</p>
      <strong>${escapeHtml(card.value)}</strong>
      <p class="muted">${escapeHtml(card.detail)}</p>
    </article>
  `).join("");

  document.getElementById("macroflow-does").innerHTML = (overview.macroflow_does || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  document.getElementById("market-notes").innerHTML = (overview.market_notes || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
};

const renderChartAssets = () => {
  const host = document.getElementById("chart-assets-grid");
  if (!host) return;
  const decisionMap = getDecisionMap();
  host.innerHTML = "";

  (state.dashboard?.market_assets || []).forEach((asset) => {
    const timeframe = state.currentTimeframe;
    const chartPayload = asset.charts?.[timeframe] || { candles: [] };
    const decision = decisionMap.get(asset.asset);
    const card = document.createElement("article");
    card.className = "asset-card panel";
    card.innerHTML = `
      <div class="asset-top">
        <div>
          <p class="eyebrow">${escapeHtml(asset.asset)}</p>
          <h3>${escapeHtml(asset.label)}</h3>
          <p class="muted">${escapeHtml(asset.description)}</p>
        </div>
        <span class="tag subtle">${decision ? escapeHtml(decision.execution_status) : "monitoramento"}</span>
      </div>
      <div class="latest-metrics">
        <div class="metric-box">
          <p class="metric-label">Preço</p>
          <strong>${formatNumber(asset.latest?.price, 4)}</strong>
          <p class="muted">Var. ${formatPercent(asset.latest?.change_pct_4h)}</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">Volume 4H</p>
          <strong>${formatNumber(asset.latest?.volume_4h, 0)}</strong>
          <p class="muted">Base Yahoo reamostrada</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">RSI Diário</p>
          <strong>${formatNumber(asset.latest?.rsi_daily, 2)}</strong>
          <p class="muted">Momentum do ativo</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">Visualização</p>
          <strong>${timeframe}</strong>
          <p class="muted">${escapeHtml(asset.ticker)}</p>
        </div>
      </div>
      <div class="chart-box"></div>
    `;
    drawCandlestickChart(card.querySelector(".chart-box"), chartPayload.candles || []);
    host.appendChild(card);
  });
};

const renderIndicatorAssets = () => {
  const host = document.getElementById("indicator-assets-grid");
  if (!host) return;
  const decisionMap = getDecisionMap();
  host.innerHTML = "";

  (state.dashboard?.market_assets || []).forEach((asset) => {
    const timeframe = state.currentTimeframe;
    const indicatorPayload = asset.charts?.[timeframe]?.indicators || [];
    const quantPayload = asset.charts?.[timeframe]?.quant_indicators || [];
    const quantReport = asset.quant_report || {};
    const decision = decisionMap.get(asset.asset);
    const priceSeries = [
      { color: "#dbc46d", values: indicatorPayload.map((item) => Number(item.close)) },
      { color: "#b9c2cf", values: indicatorPayload.map((item) => Number(item.pmd)) },
      { color: "#92efb4", values: indicatorPayload.map((item) => Number(item.ema_fast)) },
      { color: "#f27e8c", values: indicatorPayload.map((item) => Number(item.ema_slow)) },
    ];
    const quantSeries = [
      { color: "#92efb4", values: quantPayload.map((item) => Number(item.vwap)), strokeWidth: 2.2 },
      { color: "#dbc46d", values: quantPayload.map((item) => Number(item.vwap_rolling)), strokeWidth: 1.8 },
      { color: "#f6a04d", values: quantPayload.map((item) => Number(item.poc)), strokeWidth: 1.8 },
    ];
    const rsiSeries = [
      { color: "#92efb4", values: indicatorPayload.map((item) => Number(item.rsi)), strokeWidth: 2.2 },
    ];

    const card = document.createElement("article");
    card.className = "asset-card panel";
    card.innerHTML = `
      <div class="asset-top">
        <div>
          <p class="eyebrow">${escapeHtml(asset.asset)}</p>
          <h3>${escapeHtml(asset.label)}</h3>
          <p class="muted">${decision ? escapeHtml(decision.stage_reason) : escapeHtml(asset.description)}</p>
        </div>
        <span class="tag">${timeframe}</span>
      </div>
      <div class="indicator-details">
        <div class="stack-list">
          <div class="chart-box indicator-price-chart"></div>
          <div class="chart-box indicator-quant-chart"></div>
          <div class="chart-box indicator-rsi-chart"></div>
        </div>
        <div class="stack-list">
          <div class="decision-box quant-decision-box">
            <p class="metric-label">Score quant / regime / sinal</p>
            <strong>${formatNumber(quantReport.score, 0)} | ${escapeHtml(quantReport.regime || "-")} | ${escapeHtml(quantReport.signal || "HOLD")}</strong>
            <p class="muted">${escapeHtml(quantReport.status || "Sem status quant")}</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">VWAP / POC / ADX / ATR</p>
            <strong>${formatNumber(quantReport.vwap, 4)} / ${formatNumber(quantReport.poc, 4)} / ${formatNumber(quantReport.adx, 2)} / ${formatNumber(quantReport.atr, 4)}</strong>
            <p class="muted">Volume ${escapeHtml(quantReport.volume || "-")} | volatilidade ${escapeHtml(quantReport.volatilidade || "-")}</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">PMD / MME9 / MME21</p>
            <strong>${formatNumber(asset.latest?.pmd, 4)} / ${formatNumber(asset.latest?.ema_fast, 4)} / ${formatNumber(asset.latest?.ema_slow, 4)}</strong>
            <p class="muted">Leitura estrutural do setup em ${timeframe}.</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">RSI e direção</p>
            <strong>${formatNumber(asset.latest?.rsi_daily, 2)} | ${decision ? escapeHtml(decision.technical_direction) : "Monitoramento"}</strong>
            <p class="muted">${decision ? `Status ${escapeHtml(decision.execution_status)}` : "Ativo não operacional, exibido para leitura contextual."}</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">Analise explicativa</p>
            <p class="muted">${escapeHtml(quantReport.explanation || "Sem explicacao quant disponivel.")}</p>
          </div>
          <ul class="list-clean">
            ${(asset.indicator_notes || []).map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
          </ul>
        </div>
      </div>
    `;

    drawLineChart(card.querySelector(".indicator-price-chart"), priceSeries);
    drawLineChart(card.querySelector(".indicator-quant-chart"), quantSeries);
    drawLineChart(card.querySelector(".indicator-rsi-chart"), rsiSeries, {
      min: 0,
      max: 100,
      thresholds: [
        { value: 45, color: "#f27e8c" },
        { value: 55, color: "#dbc46d" },
      ],
    });
    host.appendChild(card);
  });
};

const renderNews = (newsCenter) => {
  document.getElementById("news-title").textContent = newsCenter.title || "Notícias do Mercado Financeiro";
  document.getElementById("news-summary").textContent = newsCenter.summary || "";
  document.getElementById("news-status").textContent = newsCenter.status || "planejamento";
  document.getElementById("news-sources").innerHTML = (newsCenter.sources || []).map((item) => `
    <div class="stack-item">
      <p class="metric-label">${escapeHtml(item.source)}</p>
      <strong>${escapeHtml(item.title)}</strong>
      <p class="muted">${escapeHtml(item.description)}</p>
    </div>
  `).join("");
  document.getElementById("news-bias-framework").innerHTML = (newsCenter.bias_framework || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  document.getElementById("news-implementation").innerHTML = (newsCenter.implementation_tasks || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
};

const renderSettings = (settingsPanel) => {
  const form = document.getElementById("settings-form");
  if (!form) return;
  document.getElementById("settings-note").textContent = settingsPanel.runtime_note || "";
  document.getElementById("save-settings-button").textContent = settingsPanel.save_label || "Salvar configurações";
  document.getElementById("refresh-button").textContent = settingsPanel.operational_button_label || "Iniciar Macroflow";

  form.innerHTML = (settingsPanel.groups || []).map((group) => `
    <section class="setting-group panel">
      <div class="setting-group-header">
        <p class="eyebrow">${escapeHtml(group.title)}</p>
        <p>${escapeHtml(group.description)}</p>
      </div>
      <div class="setting-group-fields">
        ${(group.fields || []).map((field) => {
          const isSelect = field.type === "select";
          const control = isSelect
            ? `<select data-env="${field.env}" data-secret="${field.secret ? "1" : "0"}">
                ${(field.options || []).map((option) => `
                  <option value="${escapeHtml(option)}" ${String(field.value) === String(option) ? "selected" : ""}>${escapeHtml(option)}</option>
                `).join("")}
              </select>`
            : `<input
                type="${field.type || "text"}"
                data-env="${field.env}"
                data-secret="${field.secret ? "1" : "0"}"
                value="${escapeHtml(field.value || "")}"
                placeholder="${escapeHtml(field.configured ? "Chave configurada" : (field.placeholder || ""))}"
                step="${escapeHtml(field.step || "")}"
              />`;
          return `
            <div class="setting-field">
              <label>${escapeHtml(field.label)}</label>
              ${control}
              <small>${escapeHtml(field.help || "")}</small>
            </div>
          `;
        }).join("")}
      </div>
    </section>
  `).join("");
};

const renderDashboard = (dashboard) => {
  state.dashboard = dashboard;
  state.currentTimeframe = dashboard.summary?.default_chart_timeframe || state.currentTimeframe || "4H";

  const macro = dashboard.macro_context || {};
  document.getElementById("headline-status").textContent = macro.nao_operar ? "Não operar" : "Operável";
  document.getElementById("headline-time").textContent = dashboard.generated_at || "-";
  document.getElementById("sidebar-headline").textContent = dashboard.summary?.headline || "Sem headline";
  document.getElementById("sidebar-time").textContent = dashboard.generated_at
    ? `Atualizado em ${dashboard.generated_at}`
    : "Sem atualização recente";

  renderTimeframeSwitches();
  renderOverview(dashboard.market_overview || {});
  renderChartAssets();
  renderIndicatorAssets();
  renderNews(dashboard.news_center || {});
  renderSettings(dashboard.settings_panel || {});
};

const loadDashboard = async () => {
  const response = await fetch("/api/dashboard");
  if (!response.ok) throw new Error("Falha ao carregar o dashboard.");
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
    button.textContent = state.dashboard?.settings_panel?.operational_button_label || "Iniciar Macroflow";
  }
};

const saveSettings = async () => {
  const button = document.getElementById("save-settings-button");
  const feedback = document.getElementById("settings-feedback");
  const values = {};

  document.querySelectorAll("#settings-form [data-env]").forEach((input) => {
    const env = input.dataset.env;
    const secret = input.dataset.secret === "1";
    const value = String(input.value ?? "").trim();
    if (secret && !value) return;
    values[env] = value;
  });

  button.disabled = true;
  feedback.textContent = "Salvando...";
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao salvar configurações");

    state.dashboard = state.dashboard || {};
    state.dashboard.settings_panel = payload.settings;
    renderSettings(payload.settings);
    const chartField = payload.settings.groups
      .flatMap((group) => group.fields)
      .find((field) => field.env === "MACROFLOW_CHART_DEFAULT_TIMEFRAME");
    if (chartField?.value) {
      state.currentTimeframe = chartField.value;
      renderTimeframeSwitches();
      renderChartAssets();
      renderIndicatorAssets();
    }
    feedback.textContent = "Configurações salvas. Clique em Iniciar Macroflow para aplicar a nova coleta.";
  } catch (error) {
    feedback.textContent = error.message;
  } finally {
    button.disabled = false;
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });
  document.getElementById("refresh-button")?.addEventListener("click", refreshDashboard);
  document.getElementById("save-settings-button")?.addEventListener("click", saveSettings);
  setActiveTab(state.currentTab);
  try {
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});
