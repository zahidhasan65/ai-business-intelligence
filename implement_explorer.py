from pathlib import Path

root = Path("/workspace")

# =========================================================
# BACKEND
# =========================================================

main = root / "backend/app/main.py"
s = main.read_text(encoding="utf-8")

marker = "# ---------------------------------------------------------\n# SELLERS\n# ---------------------------------------------------------"

if "/api/v1/explorer/product/{product_id}" not in s:

    code = r'''
# ---------------------------------------------------------
# PRODUCT & CATEGORY EXPLORER
# ---------------------------------------------------------

@app.get("/api/v1/explorer/product/{product_id}")
def explorer_product(product_id: str):

    product = fetch_one("""
        SELECT
            p.product_id,
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category,
            COUNT(DISTINCT o.order_id)
                FILTER (WHERE o.order_status = 'delivered') AS orders,
            COUNT(*) FILTER (WHERE o.order_status = 'delivered') AS units_sold,
            COUNT(DISTINCT o.customer_id)
                FILTER (WHERE o.order_status = 'delivered') AS customers,
            COUNT(DISTINCT oi.seller_id)
                FILTER (WHERE o.order_status = 'delivered') AS sellers,
            COALESCE(
                SUM(oi.price)
                FILTER (WHERE o.order_status = 'delivered'), 0
            ) AS revenue,
            COALESCE(
                AVG(oi.price)
                FILTER (WHERE o.order_status = 'delivered'), 0
            ) AS average_item_price
        FROM olist_bi.products p
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        LEFT JOIN olist_bi.order_items oi
            ON oi.product_id = p.product_id
        LEFT JOIN olist_bi.orders o
            ON o.order_id = oi.order_id
        WHERE p.product_id = :product_id
        GROUP BY p.product_id, category
    """, {"product_id": product_id})

    if not product:
        raise HTTPException(404, "Product not found")

    monthly = fetch_all("""
        SELECT
            DATE_TRUNC(
                'month', o.order_purchase_timestamp
            )::date AS month,
            COUNT(DISTINCT o.order_id) AS orders,
            COUNT(*) AS units_sold,
            COALESCE(SUM(oi.price), 0) AS revenue
        FROM olist_bi.order_items oi
        JOIN olist_bi.orders o
            ON o.order_id = oi.order_id
        WHERE
            oi.product_id = :product_id
            AND o.order_status = 'delivered'
        GROUP BY 1
        ORDER BY 1
    """, {"product_id": product_id})

    delivery = fetch_one("""
        SELECT
            COUNT(DISTINCT o.order_id) AS delivered_orders,
            AVG(
                EXTRACT(
                    EPOCH FROM (
                        o.order_delivered_customer_date
                        - o.order_purchase_timestamp
                    )
                ) / 86400.0
            ) AS avg_delivery_days,
            AVG(
                CASE
                    WHEN
                        o.order_delivered_customer_date IS NOT NULL
                        AND o.order_estimated_delivery_date IS NOT NULL
                        AND o.order_delivered_customer_date
                            <= o.order_estimated_delivery_date
                    THEN 1.0
                    ELSE 0.0
                END
            ) * 100 AS on_time_rate
        FROM olist_bi.order_items oi
        JOIN olist_bi.orders o
            ON o.order_id = oi.order_id
        WHERE
            oi.product_id = :product_id
            AND o.order_status = 'delivered'
    """, {"product_id": product_id})

    reviews = fetch_one("""
        SELECT
            COUNT(*) AS review_count,
            AVG(r.review_score) AS average_review_score
        FROM olist_bi.reviews r
        JOIN olist_bi.order_items oi
            ON oi.order_id = r.order_id
        WHERE oi.product_id = :product_id
    """, {"product_id": product_id})

    intelligence = fetch_one("""
        SELECT
            i.product_id,
            i.forecast_month,
            i.forecast_demand,
            i.forecast_growth_pct,
            i.forecast_vs_3m_pct,
            i.analysis_month,
            i.trend,
            i.trend_strength,
            i.anomaly_flag,
            i.anomaly_type,
            i.anomaly_severity,
            i.actual_demand,
            i.expected_demand,
            i.health_score,
            i.health_status,
            i.opportunity_score,
            i.risk_score,
            i.decision_priority,
            i.volume_tier,
            i.business_relevance,
            i.recommendation
        FROM olist_bi.v_product_intelligence i
        WHERE i.product_id = :product_id
        LIMIT 1
    """, {"product_id": product_id})

    return {
        "product": product,
        "monthly_sales": monthly,
        "delivery": delivery or {},
        "reviews": reviews or {},
        "intelligence": intelligence or {}
    }


@app.get("/api/v1/explorer/category/{category}")
def explorer_category(category: str):

    category_data = fetch_one("""
        SELECT
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category,
            COUNT(DISTINCT p.product_id) AS products,
            COUNT(DISTINCT o.order_id)
                FILTER (WHERE o.order_status = 'delivered') AS orders,
            COUNT(*) FILTER (WHERE o.order_status = 'delivered')
                AS units_sold,
            COUNT(DISTINCT o.customer_id)
                FILTER (WHERE o.order_status = 'delivered') AS customers,
            COUNT(DISTINCT oi.seller_id)
                FILTER (WHERE o.order_status = 'delivered') AS sellers,
            COALESCE(
                SUM(oi.price)
                FILTER (WHERE o.order_status = 'delivered'), 0
            ) AS revenue,
            COALESCE(
                AVG(oi.price)
                FILTER (WHERE o.order_status = 'delivered'), 0
            ) AS average_item_price
        FROM olist_bi.products p
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        LEFT JOIN olist_bi.order_items oi
            ON oi.product_id = p.product_id
        LEFT JOIN olist_bi.orders o
            ON o.order_id = oi.order_id
        WHERE COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'unknown'
        ) = :category
        GROUP BY 1
    """, {"category": category})

    if not category_data:
        raise HTTPException(404, "Category not found")

    monthly = fetch_all("""
        SELECT
            DATE_TRUNC(
                'month', o.order_purchase_timestamp
            )::date AS month,
            COUNT(DISTINCT o.order_id) AS orders,
            COUNT(*) AS units_sold,
            COALESCE(SUM(oi.price), 0) AS revenue
        FROM olist_bi.order_items oi
        JOIN olist_bi.orders o
            ON o.order_id = oi.order_id
        JOIN olist_bi.products p
            ON p.product_id = oi.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        WHERE
            o.order_status = 'delivered'
            AND COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) = :category
        GROUP BY 1
        ORDER BY 1
    """, {"category": category})

    top_products = fetch_all("""
        SELECT
            oi.product_id,
            COUNT(DISTINCT o.order_id) AS orders,
            COUNT(*) AS units_sold,
            COALESCE(SUM(oi.price), 0) AS revenue
        FROM olist_bi.order_items oi
        JOIN olist_bi.orders o
            ON o.order_id = oi.order_id
        JOIN olist_bi.products p
            ON p.product_id = oi.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        WHERE
            o.order_status = 'delivered'
            AND COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) = :category
        GROUP BY oi.product_id
        ORDER BY revenue DESC
        LIMIT 15
    """, {"category": category})

    forecast = fetch_one("""
        SELECT
            COUNT(*) AS forecast_products,
            COALESCE(SUM(f.forecast_demand), 0)
                AS forecast_demand,
            AVG(f.forecast_vs_3m_pct)
                FILTER (WHERE f.forecast_vs_3m_pct IS NOT NULL)
                AS avg_forecast_vs_3m_pct
        FROM olist_bi.product_forecasts f
        JOIN olist_bi.products p
            ON p.product_id = f.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        WHERE
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) = :category
            AND f.forecast_month = (
                SELECT MAX(f2.forecast_month)
                FROM olist_bi.product_forecasts f2
            )
    """, {"category": category})

    decisions = fetch_one("""
        SELECT
            COUNT(*) AS intelligence_products,
            COUNT(*) FILTER (
                WHERE d.decision_priority = 'high_opportunity'
            ) AS high_opportunity_products,
            COUNT(*) FILTER (
                WHERE d.decision_priority = 'opportunity'
            ) AS opportunity_products,
            COUNT(*) FILTER (
                WHERE d.decision_priority = 'high_risk'
            ) AS high_risk_products,
            COUNT(*) FILTER (
                WHERE d.decision_priority = 'low_volume_risk'
            ) AS low_volume_risk_products,
            COUNT(*) FILTER (
                WHERE d.decision_priority = 'watch'
            ) AS watch_products,
            COUNT(*) FILTER (
                WHERE d.health_status = 'at_risk'
            ) AS at_risk_products,
            COUNT(*) FILTER (
                WHERE d.health_status = 'critical'
            ) AS critical_products,
            AVG(d.opportunity_score) AS avg_opportunity_score,
            AVG(d.risk_score) AS avg_risk_score
        FROM olist_bi.product_decision_scores d
        JOIN olist_bi.products p
            ON p.product_id = d.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        WHERE COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'unknown'
        ) = :category
    """, {"category": category})

    return {
        "category": category_data,
        "monthly_sales": monthly,
        "top_products": top_products,
        "forecast": forecast or {},
        "decisions": decisions or {}
    }


@app.get("/api/v1/explorer/categories")
def explorer_categories():

    rows = fetch_all("""
        SELECT DISTINCT
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category
        FROM olist_bi.products p
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        ORDER BY 1
    """)

    return {
        "items": rows,
        "count": len(rows)
    }

'''

    s = s.replace(marker, code + "\n" + marker)
    main.write_text(s, encoding="utf-8")


# =========================================================
# FRONTEND HTML
# =========================================================

index = root / "frontend/index.html"
s = index.read_text(encoding="utf-8")

nav = '<button class="nav-item" data-page="products">Product Intelligence</button>'

if 'data-page="explorer"' not in s:
    s = s.replace(
        nav,
        nav + '\n      <button class="nav-item" data-page="explorer">Product & Category Explorer</button>'
    )

marker = '    <section id="risk" class="page">'

if '<section id="explorer" class="page">' not in s:

    page = r'''
    <section id="explorer" class="page">

      <div class="section-intro">
        <div>
          <h2>Product & Category Explorer</h2>
          <p>Deep-dive into sales, customers, delivery and ML intelligence.</p>
        </div>
      </div>

      <div class="explorer-switch">
        <button id="explorer-product-btn" class="explorer-mode active">
          Product
        </button>
        <button id="explorer-category-btn" class="explorer-mode">
          Category
        </button>
      </div>

      <div class="explorer-selector card">
        <label id="explorer-label">Select Product</label>
        <select id="explorer-select">
          <option value="">Loading...</option>
        </select>
      </div>

      <div id="explorer-content">
        <p class="loading">Select a product or category to explore.</p>
      </div>

    </section>

'''

    s = s.replace(marker, page + marker)

index.write_text(s, encoding="utf-8")


# =========================================================
# FRONTEND JS
# =========================================================

appjs = root / "frontend/app.js"
s = appjs.read_text(encoding="utf-8")

if "function loadExplorerOptions()" not in s:

    js = r'''

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

'''

    s = s.replace(
        "loadOverview().catch(e => console.error(e));",
        js + "\nloadOverview().catch(e => console.error(e));"
    )

    appjs.write_text(s, encoding="utf-8")


# =========================================================
# FRONTEND CSS
# =========================================================

css = root / "frontend/styles.css"
s = css.read_text(encoding="utf-8")

if ".explorer-switch" not in s:

    s += r'''

/* PRODUCT & CATEGORY EXPLORER */

.explorer-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
}

.explorer-mode {
  border: 1px solid #d1d5db;
  background: #fff;
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.explorer-mode.active {
  background: #111827;
  color: #fff;
}

.explorer-selector {
  margin-bottom: 22px;
}

.explorer-selector label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.explorer-selector select {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  font-size: 14px;
}

.explorer-heading {
  margin: 10px 0 20px;
}

.explorer-heading h2 {
  margin: 4px 0;
}

.explorer-heading p {
  margin: 4px 0;
  opacity: .7;
}

.explorer-grid {
  margin-bottom: 20px;
}

.intelligence-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.intelligence-grid > div {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.intelligence-grid span,
.decision-box span {
  display: block;
  font-size: 12px;
  opacity: .65;
  margin-bottom: 6px;
}

.intelligence-grid strong,
.decision-box strong {
  display: block;
  font-size: 18px;
}

.explorer-decision {
  margin-bottom: 20px;
}

.decision-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.decision-box {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.recommendation-box {
  margin-top: 18px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.recommendation-box p {
  margin: 8px 0 0;
}

@media (max-width: 900px) {
  .decision-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 650px) {
  .intelligence-grid,
  .decision-grid {
    grid-template-columns: 1fr;
  }
}
'''

    css.write_text(s, encoding="utf-8")

print("PATCH COMPLETE")
