const API = window.location.protocol === 'file:' ? 'http://localhost:8000/api/v1' : 'http://localhost:8000/api/v1';
const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s);
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(n||0));
const num=n=>new Intl.NumberFormat('en-US').format(Number(n||0));
const pct=n=>`${Number(n||0)>=0?'+':''}${Number(n||0).toFixed(1)}%`;
async function api(path){const r=await fetch(API+path);if(!r.ok)throw Error(await r.text());return r.json()}
function kpi(label,value,sub=''){return `<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${sub}</div></div>`}
function table(headers,rows){return `<table class="table"><thead><tr>${headers.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(x=>`<td>${x}</td>`).join('')}</tr>`).join('')}</tbody></table>`}
function bars(rows,key,max=12){if(!rows?.length)return '<p class="loading">No data.</p>';const a=rows.slice(-max);const m=Math.max(...a.map(x=>Number(x[key])||0),1);return a.map(x=>`<div class="bar" style="height:${Math.max(3,(Number(x[key])||0)/m*92)}%"><label>${x.month||''} · ${money(x[key])}</label></div>`).join('')}
async function loadOverview(){
  const k=await api('/dashboard/summary'); const ex=await api('/sales/monthly'); const cats=await api('/sales/categories'); const tops=await api('/products/top');
  $('#kpis').innerHTML=[
    kpi('Total Revenue',money(k.total_revenue),'All order items'),
    kpi('Delivered Orders',num(k.delivered_orders),`of ${num(k.total_orders)} total`),
    kpi('Customers',num(k.total_customers),'Delivered-order customers'),
    kpi('Products',num(k.total_products),'Catalog'),
    kpi('Opportunity Products',num(k.opportunity_products),'10 high opportunity'),
    kpi('High-Risk Products',num(k.high_risk_products),'Critical signal'),
    kpi('Anomaly Products',num(k.anomaly_products),'Detected signals'),
    kpi('Sellers',num(k.total_sellers),'Seller network')
  ].join('');
  $('#revenue-chart').innerHTML=bars(ex,'revenue');
  const healthy=k.healthy_products||0, watch=k.watch_products||0, risk=(k.at_risk_products||0)+(k.critical_products||0), total=healthy+watch+risk||1;
  const a=healthy/total*100,b=(healthy+watch)/total*100;
  $('#health-chart').innerHTML=`<div class="donut" style="background:conic-gradient(#1f2937 0 ${a}%,#64748b ${a}% ${b}%,#a8b2c1 ${b}% 100%)"></div><div class="legend"><div><i></i>Healthy ${num(healthy)}</div><div><i></i>Watch ${num(watch)}</div><div><i></i>At risk/Critical ${num(risk)}</div></div>`;
  $('#categories').innerHTML=table(['Category','Orders','Revenue'],cats.slice(0,8).map(x=>[x.category,num(x.orders),money(x.revenue)]));
  $('#top-products').innerHTML=table(['Product','Category','Revenue'],tops.slice(0,8).map(x=>[x.product_id.slice(0,10)+'…',x.category,money(x.revenue)]));
}
async function loadSales(){const s=await api('/sales/monthly'),c=await api('/sales/categories'),p=await api('/payments');$('#sales-chart').innerHTML=bars(s,'revenue',18);$('#sales-categories').innerHTML=table(['Category','Orders','Units','Revenue'],c.slice(0,15).map(x=>[x.category,num(x.orders),num(x.units_sold),money(x.revenue)]));$('#payments').innerHTML=table(['Method','Orders','Value'],p.slice(0,10).map(x=>[x.payment_type,num(x.payment_count),money(x.payment_value)]))}
let productView='forecast';
async function loadProducts(){let path=productView==='forecast'?'/forecast?limit=25':productView==='opportunity'?'/opportunities?limit=25':'/risks?limit=25';const d=await api(path);let rows=d.rows||d; if(productView==='forecast')$('#product-table').innerHTML=table(['Product','Category','Forecast','Vs 3M','Month'],rows.map(x=>[x.product_id.slice(0,12)+'…',x.category,num(x.forecast_demand),pct(x.forecast_vs_3m_pct),String(x.forecast_month).slice(0,10)]));else $('#product-table').innerHTML=table(['Product','Category','Health','Opportunity','Risk','Priority'],rows.map(x=>[x.product_id.slice(0,12)+'…',x.category,`<span class="badge ${x.health_status==='healthy'?'good':x.health_status==='critical'||x.health_status==='at_risk'?'bad':'warn'}">${x.health_status}</span>`,num(x.opportunity_score),num(x.risk_score),x.decision_priority]));}
async function loadRisk(){const k=await api('/dashboard/summary'),a=await api('/anomalies?limit=30');$('#risk-kpis').innerHTML=[kpi('Anomalies',num(k.anomaly_products)),kpi('Critical',num(k.critical_products)),kpi('At Risk',num(k.at_risk_products)),kpi('High Risk',num(k.high_risk_products))].join('');const rows=a.rows||a;$('#anomaly-table').innerHTML=table(['Product','Category','Type','Severity','Actual','Expected'],rows.map(x=>[x.product_id.slice(0,12)+'…',x.category,x.anomaly_type,x.anomaly_severity,num(x.actual_demand),num(x.expected_demand)]))}
function showPage(name){$$('.page').forEach(x=>x.classList.remove('active'));$('#'+name).classList.add('active');$$('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.page===name));$('#page-title').textContent={overview:'Executive Overview',sales:'Sales Analytics',products:'Product Intelligence',risk:'Risk & Anomalies',analyst:'AI Business Analyst'}[name];if(name==='overview')loadOverview();if(name==='sales')loadSales();if(name==='products')loadProducts();if(name==='risk')loadRisk()}
async function ask(q){if(!q)return;const chat=$('#chat');chat.innerHTML+=`<div class="msg user">${q}</div><div class="msg bot loading">Analyzing...</div>`;chat.scrollTop=chat.scrollHeight;try{const d=await api('/analyst?q='+encodeURIComponent(q));const last=chat.querySelector('.msg.bot.loading');last.classList.remove('loading');last.textContent=d.answer||JSON.stringify(d,null,2)}catch(e){const last=chat.querySelector('.msg.bot.loading');last.classList.remove('loading');last.textContent='Unable to reach the business analyst API.'}}
$$('.nav-item').forEach(b=>b.onclick=()=>showPage(b.dataset.page));$$('.tab').forEach(b=>b.onclick=()=>{$$('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');productView=b.dataset.productView;loadProducts()});$$('.suggestions button').forEach(b=>b.onclick=()=>{showPage('analyst');$('#question').value=b.textContent;ask(b.textContent)});$('#ask-form').onsubmit=e=>{e.preventDefault();const q=$('#question').value.trim();$('#question').value='';ask(q)};$('#refresh').onclick=()=>showPage(document.querySelector('.page.active').id);loadOverview().catch(e=>console.error(e));
