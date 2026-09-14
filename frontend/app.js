const API = 'http://localhost:8000/api/v1';

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

const money = n =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(Number(n ?? 0));

const num = n =>
  new Intl.NumberFormat('en-US').format(Number(n ?? 0));

const pct = n => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
};

const safe = value =>
  value === null || value === undefined || value === ''
    ? '—'
    : String(value);

async function api(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw Error(await r.text());
  return r.json();
}

function rowsOf(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.rows)) return data.rows;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function kpi(label, value, sub = '') {
  return `
    <div class="kpi">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
      <div class="sub">${sub}</div>
    </div>
  `;
}

function table(headers, rows) {
  if (!rows.length) {
    return '<p class="loading">No data available.</p>';
  }

  return `
    <table class="table">
      <thead>
        <tr>${headers.map(x => `<th>${x}</th>`).join('')}</tr>
      </thead>
      <tbody>
        ${rows.map(r =>
          `<tr>${r.map(x => `<td>${x ?? '—'}</td>`).join('')}</tr>`
        ).join('')}
      </tbody>
    </table>
  `;
}

function bars(rows, key, max = 12) {
  if (!rows.length) return '<p class="loading">No data available.</p>';

  const a = rows.slice(-max);
  const m = Math.max(...a.map(x => Number(x[key]) || 0), 1);

  return a.map(x => {
    const value = Number(x[key]) || 0;
    const label = x.month || x.period || '';

    return `
      <div
        class="bar"
        style="height:${Math.max(3, value / m * 92)}%"
      >
        <label>${label} · ${money(value)}</label>
      </div>
    `;
  }).join('');
}

function showError(selector, message = 'Unable to load data.') {
  const el = $(selector);
  if (el) el.innerHTML = `<p class="loading">${message}</p>`;
}

async function loadOverview() {
  try {
    const [k, exData, catsData, topsData] = await Promise.all([
      api('/dashboard/summary'),
      api('/sales/monthly'),
      api('/sales/categories'),
      api('/products/top')
    ]);

    const ex = rowsOf(exData);
    const cats = rowsOf(catsData);
    const tops = rowsOf(topsData);

    $('#kpis').innerHTML = [
      kpi(
        'Total Revenue',
        money(k.total_revenue),
        'Delivered-order product revenue'
      ),
      kpi(
        'Delivered Orders',
        num(k.delivered_orders),
        `of ${num(k.total_orders)} total`
      ),
      kpi(
        'Customers',
        num(k.total_customers),
        'Delivered-order customers'
      ),
      kpi(
        'Products',
        num(k.total_products),
        'Catalog'
      ),
      kpi(
        'Opportunity Products',
        num(k.opportunity_products),
        `${num(k.high_opportunity_products)} high opportunity`
      ),
      kpi(
        'High-Risk Products',
        num(k.high_risk_products),
        `${num(k.critical_products)} critical`
      ),
      kpi(
        'Anomaly Products',
        num(k.anomaly_products),
        'Detected signals'
      ),
      kpi(
        'Sellers',
        num(k.total_sellers),
        'Seller network'
      )
    ].join('');

    $('#revenue-chart').innerHTML = bars(ex, 'revenue');

    /*
      The current dashboard summary does not expose healthy_products.
      Therefore do not fabricate a Healthy count in the UI.
      Show the verified decision-health counts that are actually available.
    */
    const watch = Number(k.watch_products || 0);
    const atRisk = Number(k.at_risk_products || 0);
    const critical = Number(k.critical_products || 0);
    const healthTotal = watch + atRisk + critical;

    $('#health-chart').innerHTML = `
      <div class="donut-wrap-inner">
        <div class="donut donut-neutral"></div>
        <div class="legend">
          <div><i></i>Watch ${num(watch)}</div>
          <div><i></i>At Risk ${num(atRisk)}</div>
          <div><i></i>Critical ${num(critical)}</div>
          <div class="health-note">
            ${num(healthTotal)} flagged decision-health products
          </div>
        </div>
      </div>
    `;

    $('#categories').innerHTML = table(
      ['Category', 'Orders', 'Revenue'],
      cats.slice(0, 8).map(x => [
        safe(x.category),
        num(x.orders),
        money(x.revenue)
      ])
    );

    $('#top-products').innerHTML = table(
      ['Product', 'Category', 'Revenue'],
      tops.slice(0, 8).map(x => [
        safe(x.product_id).slice(0, 10) + '...',
        safe(x.category),
        money(x.revenue)
      ])
    );

  } catch (e) {
    console.error('Overview error:', e);
    showError('#revenue-chart');
    showError('#categories');
    showError('#top-products');
  }
}

async function loadSales() {
  try {
    const [sData, cData, pData] = await Promise.all([
      api('/sales/monthly'),
      api('/sales/categories'),
      api('/payments')
    ]);

    const s = rowsOf(sData);
    const c = rowsOf(cData);
    const p = rowsOf(pData);

    $('#sales-chart').innerHTML = bars(s, 'revenue', 18);

    $('#sales-categories').innerHTML = table(
      ['Category', 'Orders', 'Units', 'Revenue'],
      c.slice(0, 15).map(x => [
        safe(x.category),
        num(x.orders),
        num(x.units_sold),
        money(x.revenue)
      ])
    );

    $('#payments').innerHTML = table(
      ['Method', 'Orders', 'Value'],
      p.slice(0, 10).map(x => [
        safe(x.payment_type),
        num(x.payment_count),
        money(x.total_payment_value)
      ])
    );

  } catch (e) {
    console.error('Sales error:', e);
    showError('#sales-chart');
    showError('#sales-categories');
    showError('#payments');
  }
}

let productView = 'forecast';

async function loadProducts() {
  try {
    const path =
      productView === 'forecast'
        ? '/forecast?limit=25'
        : productView === 'opportunity'
          ? '/opportunities?limit=25'
          : '/risks?limit=25';

    const data = await api(path);
    const rows = rowsOf(data);

    if (productView === 'forecast') {
      $('#product-table').innerHTML = table(
        ['Product', 'Category', 'Forecast', 'Vs 3M', 'Month'],
        rows.map(x => [
          safe(x.product_id).slice(0, 12) + '...',
          safe(x.category),
          Number(x.forecast_demand ?? 0).toFixed(2),
          pct(x.forecast_vs_3m_pct),
          safe(x.forecast_month).slice(0, 10)
        ])
      );
    } else {
      $('#product-table').innerHTML = table(
        [
          'Product',
          'Category',
          'Health',
          'Opportunity',
          'Risk',
          'Priority'
        ],
        rows.map(x => [
          safe(x.product_id).slice(0, 12) + '...',
          safe(x.category),
          `<span class="badge ${
            x.health_status === 'healthy'
              ? 'good'
              : x.health_status === 'critical' ||
                x.health_status === 'at_risk'
                ? 'bad'
                : 'warn'
          }">${safe(x.health_status)}</span>`,
          num(x.opportunity_score),
          num(x.risk_score),
          safe(x.decision_priority)
        ])
      );
    }

  } catch (e) {
    console.error('Products error:', e);
    showError('#product-table');
  }
}

async function loadRisk() {
  try {
    const [k, anomalyData] = await Promise.all([
      api('/dashboard/summary'),
      api('/anomalies?limit=30')
    ]);

    $('#risk-kpis').innerHTML = [
      kpi('Anomalies', num(k.anomaly_products)),
      kpi('Critical', num(k.critical_products)),
      kpi('At Risk', num(k.at_risk_products)),
      kpi('High Risk', num(k.high_risk_products))
    ].join('');

    const rows = rowsOf(anomalyData);

    $('#anomaly-table').innerHTML = table(
      [
        'Product',
        'Category',
        'Type',
        'Severity',
        'Actual',
        'Expected'
      ],
      rows.map(x => [
        safe(x.product_id).slice(0, 12) + '...',
        safe(x.category),
        safe(x.anomaly_type),
        Number(x.anomaly_severity ?? 0).toFixed(1),
        x.actual_demand == null ? '—' : num(x.actual_demand),
        x.expected_demand == null ? '—' : num(x.expected_demand)
      ])
    );

  } catch (e) {
    console.error('Risk error:', e);
    showError('#anomaly-table');
  }
}

function analystMessage(d) {
  const insights = Array.isArray(d.insights) ? d.insights : [];
  const recommendations =
    Array.isArray(d.recommendations) ? d.recommendations : [];
  const sources = Array.isArray(d.sources) ? d.sources : [];
  const limitations = Array.isArray(d.limitations) ? d.limitations : [];

  let html = `
    <div class="analyst-answer">
      <strong>Answer</strong>
      <p>${safe(d.answer)}</p>
    </div>
  `;

  if (insights.length) {
    html += `
      <div class="analyst-section">
        <strong>Insights</strong>
        <ul>${insights.map(x => `<li>${safe(x)}</li>`).join('')}</ul>
      </div>
    `;
  }

  if (recommendations.length) {
    html += `
      <div class="analyst-section">
        <strong>Recommended Actions</strong>
        <ul>${recommendations.map(x => `<li>${safe(x)}</li>`).join('')}</ul>
      </div>
    `;
  }

  if (sources.length) {
    html += `
      <div class="analyst-section">
        <strong>Sources</strong>
        <div class="source-list">
          ${sources.map(x => `<span class="source-tag">${safe(x)}</span>`).join('')}
        </div>
      </div>
    `;
  }

  if (limitations.length) {
    html += `
      <div class="analyst-section limitations">
        <strong>Limitations</strong>
        <ul>${limitations.map(x => `<li>${safe(x)}</li>`).join('')}</ul>
      </div>
    `;
  }

  return html;
}

async function ask(q) {
  if (!q) return;

  const chat = $('#chat');

  chat.innerHTML += `
    <div class="msg user">${q}</div>
    <div class="msg bot loading">Analyzing...</div>
  `;

  chat.scrollTop = chat.scrollHeight;

  try {
    const d = await api('/analyst?q=' + encodeURIComponent(q));
    const last = chat.querySelector('.msg.bot.loading');

    last.classList.remove('loading');
    last.innerHTML = analystMessage(d);

  } catch (e) {
    console.error('Analyst error:', e);

    const last = chat.querySelector('.msg.bot.loading');

    last.classList.remove('loading');
    last.textContent =
      'Unable to reach the business analyst API.';
  }

  chat.scrollTop = chat.scrollHeight;
}

function showPage(name) {
  $$('.page').forEach(x => x.classList.remove('active'));
  $('#' + name).classList.add('active');

  $$('.nav-item').forEach(x =>
    x.classList.toggle('active', x.dataset.page === name)
  );

  $('#page-title').textContent = {
    overview: 'Executive Overview',
    sales: 'Sales Analytics',
    products: 'Product Intelligence',
    risk: 'Risk & Anomalies',
    analyst: 'AI Business Analyst'
  }[name];

  if (name === 'overview') loadOverview();
  if (name === 'sales') loadSales();
  if (name === 'products') loadProducts();
  if (name === 'risk') loadRisk();
}

$$('.nav-item').forEach(
  b => b.onclick = () => showPage(b.dataset.page)
);

$$('.tab').forEach(
  b => b.onclick = () => {
    $$('.tab').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    productView = b.dataset.productView;
    loadProducts();
  }
);

$$('.suggestions button').forEach(
  b => b.onclick = () => {
    showPage('analyst');
    $('#question').value = b.textContent;
    ask(b.textContent);
  }
);

$('#ask-form').onsubmit = e => {
  e.preventDefault();
  const q = $('#question').value.trim();
  $('#question').value = '';
  ask(q);
};

$('#refresh').onclick = () =>
  showPage(document.querySelector('.page.active').id);



// =========================================================
// PRODUCT & CATEGORY EXPLORER
// =========================================================

let explorerMode = "product";

function explorerTable(headers, rows) {
  return table(headers, rows);
}

function renderProductExplorer(d) {

  const p = d.product || {};
  const i = d.intelligence || {};
  const delivery = d.delivery || {};
  const reviews = d.reviews || {};
  const monthly = rowsOf(d.monthly_sales);

  return `
    <div class="explorer-heading">
      <p class="eyebrow">PRODUCT DEEP DIVE</p>
      <h2>${safe(p.product_id)}</h2>
      <p>${safe(p.category)}</p>
    </div>

    <div class="kpi-grid">
      ${kpi("Revenue", money(p.revenue))}
      ${kpi("Orders", num(p.orders))}
      ${kpi("Units Sold", num(p.units_sold))}
      ${kpi("Customers", num(p.customers))}
      ${kpi("Sellers", num(p.sellers))}
      ${kpi("Avg Price", money(p.average_item_price))}
    </div>

    <div class="grid-2 explorer-grid">

      <article class="card">
        <div class="card-head">
          <h2>Monthly Sales</h2>
          <span>Revenue</span>
        </div>
        <div class="chart tall">
          ${bars(monthly, "revenue", 12)}
        </div>
      </article>

      <article class="card">
        <div class="card-head">
          <h2>Forecast & Trend</h2>
          <span>ML intelligence</span>
        </div>

        <div class="intelligence-grid">
          <div>
            <span>Forecast Demand</span>
            <strong>${i.forecast_demand == null ? "—" : Number(i.forecast_demand).toFixed(2)}</strong>
          </div>
          <div>
            <span>Vs 3M</span>
            <strong>${pct(i.forecast_vs_3m_pct)}</strong>
          </div>
          <div>
            <span>Trend</span>
            <strong>${safe(i.trend)}</strong>
          </div>
          <div>
            <span>Trend Strength</span>
            <strong>${safe(i.trend_strength)}</strong>
          </div>
        </div>
      </article>

    </div>

    <div class="grid-2 explorer-grid">

      <article class="card">
        <div class="card-head">
          <h2>Delivery Performance</h2>
        </div>

        ${explorerTable(
          ["Metric", "Value"],
          [
            ["Delivered Orders", num(delivery.delivered_orders)],
            ["Avg Delivery Days",
              delivery.avg_delivery_days == null
                ? "—"
                : Number(delivery.avg_delivery_days).toFixed(1)],
            ["On-Time Rate",
              delivery.on_time_rate == null
                ? "—"
                : Number(delivery.on_time_rate).toFixed(1) + "%"]
          ]
        )}
      </article>

      <article class="card">
        <div class="card-head">
          <h2>Customer & Reviews</h2>
        </div>

        ${explorerTable(
          ["Metric", "Value"],
          [
            ["Customers", num(p.customers)],
            ["Review Count", num(reviews.review_count)],
            ["Average Review",
              reviews.average_review_score == null
                ? "—"
                : Number(reviews.average_review_score).toFixed(2)]
          ]
        )}
      </article>

    </div>

    <article class="card explorer-decision">

      <div class="card-head">
        <h2>Decision Intelligence</h2>
        <span>${safe(i.decision_priority)}</span>
      </div>

      <div class="decision-grid">

        <div class="decision-box">
          <span>Health Score</span>
          <strong>${i.health_score == null ? "—" : Number(i.health_score).toFixed(1)}</strong>
          <small>${safe(i.health_status)}</small>
        </div>

        <div class="decision-box">
          <span>Opportunity Score</span>
          <strong>${i.opportunity_score == null ? "—" : Number(i.opportunity_score).toFixed(1)}</strong>
        </div>

        <div class="decision-box">
          <span>Risk Score</span>
          <strong>${i.risk_score == null ? "—" : Number(i.risk_score).toFixed(1)}</strong>
        </div>

        <div class="decision-box">
          <span>Anomaly</span>
          <strong>${safe(i.anomaly_type)}</strong>
        </div>

      </div>

      <div class="recommendation-box">
        <strong>Management Recommendation</strong>
        <p>${safe(i.recommendation)}</p>
      </div>

    </article>
  `;
}


function renderCategoryExplorer(d) {

  const c = d.category || {};
  const f = d.forecast || {};
  const dec = d.decisions || {};
  const monthly = rowsOf(d.monthly_sales);
  const products = rowsOf(d.top_products);

  return `
    <div class="explorer-heading">
      <p class="eyebrow">CATEGORY DEEP DIVE</p>
      <h2>${safe(c.category)}</h2>
      <p>Category-level business and ML intelligence.</p>
    </div>

    <div class="kpi-grid">
      ${kpi("Revenue", money(c.revenue))}
      ${kpi("Orders", num(c.orders))}
      ${kpi("Units Sold", num(c.units_sold))}
      ${kpi("Customers", num(c.customers))}
      ${kpi("Products", num(c.products))}
      ${kpi("Sellers", num(c.sellers))}
    </div>

    <div class="grid-2 explorer-grid">

      <article class="card">
        <div class="card-head">
          <h2>Category Sales Trend</h2>
          <span>Revenue</span>
        </div>
        <div class="chart tall">
          ${bars(monthly, "revenue", 12)}
        </div>
      </article>

      <article class="card">
        <div class="card-head">
          <h2>Category Forecast</h2>
          <span>Latest ML snapshot</span>
        </div>

        <div class="intelligence-grid">
          <div>
            <span>Forecast Demand</span>
            <strong>${Number(f.forecast_demand || 0).toFixed(1)}</strong>
          </div>
          <div>
            <span>Forecast Products</span>
            <strong>${num(f.forecast_products)}</strong>
          </div>
          <div>
            <span>Avg Vs 3M</span>
            <strong>${pct(f.avg_forecast_vs_3m_pct)}</strong>
          </div>
          <div>
            <span>Avg Risk</span>
            <strong>${dec.avg_risk_score == null ? "—" : Number(dec.avg_risk_score).toFixed(1)}</strong>
          </div>
        </div>
      </article>

    </div>

    <div class="grid-2 explorer-grid">

      <article class="card">
        <div class="card-head">
          <h2>Decision Distribution</h2>
          <span>Products</span>
        </div>

        ${explorerTable(
          ["Signal", "Products"],
          [
            ["High Opportunity", num(dec.high_opportunity_products)],
            ["Opportunity", num(dec.opportunity_products)],
            ["Watch", num(dec.watch_products)],
            ["At Risk", num(dec.at_risk_products)],
            ["Critical", num(dec.critical_products)],
            ["High Risk", num(dec.high_risk_products)],
            ["Low Volume Risk", num(dec.low_volume_risk_products)]
          ]
        )}
      </article>

      <article class="card">
        <div class="card-head">
          <h2>Top Products</h2>
          <span>Revenue</span>
        </div>

        ${explorerTable(
          ["Product", "Orders", "Units", "Revenue"],
          products.map(x => [
            safe(x.product_id).slice(0, 12) + "...",
            num(x.orders),
            num(x.units_sold),
            money(x.revenue)
          ])
        )}
      </article>

    </div>
  `;
}


async function loadExplorerOptions() {

  const select = $("#explorer-select");

  if (!select) return;

  select.innerHTML = '<option value="">Loading...</option>';

  try {

    if (explorerMode === "product") {

      const data = await api("/products?limit=500");
      const rows = rowsOf(data);

      select.innerHTML =
        '<option value="">Select a product...</option>' +
        rows.map(x =>
          `<option value="${safe(x.product_id)}">${safe(x.product_id)} — ${safe(x.category)}</option>`
        ).join("");

    } else {

      const data = await api("/explorer/categories");
      const rows = rowsOf(data);

      select.innerHTML =
        '<option value="">Select a category...</option>' +
        rows.map(x =>
          `<option value="${safe(x.category)}">${safe(x.category)}</option>`
        ).join("");
    }

  } catch (e) {

    console.error(e);

    select.innerHTML =
      '<option value="">Unable to load</option>';
  }
}


async function loadExplorer() {

  const select = $("#explorer-select");
  const content = $("#explorer-content");

  if (!select || !content || !select.value) {

    if (content) {
      content.innerHTML =
        '<p class="loading">Select a product or category to explore.</p>';
    }

    return;
  }

  content.innerHTML =
    '<p class="loading">Loading intelligence...</p>';

  try {

    const value = encodeURIComponent(select.value);

    const endpoint =
      explorerMode === "product"
        ? `/explorer/product/${value}`
        : `/explorer/category/${value}`;

    const data = await api(endpoint);

    content.innerHTML =
      explorerMode === "product"
        ? renderProductExplorer(data)
        : renderCategoryExplorer(data);

  } catch (e) {

    console.error(e);

    content.innerHTML =
      '<p class="loading">Unable to load explorer data.</p>';
  }
}


function setupExplorer() {

  const productBtn = $("#explorer-product-btn");
  const categoryBtn = $("#explorer-category-btn");
  const select = $("#explorer-select");

  if (!productBtn || !categoryBtn || !select) return;

  productBtn.onclick = async () => {

    explorerMode = "product";

    productBtn.classList.add("active");
    categoryBtn.classList.remove("active");

    $("#explorer-label").textContent = "Select Product";

    await loadExplorerOptions();
  };

  categoryBtn.onclick = async () => {

    explorerMode = "category";

    categoryBtn.classList.add("active");
    productBtn.classList.remove("active");

    $("#explorer-label").textContent = "Select Category";

    await loadExplorerOptions();
  };

  select.onchange = loadExplorer;

  loadExplorerOptions();
}


// Extend existing navigation
const explorerOriginalShowPage = showPage;

showPage = function(name) {

  if (name === "explorer") {

    $$(".page").forEach(x => x.classList.remove("active"));
    $("#explorer").classList.add("active");

    $$(".nav-item").forEach(x =>
      x.classList.toggle("active", x.dataset.page === name)
    );

    $("#page-title").textContent =
      "Product & Category Explorer";

    setupExplorer();

    return;
  }

  explorerOriginalShowPage(name);
};


loadOverview().catch(e => console.error(e));




