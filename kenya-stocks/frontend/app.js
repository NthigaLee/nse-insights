// ============================================================
//  NSE Insights — App Logic
//  Qualtrim-style dashboard for Kenya NSE stocks
// ============================================================

let activeCompany = null;
let chartInstances = {};

// ---- Chart.js Global Defaults ----
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#2a3146';
Chart.defaults.font.family = "'Inter', 'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 11;

// ---- Formatters ----
function fmtNum(val, units) {
  if (val === null || val === undefined) return '—';
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
          backgroundColor: '#1c2233',
          borderColor: '#2a3146',
          borderWidth: 1,
          padding: 8,
          callbacks: {
            label: (item) => {
              if (opts.prefix) return opts.prefix + item.formattedValue;
              return item.formattedValue + (opts.suffix || '');
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b' }
        },
        y: {
          grid: { color: '#1e2d3d' },
          ticks: {
            color: '#64748b',
            callback: (v) => {
              if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(0) + 'B';
              if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + 'M';
              if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(0) + 'K';
              return v.toFixed(2);
            }
          }
        }
      }
    }
  });
}

// ---- Build bar colors (last year highlighted orange) ----
function barColors(n) {
  return Array.from({ length: n }, (_, i) =>
    i === n - 1 ? 'rgba(245, 158, 11, 0.85)' : 'rgba(59, 130, 246, 0.75)'
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

  // Show dashboard, hide empty state
  document.getElementById('dashboard').classList.remove('hidden');
  document.getElementById('empty-state').classList.add('hidden');

  // Update breadcrumb
  document.getElementById('breadcrumb-company').textContent = `${co.ticker} | NSE`;

  // -- Company Header --
  document.getElementById('company-logo').textContent = co.logo;
  document.getElementById('company-name').textContent = co.name;
  document.getElementById('company-meta').textContent = `${co.ticker} | ${co.exchange} · ${co.sector}`;
  document.getElementById('company-price').textContent = fmtPrice(co.latestPrice);

  // Latest period (may be quarterly — more up-to-date than last annual)
  const latest = co.latestPeriod || co.annuals[co.annuals.length - 1];
  const latestLabel = latest.period || latest.year;
  document.getElementById('company-eps-pill').textContent = `EPS (${latestLabel}): ${fmtEPS(latest.eps)}`;
  document.getElementById('company-latest-year').textContent =
    `Units: KES ${co.units} · Last period: ${latestLabel}`;

  // -- Stats Grid --
  renderStatsGrid(co);

  // -- Charts --
  renderCharts(co);
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
    if (!curr || !prev) return null;
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
function renderCharts(co) {
  const annuals = co.annuals;
  // Use compact period label (e.g. "Dec2023", "H1FY2024") — fall back to year
  const labels  = annuals.map(d => d.period || d.year);
  const n       = annuals.length;
  const colors  = barColors(n);

  // Revenue / NII
  const revenueData = annuals.map(d => d.revenue ?? d.nii);
  makeBarChart('chart-revenue', labels, [{
    label: 'Revenue/NII',
    data: revenueData,
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);

  // Net Income (PAT)
  makeBarChart('chart-pat', labels, [{
    label: 'Net Income',
    data: annuals.map(d => d.pat),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);

  // EPS
  makeBarChart('chart-eps', labels, [{
    label: 'EPS',
    data: annuals.map(d => d.eps),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }], { prefix: 'KES ' });

  // DPS
  makeBarChart('chart-dps', labels, [{
    label: 'DPS',
    data: annuals.map(d => d.dps),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }], { prefix: 'KES ' });

  // NII
  makeBarChart('chart-nii', labels, [{
    label: 'NII',
    data: annuals.map(d => d.nii),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);

  // ── Balance Sheet charts ────────────────────────────────────────────────────
  makeBarChart('chart-assets', labels, [{
    label: 'Total Assets',
    data: annuals.map(d => d.totalAssets),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);

  makeBarChart('chart-equity', labels, [{
    label: 'Total Equity',
    data: annuals.map(d => d.totalEquity),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);

  makeBarChart('chart-deposits', labels, [{
    label: 'Customer Deposits',
    data: annuals.map(d => d.deposits),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);

  makeBarChart('chart-loans', labels, [{
    label: 'Loans & Advances',
    data: annuals.map(d => d.loans),
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);

  // EBITDA for telcos, M-PESA revenue for Safaricom, or skip for others
  const ebitdaData = annuals.map(d => d.mpesa ?? d.ebitda);
  makeBarChart('chart-ebitda', labels, [{
    label: co.ticker === 'SCOM' ? 'M-PESA Revenue' : 'EBITDA',
    data: ebitdaData,
    backgroundColor: colors,
    borderRadius: 3,
    borderSkipped: false,
  }]);
}

// ---- Period Toggle ----
function setPeriod(period) {
  document.getElementById('toggle-annual').classList.toggle('active', period === 'annual');
  document.getElementById('toggle-quarterly').classList.toggle('active', period === 'quarterly');
  // Quarterly data not yet available — no-op for now
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
