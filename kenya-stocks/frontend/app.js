// ============================================================
//  NSE Insights — App Logic
//  Qualtrim-style dashboard for Kenya NSE stocks
// ============================================================

let activeCompany = null;
let chartInstances = {};

// ---- TradingView NSEKE Ticker Mapping ----
// Format: our internal ticker → TradingView NSEKE symbol
// Note: Safaricom is SCOM on NSE (not SAFARICOM)
const NSEKE_TICKERS = {
  ABSA: 'NSEKE:ABSA',
  COOP: 'NSEKE:COOP',
  DTB:  'NSEKE:DTB',
  EQTY: 'NSEKE:EQTY',
  KCB:  'NSEKE:KCB',
  NCBA: 'NSEKE:NCBA',
  SCBK: 'NSEKE:SCBK',
  SCOM: 'NSEKE:SCOM',  // Safaricom (if added later)
};

// ---- Chart.js Global Defaults ----
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#2a3146';
Chart.defaults.font.family = "'Inter', 'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 11;

// ---- Formatters ----
function fmtNum(val, units) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  // Convert to billions or millions for display
  if (units === 'thousands') {
    if (Math.abs(val) >= 1e6)      return (val / 1e6).toFixed(1) + 'B';
    if (Math.abs(val) >= 1e3)      return (val / 1e3).toFixed(1) + 'M';
    return val.toFixed(0);
  }
  if (units === 'millions') {
    if (Math.abs(val) >= 1e3)      return (val / 1e3).toFixed(1) + 'B';
    return val.toFixed(0) + 'M';
  }
  return val.toFixed(2);
}

function fmtEPS(val) {
  if (val === null || val === undefined) return '—';
  return 'KES ' + val.toFixed(2);
}

function fmtDPS(val) {
  if (val === null || val === undefined) return '—';
  return 'KES ' + val.toFixed(2);
}

function fmtPrice(val) {
  if (val === null || val === undefined) return '—';
  return 'KES ' + val.toFixed(2);
}

// ---- Calculate Compound Annual Growth Rate ----
function calcCAGR(data, periods) {
  if (!data || data.length < 2) return null;
  const latest = data[data.length - 1];
  const startIdx = Math.max(0, data.length - 1 - periods);
  const start = data[startIdx];
  if (start === null || start === undefined || start <= 0 || latest <= 0) return null;
  const n = data.length - 1 - startIdx;
  if (n === 0) return null;
  return (Math.pow(latest / start, 1 / n) - 1) * 100;
}

// ---- Bar Chart Creator ----
function makeBarChart(canvasId, labels, datasets, opts = {}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  // Destroy existing instance if any
  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }

  chartInstances[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 10,
          titleFont: { size: 12, weight: 'bold' },
          bodyFont: { size: 12 },
          cornerRadius: 8,
          callbacks: {
            label: (item) => {
              const val = item.raw;
              const formatted = opts.isCurrency ? fmtPrice(val) : fmtNum(val, opts.units);
              return ` ${item.dataset.label}: ${formatted}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { size: 10 } }
        },
        y: {
          grid: { color: 'rgba(51, 65, 85, 0.5)', drawTicks: false },
          border: { display: false },
          ticks: {
            color: '#64748b',
            font: { size: 10 },
            callback: (v) => {
              const u = opts.units;
              if (u === 'millions') {
                // data stored in KES millions
                if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + 'T';
                if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(0) + 'B';
                return v.toFixed(0) + 'M';
              }
              if (u === 'thousands') {
                // data stored in KES thousands
                if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(0) + 'B';
                if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + 'M';
                if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(0) + 'K';
                return v;
              }
              // raw / isCurrency (EPS, DPS, price)
              if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(0) + 'B';
              if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + 'M';
              if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(0) + 'K';
              return v;
            }
          }
        }
      }
    }
  });

  // Add growth pills if requested (Qualtrim style)
  const card = ctx.closest('.chart-card');
  let growthContainer = card.querySelector('.growth-pills');
  if (opts.showGrowth && datasets[0].data.length >= 2) {
    if (!growthContainer) {
      growthContainer = document.createElement('div');
      growthContainer.className = 'growth-pills';
      card.appendChild(growthContainer);
    }
    const data = datasets[0].data;
    const cagr1 = calcCAGR(data, 1);
    const cagr3 = calcCAGR(data, 3);
    const cagr5 = calcCAGR(data, 5);
    
    let html = '';
    if (cagr1 !== null) html += `<div class="growth-pill"><span>1Y:</span>${cagr1 >= 0 ? '+' : ''}${cagr1.toFixed(1)}%</div>`;
    if (cagr3 !== null) html += `<div class="growth-pill"><span>3Y:</span>${cagr3 >= 0 ? '+' : ''}${cagr3.toFixed(1)}%</div>`;
    if (cagr5 !== null) html += `<div class="growth-pill"><span>5Y:</span>${cagr5 >= 0 ? '+' : ''}${cagr5.toFixed(1)}%</div>`;
    growthContainer.innerHTML = html;
  } else if (growthContainer) {
    growthContainer.innerHTML = '';
  }
}

// ---- Build bar colors (Qualtrim style: Orange for latest, Blue for others) ----
function barColors(n) {
  return Array.from({ length: n }, (_, i) =>
    i === n - 1 ? '#f59e0b' : '#38bdf8'
  );
}

// ---- Load Company ----
function loadCompany() {
  const sel = document.getElementById('company-select').value;
  if (!sel || !NSE_COMPANIES[sel]) {
    alert('Please select a company first.');
    return;
  }
  const co = NSE_COMPANIES[sel];
  activeCompany = co;
  _currentCompany = co;
  _currentPeriod = 'annual';
  // Reset toggle to annual
  document.getElementById('toggle-annual').classList.add('active');
  document.getElementById('toggle-quarterly').classList.remove('active');

  // Show dashboard, hide empty state
  document.getElementById('dashboard').classList.remove('hidden');
  document.getElementById('empty-state').classList.add('hidden');

  // Update breadcrumb
  document.getElementById('breadcrumb-company').textContent = `${co.ticker} | NSE`;

  // -- Company Header --
  document.getElementById('company-logo').textContent = co.logo;
  document.getElementById('company-name').textContent = co.name;
  document.getElementById('company-meta').textContent = `${co.ticker} | ${co.exchange} · ${co.sector}`;
  // Price: live via TradingView chart below — static latestPrice shown in stats grid
  const priceEl = document.getElementById('company-price');
  priceEl.textContent = 'Live on chart';
  priceEl.classList.add('tv-live-badge');

  // Latest period (may be quarterly — more up-to-date than last annual)
  const latest = co.latestPeriod || co.annuals[co.annuals.length - 1];
  const latestLabel = latest.period || latest.year;
  document.getElementById('company-eps-pill').textContent = `EPS (${latestLabel}): ${fmtEPS(latest.eps)}`;
  document.getElementById('company-latest-year').textContent =
    `Units: KES ${co.units} · Last period: ${latestLabel}`;

  // -- TradingView Live Price Chart --
  initTradingViewChart(co.ticker);

  // -- Stats Grid --
  renderStatsGrid(co);

  // -- Charts --
  renderCharts(co, 'annual');
}

// ---- Stats Grid ----
function renderStatsGrid(co) {
  // Use latestPeriod (could be quarterly) for the stats card — more up-to-date
  const latest = co.latestPeriod || co.annuals[co.annuals.length - 1];
  const latestLabel = latest.period || latest.year;
  // For YoY comparison use second-to-last annual row
  const annualRows = co.annuals;
  const prev = annualRows.length >= 2 ? annualRows[annualRows.length - 2] : null;

  function growth(curr, prev) {
    if (curr === null || curr === undefined || prev === null || prev === undefined) return null;
    return ((curr - prev) / Math.abs(prev)) * 100;
  }

  function growthLabel(curr, prev) {
    const g = growth(curr, prev);
    if (g === null) return { text: '—', cls: '' };
    const sign = g >= 0 ? '+' : '';
    return { text: `${sign}${g.toFixed(1)}%`, cls: g >= 0 ? 'up' : 'down' };
  }

  const revGrowth = growthLabel(latest.revenue, prev?.revenue);
  const patGrowth = growthLabel(latest.pat,     prev?.pat);
  const niiGrowth = growthLabel(latest.nii,     prev?.nii);

  const sections = [
    {
      title: 'Revenue / NII',
      rows: [
        { label: 'Revenue',        val: fmtNum(latest.revenue, co.units) },
        { label: 'Net Int. Income',val: fmtNum(latest.nii, co.units) },
        { label: 'YoY Revenue',    val: revGrowth.text,  cls: revGrowth.cls },
      ]
    },
    {
      title: 'Profitability',
      rows: [
        { label: 'Net Income',     val: fmtNum(latest.pat, co.units) },
        { label: 'YoY Net Inc.',   val: patGrowth.text, cls: patGrowth.cls },
        { label: 'YoY NII',        val: niiGrowth.text, cls: niiGrowth.cls },
      ]
    },
    {
      title: 'Per Share',
      rows: [
        { label: 'EPS',            val: fmtEPS(latest.eps) },
        { label: 'DPS',            val: fmtDPS(latest.dps) },
        { label: 'Price',          val: fmtPrice(co.latestPrice) },
      ]
    },
    {
      title: 'Valuation',
      rows: [
        { label: 'P/E (approx)',
          val: (latest.eps && co.latestPrice) ? (co.latestPrice / latest.eps).toFixed(1) + 'x' : '—' },
        { label: 'Div. Yield',
          val: (latest.dps && co.latestPrice) ? ((latest.dps / co.latestPrice) * 100).toFixed(1) + '%' : '—' },
        { label: 'Currency',       val: co.currency },
      ]
    },
    {
      title: 'Data Coverage',
      rows: [
        { label: 'First Period', val: co.annuals[0].period || co.annuals[0].year },
        { label: 'Last Period',  val: latestLabel },
        { label: 'Period Type',  val: latest.periodType || '—' },
        { label: 'Data Points',  val: co.annuals.length },
      ]
    }
  ];

  const grid = document.getElementById('stats-grid');
  grid.innerHTML = sections.map(sec => `
    <div class="stat-section">
      <div class="stat-section-title">${sec.title}</div>
      ${sec.rows.map(r => `
        <div class="stat-row">
          <span class="stat-label">${r.label}</span>
          <span class="stat-val ${r.cls || ''}">${r.val}</span>
        </div>
      `).join('')}
    </div>
  `).join('');
}

// ---- Render Charts ----
function renderCharts(co, period) {
  period = period || 'annual';
  const hasQuarters = co.quarters && co.quarters.length > 0;
  
  // Data selection
  let dataPoints = (period === 'quarterly' && hasQuarters) ? [...co.quarters] : [...co.annuals];
  
  // Sort chronologically using dateKey (ISO date) if present, else year
  dataPoints.sort((a, b) => {
    const da = a.dateKey || String(a.year || '');
    const db = b.dateKey || String(b.year || '');
    return da.localeCompare(db);
  });

  const labels  = dataPoints.map(d => d.period || d.year);
  const n       = dataPoints.length;
  const colors  = barColors(n);
  const chartOpts = { showGrowth: period === 'annual', units: co.units };

  // Revenue / NII
  makeBarChart('chart-revenue', labels, [{
    label: 'Revenue/NII',
    data: dataPoints.map(d => d.revenue ?? d.nii),
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);

  // Net Income (PAT)
  makeBarChart('chart-pat', labels, [{
    label: 'Net Income',
    data: dataPoints.map(d => d.pat),
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);

  // EPS
  makeBarChart('chart-eps', labels, [{
    label: 'EPS',
    data: dataPoints.map(d => d.eps),
    backgroundColor: colors,
    borderRadius: 4,
  }], { ...chartOpts, isCurrency: true });

  // DPS
  makeBarChart('chart-dps', labels, [{
    label: 'DPS',
    data: dataPoints.map(d => d.dps),
    backgroundColor: colors,
    borderRadius: 4,
  }], { ...chartOpts, isCurrency: true });

  // NII
  makeBarChart('chart-nii', labels, [{
    label: 'NII',
    data: dataPoints.map(d => d.nii),
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);

  // Balance Sheet
  makeBarChart('chart-assets', labels, [{
    label: 'Total Assets',
    data: dataPoints.map(d => d.totalAssets),
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);

  makeBarChart('chart-equity', labels, [{
    label: 'Total Equity',
    data: dataPoints.map(d => d.totalEquity),
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);

  makeBarChart('chart-deposits', labels, [{
    label: 'Deposits',
    data: dataPoints.map(d => d.deposits),
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);

  makeBarChart('chart-loans', labels, [{
    label: 'Loans',
    data: dataPoints.map(d => d.loans),
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);

  const ebitdaData = dataPoints.map(d => d.mpesa ?? d.ebitda);
  makeBarChart('chart-ebitda', labels, [{
    label: co.ticker === 'SCOM' ? 'M-PESA Revenue' : 'EBITDA',
    data: ebitdaData,
    backgroundColor: colors,
    borderRadius: 4,
  }], chartOpts);
}

// ---- TradingView Live Price Chart ----
function initTradingViewChart(ticker) {
  const nsekeTicker = NSEKE_TICKERS[ticker] || `NSEKE:${ticker}`;

  const section   = document.getElementById('tv-chart-section');
  const container = document.getElementById('tradingview-chart-container');
  const link      = document.getElementById('tv-open-link');

  section.classList.remove('hidden');

  if (link) {
    link.href = `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(nsekeTicker)}`;
  }

  // Re-create inner div to force widget reset when switching companies
  container.innerHTML = '<div id="tradingview_widget_inner" style="height:100%"></div>';

  if (typeof TradingView === 'undefined') {
    container.innerHTML = '<div class="tv-chart-error">TradingView chart could not load. Check your internet connection.</div>';
    return;
  }

  new TradingView.widget({
    autosize:            true,
    symbol:              nsekeTicker,
    interval:            'D',
    timezone:            'Africa/Nairobi',
    theme:               'dark',
    style:               '1',
    locale:              'en',
    toolbar_bg:          '#1e293b',
    enable_publishing:   false,
    withdateranges:      true,
    hide_side_toolbar:   false,
    allow_symbol_change: false,
    save_image:          false,
    container_id:        'tradingview_widget_inner',
  });
}

// ---- Period Toggle ----
let _currentCompany = null;
let _currentPeriod = 'annual';

function setPeriod(period) {
  if (!_currentCompany) return;
  const hasQuarters = _currentCompany.quarters && _currentCompany.quarters.length > 0;
  // If no quarterly data, stay on annual
  if (period === 'quarterly' && !hasQuarters) {
    period = 'annual';
    // Flash the quarterly button to indicate no data
    const btn = document.getElementById('toggle-quarterly');
    btn.textContent = 'No quarterly data';
    setTimeout(() => { btn.textContent = 'Quarterly'; }, 1500);
  }
  _currentPeriod = period;
  document.getElementById('toggle-annual').classList.toggle('active', period === 'annual');
  document.getElementById('toggle-quarterly').classList.toggle('active', period === 'quarterly');
  renderCharts(_currentCompany, period);
}

// ---- Populate dropdown from NSE_COMPANIES (grouped by sector) ----
function populateDropdown() {
  const sel = document.getElementById('company-select');

  // Group tickers by sector
  const sectors = {};
  for (const [ticker, co] of Object.entries(NSE_COMPANIES)) {
    const sec = co.sector || 'Other';
    if (!sectors[sec]) sectors[sec] = [];
    sectors[sec].push({ ticker, name: co.name });
  }

  // Sort sectors, put Banking first
  const sectorOrder = ['Banking', 'Telecoms', 'FMCG', 'Insurance', 'Energy', 'Construction', 'Media', 'Agriculture', 'Manufacturing', 'Other'];
  const sortedSectors = Object.keys(sectors).sort((a, b) => {
    const ai = sectorOrder.indexOf(a);
    const bi = sectorOrder.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });

  for (const sector of sortedSectors) {
    const grp = document.createElement('optgroup');
    grp.label = sector;
    for (const { ticker, name } of sectors[sector].sort((a, b) => a.name.localeCompare(b.name))) {
      const opt = document.createElement('option');
      opt.value = ticker;
      opt.textContent = `${ticker} — ${name}`;
      grp.appendChild(opt);
    }
    sel.appendChild(grp);
  }
}

// ---- Enter key on select ----
document.addEventListener('DOMContentLoaded', () => {
  populateDropdown();
  document.getElementById('company-select').addEventListener('keydown', e => {
    if (e.key === 'Enter') loadCompany();
  });
});
