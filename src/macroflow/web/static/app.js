const state = {
  dashboard: null,
  currentTab: "menu-principal",
  currentTimeframe: "4H",
  newsCountry: "ALL",
  newsImportance: "ALL",
  jarvisHistory: [],
};

let chartSequence = 0;

const setText = (id, value) => {
  const element = document.getElementById(id);
  if (!element) return null;
  element.textContent = value;
  return element;
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

const formatCompactNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value));
};

const assetEmoji = (asset) => ({
  USDBRL: "💵",
  BRA50: "📉",
  SPX: "🧭",
  NDX: "⚡",
  USA500: "🇺🇸",
  USAIND: "🏛️",
}[asset] || "📊");

const metricIcon = (label = "") => {
  const source = label.toLowerCase();
  if (source.includes("regime") || source.includes("macro")) return "🧭";
  if (source.includes("score")) return "🎯";
  if (source.includes("dxy") || source.includes("dolar")) return "💵";
  if (source.includes("yield") || source.includes("treasury") || source.includes("juros")) return "🏦";
  if (source.includes("not") || source.includes("news") || source.includes("calend")) return "🌍";
  if (source.includes("volume")) return "🌊";
  if (source.includes("sinal") || source.includes("trade")) return "⚡";
  return "✦";
};

const normalizeText = (value = "") => String(value || "").toLowerCase();

const toneFromText = (...values) => {
  const joined = normalizeText(values.filter(Boolean).join(" "));
  if (!joined) return "neutral";
  if (joined.includes("buy") || joined.includes("compra") || joined.includes("operavel") || joined.includes("online") || joined.includes("alta")) return "bullish";
  if (joined.includes("sell") || joined.includes("venda") || joined.includes("bloqueado") || joined.includes("error") || joined.includes("offline") || joined.includes("queda")) return "bearish";
  if (joined.includes("warning") || joined.includes("chaotic") || joined.includes("nao operar") || joined.includes("aten") || joined.includes("monitorar")) return "warning";
  if (joined.includes("jarvis") || joined.includes("ia")) return "violet";
  return "neutral";
};

const toneClass = (tone) => {
  if (tone === "bullish") return "bullish";
  if (tone === "bearish") return "bearish";
  if (tone === "warning") return "warning";
  if (tone === "info") return "info";
  if (tone === "violet") return "violet";
  return "";
};

const buildHelperPill = (label, tone = "neutral") => `
  <span class="helper-pill ${toneClass(tone)}">${escapeHtml(label)}</span>
`;

const renderBulls = (importance) => "🐂".repeat(Math.max(Number(importance) || 0, 0)) || "·";

const setActiveTab = (tabId) => {
  state.currentTab = tabId;
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
    button.setAttribute("aria-current", button.dataset.tab === tabId ? "page" : "false");
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
    container.classList.add("empty");
    container.innerHTML = "<p class='muted'>Sem dados suficientes para desenhar este grafico.</p>";
    return;
  }
  container.classList.remove("empty");

  const chartId = `chart-${++chartSequence}`;
  const width = 760;
  const height = 220;
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

  const gridLines = Array.from({ length: 5 }, (_, index) => {
    const y = padding + ((height - padding * 2) / 4) * index;
    return `<line class="chart-grid-line" x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}"></line>`;
  }).join("");

  const thresholdPaths = (options.thresholds || []).map((threshold) => {
    const y = scaleY(threshold.value);
    return `<line x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}" stroke="${threshold.color}" stroke-dasharray="4 4" opacity="0.35"></line>`;
  }).join("");

  const firstSeries = validSeries[0];
  const areaPath = `${makePath(firstSeries.values)} L ${scaleX(totalPoints - 1)} ${height - padding} L ${scaleX(0)} ${height - padding} Z`;
  const gradients = validSeries.map((line, index) => `
    <linearGradient id="${chartId}-line-${index}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="${line.color}" stop-opacity="0.28"></stop>
      <stop offset="45%" stop-color="${line.color}" stop-opacity="0.94"></stop>
      <stop offset="100%" stop-color="${line.color}" stop-opacity="0.72"></stop>
    </linearGradient>
  `).join("");

  const linePaths = validSeries.map((line, index) => {
    const lastIndex = line.values
      .map((value, valueIndex) => ({ value, valueIndex }))
      .filter((item) => Number.isFinite(item.value))
      .pop();
    return `
      <path class="chart-line" pathLength="1" d="${makePath(line.values)}" stroke="url(#${chartId}-line-${index})" stroke-width="${line.strokeWidth || 2.2}" opacity="${line.opacity || 1}"></path>
      ${lastIndex ? `<circle class="chart-dot" cx="${scaleX(lastIndex.valueIndex)}" cy="${scaleY(lastIndex.value)}" r="3.2" fill="${line.color}" style="color:${line.color}"></circle>` : ""}
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        ${gradients}
        <linearGradient id="${chartId}-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${firstSeries.color}" stop-opacity="0.24"></stop>
          <stop offset="100%" stop-color="${firstSeries.color}" stop-opacity="0"></stop>
        </linearGradient>
      </defs>
      ${gridLines}
      ${thresholdPaths}
      <path class="chart-area" d="${areaPath}" fill="url(#${chartId}-area)"></path>
      ${linePaths}
    </svg>
  `;
};

const drawCandlestickChart = (container, candles) => {
  if (!container) return;
  if (!candles || !candles.length) {
    container.classList.add("empty");
    container.innerHTML = "<p class='muted'>Sem candles suficientes para este ativo.</p>";
    return;
  }
  container.classList.remove("empty");

  const chartId = `candles-${++chartSequence}`;
  const width = 760;
  const height = 252;
  const padding = 18;
  const highs = candles.map((candle) => candle.high).filter(Number.isFinite);
  const lows = candles.map((candle) => candle.low).filter(Number.isFinite);
  const volumes = candles.map((candle) => Number(candle.volume) || 0);
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const scaleX = (index) => padding + (index / Math.max(candles.length, 1)) * (width - padding * 2);
  const scaleY = (value) => {
    if (max === min) return height / 2;
    return height - padding - ((value - min) / (max - min)) * (height - padding * 2);
  };
  const candleWidth = Math.max(4, (width - padding * 2) / Math.max(candles.length, 1) * 0.52);
  const volumeHeight = 34;
  const maxVolume = Math.max(...volumes, 1);

  const gridLines = Array.from({ length: 5 }, (_, index) => {
    const y = padding + ((height - padding * 2 - volumeHeight) / 4) * index;
    return `<line class="chart-grid-line" x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}"></line>`;
  }).join("");

  const volumeBars = candles.map((candle, index) => {
    const x = scaleX(index);
    const barHeight = ((Number(candle.volume) || 0) / maxVolume) * volumeHeight;
    return `<rect class="chart-volume-bar" x="${x - candleWidth / 2}" y="${height - padding - barHeight}" width="${candleWidth}" height="${barHeight}" rx="2"></rect>`;
  }).join("");

  const shapes = candles.map((candle, index) => {
    const x = scaleX(index);
    const openY = scaleY(candle.open);
    const closeY = scaleY(candle.close);
    const highY = scaleY(candle.high);
    const lowY = scaleY(candle.low);
    const rising = candle.close >= candle.open;
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(Math.abs(closeY - openY), 2);
    const colorClass = rising ? "chart-candle-up" : "chart-candle-down";
    const wickClass = rising ? "chart-wick-up" : "chart-wick-down";
    return `
      <line class="${wickClass}" x1="${x}" y1="${highY}" x2="${x}" y2="${lowY}" stroke-width="1.25" opacity="0.84"></line>
      <rect class="${colorClass}" x="${x - candleWidth / 2}" y="${bodyTop}" width="${candleWidth}" height="${bodyHeight}" rx="3" opacity="0.9"></rect>
    `;
  }).join("");

  const lastClose = candles.at(-1)?.close;
  const lastY = Number.isFinite(lastClose) ? scaleY(lastClose) : null;

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <radialGradient id="${chartId}-glow" cx="50%" cy="0%" r="80%">
          <stop offset="0%" stop-color="rgba(93, 242, 180, 0.22)"></stop>
          <stop offset="100%" stop-color="rgba(93, 242, 180, 0)"></stop>
        </radialGradient>
      </defs>
      <rect x="${padding}" y="${padding}" width="${width - padding * 2}" height="${height - padding * 2}" fill="url(#${chartId}-glow)" opacity="0.24"></rect>
      ${gridLines}
      ${volumeBars}
      ${shapes}
      ${lastY ? `<line class="chart-price-line" x1="${padding}" y1="${lastY}" x2="${width - padding}" y2="${lastY}"></line>` : ""}
      ${lastY ? `<text class="chart-price-label" x="${width - padding - 62}" y="${Math.max(lastY - 6, 14)}">${formatNumber(lastClose, 4)}</text>` : ""}
    </svg>
  `;
};

const renderSourceHealth = (sources = []) => {
  const host = document.getElementById("source-health-list");
  if (!host) return;
  if (!sources.length) {
    host.innerHTML = "<div class='source-item' data-status='warning'><p class='muted'>Sem dados de integridade carregados ainda.</p></div>";
    return;
  }
  host.innerHTML = sources.map((source) => {
    const status = String(source.status || source.health || "warning").toLowerCase();
    const detail = source.message || source.detail || source.note || "Sem detalhe adicional.";
    return `
      <article class="source-item" data-status="${escapeHtml(status)}">
        <div class="source-item-top">
          <p class="metric-label">${escapeHtml(source.source || source.label || "feed")}</p>
          <span class="source-status">
            <span class="source-status-dot"></span>
            ${escapeHtml(status)}
          </span>
        </div>
        <strong>${escapeHtml(source.updated_at || source.checked_at || source.status || "monitorado")}</strong>
        <p class="muted">${escapeHtml(detail)}</p>
      </article>
    `;
  }).join("");
};

const renderCommandCenter = (dashboard) => {
  const macro = dashboard.macro_context || {};
  const news = dashboard.news_center || {};
  const actionableTrades = (dashboard.quant_reports || []).filter((report) => ["BUY", "SELL"].includes(report.signal)).length;

  setText("hero-operation-headline", macro.headline || "Sem dados carregados");
  setText("hero-operation-reason", macro.motivo_nao_operar || "Sem bloqueio estrutural relevante no snapshot atual.");
  setText("hero-regime-value", macro.regime || "-");
  setText("hero-score-value", formatNumber(macro.score, 0));
  setText("hero-bias-value", news.risk_bias || "neutro");
  setText("hero-setup-value", String(actionableTrades));

  const highlightHost = document.getElementById("hero-highlights");
  highlightHost.innerHTML = [
    {
      label: "DXY / RSI",
      value: `${formatNumber(macro.dxy_fred, 2)} / ${formatNumber(macro.dxy_rsi14, 1)}`,
      detail: "Forca do dolar usada para contextualizar risco e inclinacao macro.",
    },
    {
      label: "US10Y / Delta",
      value: `${formatNumber(macro.us10y_fred, 2)} / ${formatNumber(macro.us10y_delta_5d, 2)}`,
      detail: "Juros longos e sua direcao recente para leitura de stress e liquidez.",
    },
    {
      label: "Calendario / Bias",
      value: `${news.high_impact_count || 0} eventos / ${news.risk_bias || "neutro"}`,
      detail: "Eventos macro de alta criticidade ampliando o contexto do Jarvis e do motor quant.",
    },
  ].map((item) => `
    <article class="hero-highlight">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <p>${escapeHtml(item.detail)}</p>
    </article>
  `).join("");
};

const renderOverview = (overview) => {
  setText("overview-title", overview.title || "Menu Principal");
  setText("overview-subtitle", overview.subtitle || "");
  const news = state.dashboard?.news_center || {};
  const macro = state.dashboard?.macro_context || {};
  const headline = (overview.macroflow_does || [])[0]
    || "Filtra o macro com DXY, Treasuries, SPX e calendario economico antes de considerar qualquer trade.";
  const process = (overview.macroflow_does || [])[1]
    || "Converte contexto em score, regime e sinal deterministico, mantendo bloqueios quando a qualidade cai.";
  const operation = (overview.market_notes || [])[0]
    || "Usa o macro como filtro institucional e o setup tecnico como gatilho operacional.";
  const newsSummary = news.summary
    || "Noticias e eventos economicos entram como camada complementar de vies e monitoramento.";

  const briefHost = document.getElementById("macroflow-brief");
  if (!briefHost) return;
  briefHost.innerHTML = `
    <div class="principal-brief-block">
      <span class="principal-brief-label">Como atua</span>
      <p><strong>${escapeHtml(headline)}</strong></p>
      <p>${escapeHtml(process)}</p>
    </div>
    <div class="principal-brief-divider"></div>
    <div class="principal-brief-block">
      <span class="principal-brief-label">Leitura operacional</span>
      <p><strong>Regime ${escapeHtml(macro.regime || "-")}</strong> com score ${formatNumber(macro.score, 0)}. ${escapeHtml(operation)}</p>
    </div>
    <div class="principal-brief-divider"></div>
    <div class="principal-brief-block">
      <span class="principal-brief-label">Noticias no contexto</span>
      <p><strong>${news.high_impact_count || 0} eventos criticos</strong> com vies <strong>${escapeHtml(news.risk_bias || "neutro")}</strong>.</p>
      <p>${escapeHtml(newsSummary)}</p>
    </div>
  `;
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
    const quantReport = asset.quant_report || {};
    const tone = toneFromText(quantReport.signal, decision?.execution_status, decision?.technical_direction);
    const card = document.createElement("article");
    card.className = "asset-card panel";
    card.dataset.tone = tone;
    card.innerHTML = `
      <div class="asset-top">
        <div class="asset-title">
          <span class="asset-icon">${assetEmoji(asset.asset)}</span>
          <div>
            <p class="eyebrow">${escapeHtml(asset.asset)}</p>
            <h3>${escapeHtml(asset.label)}</h3>
            <p class="muted">${escapeHtml(asset.description)}</p>
          </div>
        </div>
        <div class="signal-cluster">
          <span class="tag ${toneClass(tone)}">${escapeHtml(quantReport.signal || decision?.technical_direction || "MONITORAR")}</span>
          <span class="tag subtle">${decision ? escapeHtml(decision.execution_status) : "monitoramento"}</span>
        </div>
      </div>
      <div class="latest-metrics">
        <div class="metric-box" data-tone="${tone}">
          <p class="metric-label">Preço spot</p>
          <strong>${formatNumber(asset.latest?.price, 4)}</strong>
          <p class="muted">Var. ${formatPercent(asset.latest?.change_pct_4h)}</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">Volume 4H</p>
          <strong>${formatCompactNumber(asset.latest?.volume_4h)}</strong>
          <p class="muted">Base Yahoo reamostrada</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">RSI Diário</p>
          <strong>${formatNumber(asset.latest?.rsi_daily, 2)}</strong>
          <p class="muted">Momentum do ativo</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">Regime / score</p>
          <strong>${escapeHtml(quantReport.regime || "-")} / ${formatNumber(quantReport.score, 0)}</strong>
          <p class="muted">${timeframe} • ${escapeHtml(asset.ticker)}</p>
        </div>
      </div>
      <div class="chart-box"></div>
      <div class="signal-cluster">
        <span class="helper-pill ${toneClass(tone)}">${escapeHtml(decision?.technical_direction || "Sem direção técnica")}</span>
        <span class="helper-pill info">VWAP ${formatNumber(quantReport.vwap, 4)}</span>
        <span class="helper-pill warning">POC ${formatNumber(quantReport.poc, 4)}</span>
        <span class="helper-pill ${quantReport.volume === "acima da média" ? "bullish" : ""}">${escapeHtml(quantReport.volume || "volume sem leitura")}</span>
      </div>
      <p class="muted">${escapeHtml(decision?.stage_reason || quantReport.explanation || asset.description)}</p>
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
    const tone = toneFromText(quantReport.signal, quantReport.regime, decision?.execution_status);
    const priceSeries = [
      { color: "#f6c66f", values: indicatorPayload.map((item) => Number(item.close)) },
      { color: "#a6b3c9", values: indicatorPayload.map((item) => Number(item.pmd)) },
      { color: "#5df2b4", values: indicatorPayload.map((item) => Number(item.ema_fast)) },
      { color: "#ff6b7d", values: indicatorPayload.map((item) => Number(item.ema_slow)) },
    ];
    const quantSeries = [
      { color: "#5df2b4", values: quantPayload.map((item) => Number(item.vwap)), strokeWidth: 2.3 },
      { color: "#79dbff", values: quantPayload.map((item) => Number(item.vwap_rolling)), strokeWidth: 1.9 },
      { color: "#f6c66f", values: quantPayload.map((item) => Number(item.poc)), strokeWidth: 1.9 },
    ];
    const rsiSeries = [
      { color: "#bb8dff", values: indicatorPayload.map((item) => Number(item.rsi)), strokeWidth: 2.2 },
    ];

    const card = document.createElement("article");
    card.className = "asset-card panel";
    card.dataset.tone = tone;
    card.innerHTML = `
      <div class="asset-top">
        <div class="asset-title">
          <span class="asset-icon">${assetEmoji(asset.asset)}</span>
          <div>
            <p class="eyebrow">${escapeHtml(asset.asset)}</p>
            <h3>${escapeHtml(asset.label)}</h3>
            <p class="muted">${decision ? escapeHtml(decision.stage_reason) : escapeHtml(asset.description)}</p>
          </div>
        </div>
        <div class="signal-cluster">
          <span class="tag ${toneClass(tone)}">${escapeHtml(quantReport.signal || "HOLD")}</span>
          <span class="tag subtle">${escapeHtml(timeframe)}</span>
        </div>
      </div>
      <div class="indicator-layout">
        <div class="indicator-chart-grid">
          <div class="chart-box indicator-price-chart"></div>
          <div class="chart-box indicator-quant-chart"></div>
          <div class="chart-box indicator-rsi-chart"></div>
        </div>
        <div class="indicator-summary-grid">
          <div class="decision-box quant-decision-box" data-tone="${tone}">
            <p class="metric-label">Score quant / regime / sinal</p>
            <strong>${formatNumber(quantReport.score, 0)} | ${escapeHtml(quantReport.regime || "-")} | ${escapeHtml(quantReport.signal || "HOLD")}</strong>
            <p class="muted">${escapeHtml(quantReport.status || "Sem status quant")}</p>
          </div>
          <div class="decision-box" data-tone="${decision?.execution_status === "BLOQUEADO_MACRO" ? "warning" : tone}">
            <p class="metric-label">Status / direção</p>
            <strong>${decision ? escapeHtml(decision.execution_status) : "MONITORAMENTO"} | ${decision ? escapeHtml(decision.technical_direction) : "Monitoramento"}</strong>
            <p class="muted">${decision ? escapeHtml(decision.stage_reason) : "Ativo exibido para leitura contextual."}</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">Preço / PMD / RSI</p>
            <strong>${formatNumber(asset.latest?.price, 4)} / ${formatNumber(asset.latest?.pmd, 4)} / ${formatNumber(asset.latest?.rsi_daily, 2)}</strong>
            <p class="muted">Leitura estrutural do setup em ${timeframe}.</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">MME9 / MME21 / ATR</p>
            <strong>${formatNumber(asset.latest?.ema_fast, 4)} / ${formatNumber(asset.latest?.ema_slow, 4)} / ${formatNumber(quantReport.atr, 4)}</strong>
            <p class="muted">Tendencia, risco e compressao da estrutura.</p>
          </div>
        </div>
        <div class="decision-box indicator-explanation-card">
            <p class="metric-label">Analise explicativa</p>
            <p class="muted">${escapeHtml(quantReport.explanation || "Sem explicacao quant disponivel.")}</p>
        </div>
        <div class="indicator-metric-grid">
          <div class="decision-box">
            <p class="metric-label">VWAP / rolling</p>
            <strong>${formatNumber(quantReport.vwap, 4)} / ${formatNumber(quantReport.vwap_rolling, 4)}</strong>
            <p class="muted">Posicionamento relativo ao fluxo medio ponderado.</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">POC / ADX</p>
            <strong>${formatNumber(quantReport.poc, 4)} / ${formatNumber(quantReport.adx, 2)}</strong>
            <p class="muted">Confluencia entre volume dominante e forca da tendencia.</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">ATR / volatilidade</p>
            <strong>${formatNumber(quantReport.atr, 4)} / ${escapeHtml(quantReport.volatilidade || "-")}</strong>
            <p class="muted">Amplitude media e leitura de compressao ou stress.</p>
          </div>
          <div class="decision-box">
            <p class="metric-label">Volume / squeeze</p>
            <strong>${escapeHtml(quantReport.volume || "-")} / ${escapeHtml(quantReport.squeeze ? "sim" : "nao")}</strong>
            <p class="muted">Pressao de participacao e chance de expansao do range.</p>
          </div>
          ${(asset.indicator_notes || []).map((note) => `
            <div class="decision-box indicator-note-card">
              <p class="metric-label">Nota tecnica</p>
              <p class="muted">${escapeHtml(note)}</p>
            </div>
          `).join("")}
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
  setText("news-title", newsCenter.title || "Noticias do Mercado Financeiro");
  setText("news-summary", newsCenter.summary || "");
  const newsStatus = setText("news-status", newsCenter.status || "planejamento");
  if (newsStatus) {
    newsStatus.className = `tag subtle ${toneClass(toneFromText(newsCenter.status))}`.trim();
  }
  const newsRiskBias = setText("news-risk-bias", `Vies ${newsCenter.risk_bias || "neutro"}`);
  if (newsRiskBias) {
    newsRiskBias.className = `tag ${toneClass(toneFromText(newsCenter.risk_bias))}`.trim();
  }
  setText("news-source-note", `${newsCenter.source || "Trading Economics"} | ${newsCenter.window?.start || "-"} a ${newsCenter.window?.end || "-"}`);

  const countryFilter = document.getElementById("news-country-filter");
  const importanceFilter = document.getElementById("news-importance-filter");
  const host = document.getElementById("economic-calendar-grid");
  if (!countryFilter || !importanceFilter || !host) return;
  const sourceCountries = newsCenter.countries?.length ? newsCenter.countries : (newsCenter.configured_countries || []);
  const countries = ["ALL", ...sourceCountries];
  if (!countries.includes(state.newsCountry)) state.newsCountry = "ALL";
  countryFilter.innerHTML = countries.map((country) => `
    <option value="${escapeHtml(country)}" ${state.newsCountry === country ? "selected" : ""}>
      ${country === "ALL" ? "Todos os países" : escapeHtml(country)}
    </option>
  `).join("");
  importanceFilter.value = state.newsImportance;

  countryFilter.onchange = () => {
    state.newsCountry = countryFilter.value;
    renderNews(state.dashboard?.news_center || {});
  };
  importanceFilter.onchange = (event) => {
    state.newsImportance = event.target.value;
    renderNews(state.dashboard?.news_center || {});
  };

  const events = (newsCenter.events || []).filter((event) => {
    const countryMatch = state.newsCountry === "ALL" || event.country === state.newsCountry;
    const importanceMatch = state.newsImportance === "ALL" || String(event.importance) === state.newsImportance;
    return countryMatch && importanceMatch;
  });
  if (!events.length) {
    host.innerHTML = "<article class='panel info-card'><p class='muted'>Sem eventos para os filtros selecionados.</p></article>";
    return;
  }
  host.innerHTML = events.map((event) => `
    <article class="calendar-event panel" data-importance="${escapeHtml(event.importance || 0)}">
      <div class="calendar-event-top">
        <div>
          <p class="eyebrow">${escapeHtml(event.country)} | ${escapeHtml(event.category)}</p>
          <h3>${escapeHtml(event.event)}</h3>
          <p class="muted">${escapeHtml(event.date || "-")}</p>
        </div>
        <div class="signal-cluster">
          <span class="tag warning">${renderBulls(event.importance)} ${escapeHtml(event.importance_label || `${event.importance} touros`)}</span>
          <span class="tag ${toneClass(toneFromText(event.market_bias))}">${escapeHtml(event.market_bias || "monitorar")}</span>
        </div>
      </div>
      <div class="calendar-values">
        <div><p class="metric-label">Actual</p><strong>${escapeHtml(event.actual || "-")}</strong></div>
        <div><p class="metric-label">Forecast</p><strong>${escapeHtml(event.forecast || event.te_forecast || "-")}</strong></div>
        <div><p class="metric-label">Previous</p><strong>${escapeHtml(event.previous || "-")}</strong></div>
        <div><p class="metric-label">Surpresa / vies</p><strong>${escapeHtml(event.surprise || "-")} / ${escapeHtml(event.market_bias || "monitorar")}</strong></div>
      </div>
      <div class="calendar-impact">
        <p class="muted">${escapeHtml(event.projection || "Monitorar impacto com DXY, US10Y e SPX.")}</p>
        <span class="helper-pill ${toneClass(toneFromText(event.theme || event.category))}">${escapeHtml(event.theme || event.category || "macro")}</span>
      </div>
    </article>
  `).join("");
};

const renderSettings = (settingsPanel) => {
  const form = document.getElementById("settings-form");
  if (!form) return;
  setText("settings-note", settingsPanel.runtime_note || "");
  setText("refresh-button", `🚀 ${settingsPanel.operational_button_label || "Iniciar Macroflow"}`);
  form.replaceChildren();

  (settingsPanel.groups || []).forEach((group) => {
    const section = document.createElement("section");
    section.className = "setting-group panel";
    section.dataset.groupId = String(group.id || "");

    const header = document.createElement("div");
    header.className = "setting-group-header";

    const eyebrow = document.createElement("p");
    eyebrow.className = "eyebrow";
    eyebrow.textContent = group.title || "";

    const description = document.createElement("p");
    description.textContent = group.description || "";

    header.append(eyebrow, description);

    const fields = document.createElement("div");
    fields.className = "setting-group-fields";

    (group.fields || []).forEach((field) => {
      const wrapper = document.createElement("div");
      wrapper.className = "setting-field";

      const label = document.createElement("label");
      label.textContent = field.label || "";

      let control;
      if (field.type === "select") {
        control = document.createElement("select");
        (field.options || []).forEach((option) => {
          const optionElement = document.createElement("option");
          optionElement.value = String(option);
          optionElement.textContent = String(option);
          optionElement.selected = String(field.value) === String(option);
          control.appendChild(optionElement);
        });
      } else {
        control = document.createElement("input");
        control.type = field.type || "text";
        control.value = field.value ?? "";
        control.placeholder = field.configured ? "Chave configurada" : (field.placeholder || "");
        if (field.step !== undefined) {
          control.step = String(field.step);
        }
      }

      control.dataset.env = String(field.env || "");
      control.dataset.secret = field.secret ? "1" : "0";
      control.dataset.group = String(group.id || "");

      const help = document.createElement("small");
      help.textContent = field.help || "";

      wrapper.append(label, control, help);
      fields.appendChild(wrapper);
    });

    const actions = document.createElement("div");
    actions.className = "settings-actions";

    const button = document.createElement("button");
    button.className = "primary-button settings-save-button";
    button.type = "button";
    button.dataset.saveGroup = String(group.id || "");
    button.textContent = `💾 ${group.save_label || settingsPanel.save_label || "Salvar configuracoes"}`;

    const feedback = document.createElement("span");
    feedback.className = "muted settings-feedback";
    feedback.dataset.feedbackGroup = String(group.id || "");

    actions.append(button, feedback);
    section.append(header, fields, actions);
    form.appendChild(section);
  });
};

const renderDashboard = (dashboard) => {
  state.dashboard = dashboard;
  state.currentTimeframe = dashboard.summary?.default_chart_timeframe || state.currentTimeframe || "4H";

  renderCommandCenter(dashboard);
  renderTimeframeSwitches();
  renderOverview(dashboard.market_overview || {});
  renderSourceHealth(dashboard.source_health || []);
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
  button.textContent = "🚀 Atualizando...";
  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao atualizar");
    renderDashboard(payload.state);
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = `🚀 ${state.dashboard?.settings_panel?.operational_button_label || "Iniciar Macroflow"}`;
  }
};

const saveSettings = async (groupId) => {
  let button = document.querySelector(`[data-save-group="${groupId}"]`);
  let feedback = document.querySelector(`[data-feedback-group="${groupId}"]`);
  const values = {};

  document.querySelectorAll(`#settings-form [data-group="${groupId}"][data-env]`).forEach((input) => {
    const env = input.dataset.env;
    const secret = input.dataset.secret === "1";
    const value = String(input.value ?? "").trim();
    if (secret && !value) return;
    values[env] = value;
  });

  if (!button || !feedback) return;
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
    button = document.querySelector(`[data-save-group="${groupId}"]`);
    feedback = document.querySelector(`[data-feedback-group="${groupId}"]`);
    const chartField = payload.settings.groups
      .flatMap((group) => group.fields)
      .find((field) => field.env === "MACROFLOW_CHART_DEFAULT_TIMEFRAME");
    if (chartField?.value) {
      state.currentTimeframe = chartField.value;
      renderTimeframeSwitches();
      renderChartAssets();
      renderIndicatorAssets();
    }
    if (feedback) {
      feedback.textContent = "Alterações salvas. Clique em Iniciar Macroflow para aplicar na próxima coleta.";
    }
  } catch (error) {
    if (feedback) {
      feedback.textContent = error.message;
    }
  } finally {
    if (button) {
      button.disabled = false;
    }
  }
};

const addJarvisMessage = (role, content) => {
  const host = document.getElementById("jarvis-messages");
  if (!host) return;
  const message = document.createElement("div");
  message.className = `jarvis-message ${role}`;
  message.innerHTML = `<p>${escapeHtml(content).replaceAll("\n", "<br>")}</p>`;
  host.appendChild(message);
  host.scrollTop = host.scrollHeight;
};

const toggleJarvis = (open) => {
  document.getElementById("jarvis-panel")?.classList.toggle("open", open);
  document.getElementById("jarvis-toggle")?.classList.toggle("hidden", open);
  if (open && !state.jarvisHistory.length) {
    addJarvisMessage(
      "assistant",
      "Jarvis online. Me pergunte sobre vies macro, um ativo especifico ou como o calendario economico altera o plano operacional.",
    );
  }
  if (open) document.getElementById("jarvis-input")?.focus();
};

const submitJarvisMessage = async (event) => {
  event.preventDefault();
  const input = document.getElementById("jarvis-input");
  const message = String(input.value || "").trim();
  if (!message) return;
  input.value = "";
  addJarvisMessage("user", message);
  state.jarvisHistory.push({ role: "user", content: message });

  const thinking = "Analisando snapshot do MacroFlow...";
  addJarvisMessage("assistant pending", thinking);
  try {
    const response = await fetch("/api/jarvis/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: state.jarvisHistory.slice(-8) }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao consultar o Jarvis.");
    document.querySelector("#jarvis-messages .pending:last-child")?.remove();
    addJarvisMessage("assistant", payload.reply || "Sem resposta do Jarvis.");
    state.jarvisHistory.push({ role: "assistant", content: payload.reply || "" });
  } catch (error) {
    document.querySelector("#jarvis-messages .pending:last-child")?.remove();
    addJarvisMessage("assistant", error.message);
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });
  document.getElementById("refresh-button")?.addEventListener("click", refreshDashboard);
  document.getElementById("settings-form")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-save-group]");
    if (!button) return;
    saveSettings(button.dataset.saveGroup || "");
  });
  document.getElementById("jarvis-toggle")?.addEventListener("click", () => toggleJarvis(true));
  document.getElementById("jarvis-close")?.addEventListener("click", () => toggleJarvis(false));
  document.getElementById("jarvis-form")?.addEventListener("submit", submitJarvisMessage);
  document.querySelectorAll("[data-jarvis-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      toggleJarvis(true);
      const input = document.getElementById("jarvis-input");
      if (!input) return;
      input.value = button.dataset.jarvisPrompt || "";
      input.focus();
    });
  });
  setActiveTab(state.currentTab);
  try {
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});
