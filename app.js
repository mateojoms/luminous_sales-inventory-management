const STORAGE_KEY = 'stamp-stock-sales-manager-v1';
const KSH = new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES', maximumFractionDigits: 0 });

const seedData = () => {
  const now = new Date().toISOString();
  const products = [
    product('Self-Inking Stamp', 'Stamp', 'Trodat-style office stamp', 300, 600, 20, 5, 'Nairobi Stationers', { type: 'Self-Inking' }),
    product('Black Stamp Ink', 'Ink', 'General-purpose refill ink', 100, 200, 10, 3, 'Ink World', { color: 'Black', sizeVolume: '30ml' }),
    product('Large Stamp Pad', 'Stamp Pad', 'Desktop stamp pad', 150, 300, 4, 5, 'Print Supplies Ltd', { color: 'Blue', type: 'Large' }),
    product('Custom Logo Stamp Service', 'Custom Order', 'Made-to-order company stamp', 0, 800, 0, 0, 'In-house', { trackStock: false })
  ];
  const suppliers = [
    { id: uid(), name: 'Nairobi Stationers', phone: '+254 700 000 001', email: 'sales@nairobi-stationers.example', address: 'Nairobi CBD', notes: 'Stamp bodies and office supplies', active: true, createdAt: now },
    { id: uid(), name: 'Ink World', phone: '+254 700 000 002', email: 'orders@inkworld.example', address: 'Industrial Area', notes: 'Ink refills', active: true, createdAt: now },
    { id: uid(), name: 'Print Supplies Ltd', phone: '+254 700 000 003', email: 'hello@printsupplies.example', address: 'Mombasa Road', notes: 'Pads and accessories', active: true, createdAt: now }
  ];
  const movements = products.filter(p => p.category !== 'Custom Order').map(p => ({
    id: uid(), productId: p.id, productName: p.name, movementType: 'STOCK PURCHASE', quantity: p.currentStock,
    previousStock: 0, newStock: p.currentStock, reference: 'Opening stock', notes: 'Initial sample stock', createdBy: 'System', createdAt: now
  }));
  return {
    products,
    suppliers,
    sales: [],
    saleItems: [],
    stockMovements: movements,
    returns: [],
    users: [
      { id: uid(), displayName: 'Owner / Administrator', role: 'Administrator', active: true, createdAt: now },
      { id: uid(), displayName: 'Sales Counter User', role: 'Sales User', active: true, createdAt: now }
    ],
    auditLogs: [],
    sequence: 1,
    mode: 'local'
  };
};

function product(name, category, description, costPrice, sellingPrice, currentStock, minimumStock, supplier, extras = {}) {
  const now = new Date().toISOString();
  return {
    id: uid(), name, category, description, costPrice, sellingPrice, currentStock, minimumStock, supplier,
    active: true, createdAt: now, updatedAt: now, type: extras.type || '', color: extras.color || '', sizeVolume: extras.sizeVolume || '', trackStock: extras.trackStock !== false
  };
}

function uid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

let db = load();
let currentView = 'dashboard';
let currentUserId = db.users[0]?.id;
let notice = '';
let noticeType = 'success';
let saleLines = [{ productId: '', itemType: 'stock', customName: '', quantity: 1, unitPrice: 0 }];
let filters = { products: '', stock: '', sales: '', payment: '', report: 'today' };

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && Array.isArray(saved.products)) return saved;
  } catch {}
  const seeded = seedData();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded));
  return seeded;
}

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
}

function h(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

function money(value) { return KSH.format(Number(value || 0)); }
function todayText(date = new Date()) { return date.toISOString().slice(0, 10); }
function asDate(value) { return new Date(value); }
function currentUser() { return db.users.find(u => u.id === currentUserId) || db.users[0]; }
function isAdmin() { return currentUser()?.role === 'Administrator'; }
function canManageStock() { return isAdmin(); }
function productStatus(p) {
  if (!p.trackStock) return 'Custom Order';
  if (p.currentStock <= 0) return 'Out of Stock';
  if (p.currentStock <= p.minimumStock) return 'Low Stock';
  return 'In Stock';
}
function statusPill(status) {
  const cls = status === 'In Stock' ? 'success' : status === 'Low Stock' ? 'warning' : status === 'Out of Stock' ? 'danger' : 'neutral';
  return `<span class="pill ${cls}">${h(status)}</span>`;
}
function activeProducts() { return db.products.filter(p => p.active); }
function stockProducts() { return db.products.filter(p => p.trackStock); }
function byId(id) { return db.products.find(p => p.id === id); }
function setNotice(message, type = 'success') { notice = message; noticeType = type; render(); }
function clearNotice() { notice = ''; }

function periodRange(key) {
  const now = new Date();
  const start = new Date(now);
  const end = new Date(now);
  start.setHours(0, 0, 0, 0); end.setHours(23, 59, 59, 999);
  if (key === 'yesterday') { start.setDate(start.getDate() - 1); end.setDate(end.getDate() - 1); }
  if (key === 'week') { start.setDate(start.getDate() - ((start.getDay() + 6) % 7)); }
  if (key === 'month') { start.setDate(1); }
  if (key === 'all') return [new Date(0), new Date(8640000000000000)];
  return [start, end];
}

function salesInRange(key) {
  const [start, end] = periodRange(key);
  return db.sales.filter(s => s.status !== 'VOID' && asDate(s.createdAt) >= start && asDate(s.createdAt) <= end);
}

function metrics() {
  const todaySales = salesInRange('today');
  const weekSales = salesInRange('week');
  const monthSales = salesInRange('month');
  const allSales = salesInRange('all');
  const stock = stockProducts();
  const totalItemsSold = db.saleItems.reduce((sum, item) => sum + (item.itemType === 'stock' ? Number(item.quantity) : 0), 0);
  return {
    productCount: db.products.length,
    stockUnits: stock.reduce((sum, p) => sum + Number(p.currentStock), 0),
    lowStock: stock.filter(p => p.currentStock > 0 && p.currentStock <= p.minimumStock).length,
    outStock: stock.filter(p => p.currentStock <= 0).length,
    stockValue: stock.reduce((sum, p) => sum + Number(p.currentStock) * Number(p.costPrice), 0),
    todaySales: todaySales.reduce((sum, s) => sum + Number(s.totalAmount), 0),
    todayTransactions: todaySales.length,
    weekSales: weekSales.reduce((sum, s) => sum + Number(s.totalAmount), 0),
    monthSales: monthSales.reduce((sum, s) => sum + Number(s.totalAmount), 0),
    allSales: allSales.reduce((sum, s) => sum + Number(s.totalAmount), 0),
    totalItemsSold,
    todayProfit: todaySales.reduce((sum, s) => sum + Number(s.grossProfit), 0),
    monthProfit: monthSales.reduce((sum, s) => sum + Number(s.grossProfit), 0),
    allProfit: allSales.reduce((sum, s) => sum + Number(s.grossProfit), 0)
  };
}

function appLayout(content) {
  const m = metrics();
  const nav = [
    ['dashboard', 'Dashboard'], ['sales', 'Sales'], ['inventory', 'Inventory'], ['products', 'Products'], ['suppliers', 'Suppliers'], ['reports', 'Reports'], ['settings', 'Settings']
  ];
  return `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="logo"><div class="logo-mark">SS</div><div><h1>Stamp Stock Manager</h1><p>Stock, sales & reports</p></div></div>
        <nav class="nav">${nav.map(([key, label]) => `<button class="${currentView === key ? 'active' : ''}" data-view="${key}">${label}</button>`).join('')}</nav>
        <div class="sidebar-card">
          <label for="userSwitch">Signed in role</label>
          <select id="userSwitch">${db.users.filter(u => u.active).map(u => `<option value="${u.id}" ${u.id === currentUserId ? 'selected' : ''}>${h(u.displayName)} — ${h(u.role)}</option>`).join('')}</select>
          <p class="small">Administrator controls stock, products and settings. Sales users can record sales and view records.</p>
        </div>
        <div class="sidebar-card"><strong>${money(m.allSales)}</strong><p class="small">Cumulative sales from completed transactions.</p></div>
      </aside>
      <main class="main">
        ${notice ? `<div class="notice ${noticeType}">${h(notice)}</div>` : ''}
        ${content}
      </main>
    </div>
  `;
}

function pageHeader(title, subtitle) {
  return `<div class="topbar"><div><h2>${h(title)}</h2><p>${h(subtitle)}</p></div><span class="status-pill">${db.mode === 'remote' ? 'Database mode' : 'Local sample mode'}</span></div>`;
}

function dashboard() {
  const m = metrics();
  return `${pageHeader('Business dashboard', 'Live view of inventory, sales, stock value and gross profit.')}
    <section class="grid cards">
      ${metric('Today\'s Sales', money(m.todaySales), `${m.todayTransactions} transaction(s)`)}
      ${metric('Current Stock', `${m.stockUnits} units`, `${m.productCount} products`)}
      ${metric('Low Stock', `${m.lowStock} products`, `${m.outStock} out of stock`)}
      ${metric('Cumulative Sales', money(m.allSales), `${m.totalItemsSold} stock items sold`)}
      ${metric('Stock Value', money(m.stockValue), 'Based on cost price')}
      ${metric('Today\'s Gross Profit', money(m.todayProfit), 'Excludes operating expenses')}
      ${metric('Monthly Sales', money(m.monthSales), 'Current month')}
      ${metric('Monthly Gross Profit', money(m.monthProfit), 'Estimated gross profit')}
    </section>
    <section class="section-grid">
      <div class="card"><div class="split"><h3>Quick actions</h3><span class="small">Most used workflows</span></div><div class="actions">
        ${quick('sales', 'Record Sale')} ${quick('inventory', 'Add Stock')} ${isAdmin() ? quick('products', 'Add Product') : ''} ${quick('inventory', 'View Stock')} ${quick('sales', 'View Sales')} ${quick('reports', 'View Reports')}
      </div></div>
      <div class="card"><h3>Stock alerts</h3>${stockAlerts()}</div>
    </section>
    <section class="section-grid">
      <div class="card"><h3>Sales over last 7 days</h3>${salesChart(7)}</div>
      <div class="card"><h3>Best-selling products</h3>${bestSellers()}</div>
    </section>`;
}

function metric(label, value, note) { return `<article class="card metric-card"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-note">${note}</div></article>`; }
function quick(view, label) { return `<button data-view="${view}">${label}</button>`; }
function stockAlerts() {
  const items = stockProducts().filter(p => productStatus(p) !== 'In Stock');
  if (!items.length) return '<p class="empty">No low-stock or out-of-stock products.</p>';
  return `<div class="table-wrap"><table><thead><tr><th>Product</th><th>Current</th><th>Minimum</th><th>Status</th></tr></thead><tbody>${items.map(p => `<tr><td>${h(p.name)}</td><td>${p.currentStock}</td><td>${p.minimumStock}</td><td>${statusPill(productStatus(p))}</td></tr>`).join('')}</tbody></table></div>`;
}
function salesChart(days) {
  const rows = [];
  const max = Math.max(1, ...Array.from({ length: days }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (days - i - 1));
    return salesByDate(todayText(d));
  }));
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const total = salesByDate(todayText(d));
    rows.push(`<div class="bar-row"><span>${todayText(d).slice(5)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(4, total / max * 100)}%"></div></div><strong>${money(total)}</strong></div>`);
  }
  return `<div class="chart">${rows.join('')}</div>`;
}
function salesByDate(date) { return db.sales.filter(s => s.status !== 'VOID' && s.createdAt.slice(0, 10) === date).reduce((sum, s) => sum + s.totalAmount, 0); }
function bestSellers() {
  const totals = {};
  db.saleItems.forEach(i => { totals[i.productName] = (totals[i.productName] || 0) + i.quantity; });
  const rows = Object.entries(totals).sort((a,b) => b[1] - a[1]).slice(0, 5);
  if (!rows.length) return '<p class="empty">Record sales to see best sellers.</p>';
  const max = Math.max(...rows.map(r => r[1]));
  return `<div class="chart">${rows.map(([name, qty]) => `<div class="bar-row"><span>${h(name)}</span><div class="bar-track"><div class="bar-fill" style="width:${qty / max * 100}%"></div></div><strong>${qty}</strong></div>`).join('')}</div>`;
}

function sales() {
  const query = filters.sales.toLowerCase();
  const list = db.sales.filter(s => (!query || [s.saleNumber, s.customerName, s.paymentMethod].join(' ').toLowerCase().includes(query)) && (!filters.payment || s.paymentMethod === filters.payment)).sort((a,b) => b.createdAt.localeCompare(a.createdAt));
  return `${pageHeader('Sales', 'Record single-product, multi-product and custom stamp orders.')}
    <section class="section-grid">
      <div class="card"><h3>New sale</h3>${saleForm()}</div>
      <div class="card"><h3>Sales history</h3><div class="toolbar"><input id="salesSearch" placeholder="Search sale number, customer, payment" value="${h(filters.sales)}"><select id="paymentFilter"><option value="">All payments</option>${['Cash','M-Pesa','Bank','Other'].map(p => `<option ${filters.payment === p ? 'selected' : ''}>${p}</option>`).join('')}</select></div>${salesTable(list)}</div>
    </section>`;
}

function saleForm() {
  const products = activeProducts();
  const rows = saleLines.map((line, i) => {
    const selected = byId(line.productId);
    const price = line.itemType === 'stock' && selected ? selected.sellingPrice : line.unitPrice;
    return `<div class="sale-line" data-line="${i}">
      <label><span>Item</span><select class="sale-product"><option value="">Select stock item</option>${products.filter(p => p.trackStock).map(p => `<option value="${p.id}" ${p.id === line.productId ? 'selected' : ''}>${h(p.name)} (${p.currentStock} available)</option>`).join('')}<option value="custom" ${line.itemType === 'custom' ? 'selected' : ''}>Custom stamp order</option></select></label>
      <label><span>Quantity</span><input class="sale-qty" type="number" min="1" value="${line.quantity}"></label>
      <label><span>Unit price</span><input class="sale-price" type="number" min="0" value="${price}"></label>
      <label><span>Subtotal</span><input disabled value="${money(Number(line.quantity) * Number(price))}"></label>
      <button class="danger remove-line" ${saleLines.length === 1 ? 'disabled' : ''}>Remove</button>
      ${line.itemType === 'custom' ? `<label class="full"><span>Custom order name</span><input class="custom-name" value="${h(line.customName || 'Custom Company Stamp')}" placeholder="Custom Company Stamp"></label>` : ''}
    </div>`;
  }).join('');
  const total = saleLines.reduce((sum, line) => {
    const p = byId(line.productId);
    return sum + Number(line.quantity || 0) * Number(line.itemType === 'stock' && p ? p.sellingPrice : line.unitPrice || 0);
  }, 0);
  return `<form id="saleForm" class="sale-builder">
    <div class="form-grid"><label><span>Date</span><input name="date" type="date" value="${todayText()}"></label><label><span>Customer name (optional)</span><input name="customerName" placeholder="Walk-in customer"></label><label><span>Payment method</span><select name="paymentMethod">${['Cash','M-Pesa','Bank','Other'].map(p => `<option>${p}</option>`).join('')}</select></label><label><span>Notes</span><input name="notes" placeholder="Optional receipt notes"></label></div>
    ${rows}
    <div class="split"><button type="button" id="addSaleLine" class="secondary">Add another item</button><strong>Grand total: ${money(total)}</strong></div>
    <button type="submit">Save sale and deduct stock</button>
  </form>`;
}

function salesTable(list) {
  if (!list.length) return '<p class="empty">No sales match the current filters.</p>';
  return `<div class="table-wrap"><table><thead><tr><th>Sale number</th><th>Date/time</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Status</th><th>Actions</th></tr></thead><tbody>${list.map(s => {
    const items = db.saleItems.filter(i => i.saleId === s.id).map(i => `${h(i.productName)} × ${i.quantity}`).join('<br>');
    return `<tr><td>${h(s.saleNumber)}</td><td>${h(new Date(s.createdAt).toLocaleString())}</td><td>${h(s.customerName || 'Walk-in')}</td><td>${items}</td><td>${money(s.totalAmount)}</td><td>${h(s.paymentMethod)}</td><td>${statusPill(s.status)}</td><td class="row-actions"><button class="ghost view-sale" data-id="${s.id}">View</button><button class="secondary print-sale" data-id="${s.id}">Print</button></td></tr>`;
  }).join('')}</tbody></table></div>`;
}

function inventory() {
  const query = filters.stock.toLowerCase();
  const products = stockProducts().filter(p => !query || [p.name, p.category, p.type, p.color].join(' ').toLowerCase().includes(query));
  return `${pageHeader('Inventory', 'View current stock, add purchases, make adjustments and trace every movement.')}
    <div class="toolbar"><input id="stockSearch" placeholder="Search stock by name, category, type or color" value="${h(filters.stock)}"></div>
    <section class="card"><h3>Current stock</h3>${stockTable(products)}</section>
    <section class="section-grid"><div class="card"><h3>Add stock</h3>${addStockForm()}</div><div class="card"><h3>Stock adjustment</h3>${adjustmentForm()}</div></section>
    <section class="section-grid"><div class="card"><h3>Returns</h3>${returnForm()}</div><div class="card"><h3>Inventory movement history</h3>${movementTable(db.stockMovements.slice().sort((a,b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 20))}</div></section>`;
}

function stockTable(products) {
  if (!products.length) return '<p class="empty">No stock products found.</p>';
  return `<div class="table-wrap"><table><thead><tr><th>Product</th><th>Category</th><th>Current Stock</th><th>Minimum Level</th><th>Cost Price</th><th>Selling Price</th><th>Stock Status</th></tr></thead><tbody>${products.map(p => `<tr><td><strong>${h(p.name)}</strong><div class="small">${h(p.description)}</div></td><td>${h(p.category)}</td><td>${p.currentStock}</td><td>${p.minimumStock}</td><td>${money(p.costPrice)}</td><td>${money(p.sellingPrice)}</td><td>${statusPill(productStatus(p))}</td></tr>`).join('')}</tbody></table></div>`;
}

function productOptions() { return stockProducts().filter(p => p.active).map(p => `<option value="${p.id}">${h(p.name)} (${p.currentStock})</option>`).join(''); }
function addStockForm() { return canManageStock() ? `<form id="addStockForm" class="form-grid"><label><span>Product</span><select name="productId">${productOptions()}</select></label><label><span>Quantity received</span><input name="quantity" type="number" min="1" required></label><label><span>Cost per unit</span><input name="costPrice" type="number" min="0" required></label><label><span>Supplier</span><input name="supplier" required></label><label><span>Date received</span><input name="date" type="date" value="${todayText()}" required></label><label class="full"><span>Notes</span><textarea name="notes"></textarea></label><button type="submit">Add stock</button></form>` : '<p class="empty">Only administrators can add stock.</p>'; }
function adjustmentForm() { return canManageStock() ? `<form id="adjustmentForm" class="form-grid"><label><span>Product</span><select name="productId">${productOptions()}</select></label><label><span>Actual quantity</span><input name="actualQuantity" type="number" min="0" required></label><label class="full"><span>Adjustment reason</span><textarea name="reason" required placeholder="Example: 1 bottle damaged."></textarea></label><button type="submit">Record adjustment</button></form>` : '<p class="empty">Only administrators can adjust stock.</p>'; }
function returnForm() {
  const sales = db.sales.filter(s => s.status !== 'VOID');
  return `<form id="returnForm" class="form-grid"><label><span>Original sale</span><select name="saleId">${sales.map(s => `<option value="${s.id}">${h(s.saleNumber)} — ${money(s.totalAmount)}</option>`).join('')}</select></label><label><span>Product</span><select name="productId">${productOptions()}</select></label><label><span>Returned quantity</span><input name="quantity" type="number" min="1" required></label><label class="full"><span>Return reason</span><textarea name="reason" required></textarea></label><button type="submit">Process return</button></form>`;
}
function movementTable(rows) {
  if (!rows.length) return '<p class="empty">No stock movements recorded.</p>';
  return `<div class="table-wrap"><table><thead><tr><th>Date/time</th><th>Product</th><th>Type</th><th>Qty</th><th>Previous</th><th>New</th><th>Reference</th><th>User</th></tr></thead><tbody>${rows.map(m => `<tr><td>${h(new Date(m.createdAt).toLocaleString())}</td><td>${h(m.productName)}</td><td>${h(m.movementType)}</td><td>${m.quantity}</td><td>${m.previousStock}</td><td>${m.newStock}</td><td>${h(m.reference)}</td><td>${h(m.createdBy)}</td></tr>`).join('')}</tbody></table></div>`;
}

function products() {
  const query = filters.products.toLowerCase();
  const list = db.products.filter(p => !query || [p.name, p.category, p.type, p.color].join(' ').toLowerCase().includes(query));
  return `${pageHeader('Products', 'Manage stamps, inks, pads and custom order items without deleting sales history.')}
    ${isAdmin() ? `<section class="card"><h3>Add product</h3>${productForm()}</section>` : '<div class="notice">Sales users can view products but cannot change them.</div>'}
    <div class="toolbar"><input id="productSearch" placeholder="Search product name, category, type or color" value="${h(filters.products)}"></div>
    <section class="card"><h3>Product list</h3>${productTable(list)}</section>`;
}
function productForm(existing = {}) {
  return `<form id="productForm" class="form-grid"><input type="hidden" name="id" value="${h(existing.id || '')}"><label><span>Product name</span><input name="name" required value="${h(existing.name || '')}"></label><label><span>Category</span><select name="category">${['Stamp','Ink','Stamp Pad','Custom Order','Other'].map(c => `<option ${existing.category === c ? 'selected' : ''}>${c}</option>`).join('')}</select></label><label class="full"><span>Description</span><textarea name="description">${h(existing.description || '')}</textarea></label><label><span>Type</span><input name="type" value="${h(existing.type || '')}"></label><label><span>Color</span><input name="color" value="${h(existing.color || '')}"></label><label><span>Size/volume</span><input name="sizeVolume" value="${h(existing.sizeVolume || '')}"></label><label><span>Supplier</span><input name="supplier" value="${h(existing.supplier || '')}"></label><label><span>Cost price</span><input name="costPrice" type="number" min="0" required value="${existing.costPrice ?? 0}"></label><label><span>Selling price</span><input name="sellingPrice" type="number" min="0" required value="${existing.sellingPrice ?? 0}"></label><label><span>Current quantity</span><input name="currentStock" type="number" min="0" required value="${existing.currentStock ?? 0}"></label><label><span>Minimum stock level</span><input name="minimumStock" type="number" min="0" required value="${existing.minimumStock ?? 0}"></label><label><span>Active status</span><select name="active"><option value="true" ${existing.active !== false ? 'selected' : ''}>Active</option><option value="false" ${existing.active === false ? 'selected' : ''}>Inactive</option></select></label><label><span>Track stock</span><select name="trackStock"><option value="true" ${existing.trackStock !== false ? 'selected' : ''}>Yes</option><option value="false" ${existing.trackStock === false ? 'selected' : ''}>No, custom order/service</option></select></label><button type="submit">${existing.id ? 'Save product' : 'Add product'}</button></form>`;
}
function productTable(list) {
  if (!list.length) return '<p class="empty">No products found.</p>';
  return `<div class="table-wrap"><table><thead><tr><th>Product</th><th>Category</th><th>Stock</th><th>Prices</th><th>Supplier</th><th>Status</th><th>Actions</th></tr></thead><tbody>${list.map(p => `<tr><td><strong>${h(p.name)}</strong><div class="small">${h([p.type,p.color,p.sizeVolume].filter(Boolean).join(' · '))}</div></td><td>${h(p.category)}</td><td>${p.trackStock ? p.currentStock : 'Not deducted'}</td><td>Cost ${money(p.costPrice)}<br>Sell ${money(p.sellingPrice)}</td><td>${h(p.supplier)}</td><td>${statusPill(p.active ? productStatus(p) : 'Inactive')}</td><td class="row-actions"><button class="ghost view-history" data-id="${p.id}">History</button>${isAdmin() ? `<button class="secondary edit-product" data-id="${p.id}">Edit</button><button class="danger deactivate-product" data-id="${p.id}">${p.active ? 'Deactivate' : 'Activate'}</button>` : ''}</td></tr>`).join('')}</tbody></table></div>`;
}

function suppliers() {
  return `${pageHeader('Suppliers', 'Keep supplier contacts connected to products and stock purchases.')}
    ${isAdmin() ? `<section class="card"><h3>Add supplier</h3><form id="supplierForm" class="form-grid"><label><span>Name</span><input name="name" required></label><label><span>Phone</span><input name="phone"></label><label><span>Email</span><input name="email" type="email"></label><label><span>Address</span><input name="address"></label><label class="full"><span>Notes</span><textarea name="notes"></textarea></label><button type="submit">Save supplier</button></form></section>` : ''}
    <section class="card"><h3>Supplier list</h3><div class="table-wrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Address</th><th>Notes</th></tr></thead><tbody>${db.suppliers.map(s => `<tr><td>${h(s.name)}</td><td>${h(s.phone)}</td><td>${h(s.email)}</td><td>${h(s.address)}</td><td>${h(s.notes)}</td></tr>`).join('')}</tbody></table></div></section>`;
}

function reports() {
  const sales = salesInRange(filters.report);
  const itemIds = new Set(sales.map(s => s.id));
  const items = db.saleItems.filter(i => itemIds.has(i.saleId));
  const revenue = sales.reduce((sum, s) => sum + s.totalAmount, 0);
  const profit = sales.reduce((sum, s) => sum + s.grossProfit, 0);
  return `${pageHeader('Reports', 'Daily, weekly, monthly and cumulative totals are calculated from recorded sales.')}
    <div class="toolbar"><select id="reportFilter">${[['today','Today'],['yesterday','Yesterday'],['week','This week'],['month','This month'],['all','Cumulative']].map(([v,l]) => `<option value="${v}" ${filters.report === v ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
    <section class="grid cards">${metric('Transactions', sales.length, 'Completed sales')} ${metric('Items sold', items.reduce((sum, i) => sum + i.quantity, 0), 'Stock and custom lines')} ${metric('Revenue', money(revenue), 'Gross sales')} ${metric('Gross Profit', money(profit), 'Before expenses')}</section>
    <section class="section-grid"><div class="card"><h3>Sales by payment method</h3>${paymentChart(sales)}</div><div class="card"><h3>Stock levels</h3>${stockLevelChart()}</div></section>
    <section class="card"><h3>Report details</h3>${salesTable(sales)}</section>`;
}
function paymentChart(sales) {
  const rows = ['Cash','M-Pesa','Bank','Other'].map(method => [method, sales.filter(s => s.paymentMethod === method).reduce((sum, s) => sum + s.totalAmount, 0)]);
  const max = Math.max(1, ...rows.map(r => r[1]));
  return `<div class="chart">${rows.map(([name,total]) => `<div class="bar-row"><span>${name}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(4,total/max*100)}%"></div></div><strong>${money(total)}</strong></div>`).join('')}</div>`;
}
function stockLevelChart() {
  const rows = stockProducts().slice().sort((a,b) => a.currentStock - b.currentStock).slice(0, 8);
  const max = Math.max(1, ...rows.map(p => p.currentStock));
  return `<div class="chart">${rows.map(p => `<div class="bar-row"><span>${h(p.name)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(4,p.currentStock/max*100)}%"></div></div><strong>${p.currentStock}</strong></div>`).join('')}</div>`;
}

function settings() {
  return `${pageHeader('Settings', 'Manage users and application audit information.')}
    <section class="section-grid"><div class="card"><h3>Users</h3>${userSection()}</div><div class="card"><h3>Data tools</h3><p class="small">Use these tools for local sample-mode testing only.</p><div class="actions"><button id="resetData" class="danger">Reset sample data</button><button id="exportData" class="secondary">Download JSON backup</button></div></div></section>
    <section class="card"><h3>Audit trail</h3>${auditTable()}</section>`;
}
function userSection() {
  const form = isAdmin() ? `<form id="userForm" class="form-grid"><label><span>Display name</span><input name="displayName" required></label><label><span>Role</span><select name="role"><option>Administrator</option><option>Sales User</option></select></label><button type="submit">Add user</button></form>` : '<p class="empty">Only administrators can manage users.</p>';
  return `${form}<div class="table-wrap"><table><thead><tr><th>Name</th><th>Role</th><th>Status</th></tr></thead><tbody>${db.users.map(u => `<tr><td>${h(u.displayName)}</td><td>${h(u.role)}</td><td>${statusPill(u.active ? 'Active' : 'Inactive')}</td></tr>`).join('')}</tbody></table></div>`;
}
function auditTable() {
  const rows = db.auditLogs.slice().sort((a,b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 30);
  if (!rows.length) return '<p class="empty">No audit entries yet.</p>';
  return `<div class="table-wrap"><table><thead><tr><th>Date/time</th><th>User</th><th>Action</th><th>Entity</th><th>Previous</th><th>New</th></tr></thead><tbody>${rows.map(a => `<tr><td>${h(new Date(a.createdAt).toLocaleString())}</td><td>${h(a.actor)}</td><td>${h(a.action)}</td><td>${h(a.entityType)} ${h(a.entityId || '')}</td><td><pre>${h(JSON.stringify(a.previousValue || {}, null, 0))}</pre></td><td><pre>${h(JSON.stringify(a.newValue || {}, null, 0))}</pre></td></tr>`).join('')}</tbody></table></div>`;
}

function bindCommon() {
  document.querySelectorAll('[data-view]').forEach(btn => btn.addEventListener('click', () => { clearNotice(); currentView = btn.dataset.view; render(); }));
  document.getElementById('userSwitch')?.addEventListener('change', e => { currentUserId = e.target.value; setNotice(`Role switched to ${currentUser().role}.`); });
}
function bindView() {
  document.getElementById('productSearch')?.addEventListener('input', e => { filters.products = e.target.value; render(); });
  document.getElementById('stockSearch')?.addEventListener('input', e => { filters.stock = e.target.value; render(); });
  document.getElementById('salesSearch')?.addEventListener('input', e => { filters.sales = e.target.value; render(); });
  document.getElementById('paymentFilter')?.addEventListener('change', e => { filters.payment = e.target.value; render(); });
  document.getElementById('reportFilter')?.addEventListener('change', e => { filters.report = e.target.value; render(); });
  document.getElementById('addSaleLine')?.addEventListener('click', () => { saleLines.push({ productId: '', itemType: 'stock', customName: '', quantity: 1, unitPrice: 0 }); render(); });
  document.querySelectorAll('.sale-product,.sale-qty,.sale-price,.custom-name').forEach(el => el.addEventListener('input', syncSaleLines));
  document.querySelectorAll('.remove-line').forEach(btn => btn.addEventListener('click', e => { e.preventDefault(); saleLines.splice(Number(btn.closest('.sale-line').dataset.line), 1); render(); }));
  document.getElementById('saleForm')?.addEventListener('submit', recordSale);
  document.getElementById('addStockForm')?.addEventListener('submit', addStock);
  document.getElementById('adjustmentForm')?.addEventListener('submit', adjustStock);
  document.getElementById('returnForm')?.addEventListener('submit', processReturn);
  document.getElementById('productForm')?.addEventListener('submit', saveProduct);
  document.getElementById('supplierForm')?.addEventListener('submit', saveSupplier);
  document.getElementById('userForm')?.addEventListener('submit', saveUser);
  document.getElementById('resetData')?.addEventListener('click', () => { db = seedData(); currentUserId = db.users[0].id; save(); setNotice('Sample data reset.'); });
  document.getElementById('exportData')?.addEventListener('click', exportData);
  document.querySelectorAll('.deactivate-product').forEach(btn => btn.addEventListener('click', () => toggleProduct(btn.dataset.id)));
  document.querySelectorAll('.edit-product').forEach(btn => btn.addEventListener('click', () => openProductEditor(btn.dataset.id)));
  document.querySelectorAll('.view-history').forEach(btn => btn.addEventListener('click', () => openProductHistory(btn.dataset.id)));
  document.querySelectorAll('.view-sale').forEach(btn => btn.addEventListener('click', () => openSale(btn.dataset.id)));
  document.querySelectorAll('.print-sale').forEach(btn => btn.addEventListener('click', () => printSale(btn.dataset.id)));
}
function syncSaleLines(shouldRender = true) {
  document.querySelectorAll('.sale-line').forEach(row => {
    const i = Number(row.dataset.line);
    const choice = row.querySelector('.sale-product').value;
    const qty = Number(row.querySelector('.sale-qty').value || 1);
    const priceInput = row.querySelector('.sale-price');
    saleLines[i].itemType = choice === 'custom' ? 'custom' : 'stock';
    saleLines[i].productId = choice === 'custom' ? '' : choice;
    saleLines[i].quantity = qty;
    saleLines[i].unitPrice = Number(priceInput.value || 0);
    saleLines[i].customName = row.querySelector('.custom-name')?.value || saleLines[i].customName || 'Custom Company Stamp';
  });
  if (shouldRender) render();
}
function audit(action, entityType, entityId, previousValue, newValue) {
  db.auditLogs.push({ id: uid(), actor: currentUser().displayName, action, entityType, entityId, previousValue, newValue, createdAt: new Date().toISOString() });
}
function moveStock(product, movementType, quantity, previousStock, newStock, reference, notes, saleId = null) {
  db.stockMovements.push({ id: uid(), productId: product.id, productName: product.name, movementType, quantity, previousStock, newStock, reference, notes, relatedSaleId: saleId, createdBy: currentUser().displayName, createdAt: new Date().toISOString() });
}
async function recordSale(event) {
  event.preventDefault();
  syncSaleLines(false);
  const form = new FormData(event.target);
  const items = saleLines.map(line => {
    const p = byId(line.productId);
    if (line.itemType === 'custom') return { itemType: 'custom', productId: null, productName: line.customName || 'Custom Company Stamp', quantity: Number(line.quantity), unitPrice: Number(line.unitPrice), costPrice: 0 };
    return p ? { itemType: 'stock', productId: p.id, productName: p.name, quantity: Number(line.quantity), unitPrice: Number(p.sellingPrice), costPrice: Number(p.costPrice) } : null;
  }).filter(Boolean);
  if (!items.length || items.some(i => i.quantity <= 0 || i.unitPrice < 0)) return setNotice('Add at least one valid sale item.', 'error');
  for (const item of items.filter(i => i.itemType === 'stock')) {
    const p = byId(item.productId);
    if (!p.active) return setNotice(`${p.name} is inactive and cannot be sold.`, 'error');
    if (p.currentStock < item.quantity) return setNotice(`Insufficient stock. Only ${p.currentStock} units are currently available for ${p.name}.`, 'error');
  }
  const saleId = uid();
  const createdAt = `${form.get('date') || todayText()}T${new Date().toTimeString().slice(0, 8)}.000Z`;
  const saleNumber = `SALE-${String(db.sequence++).padStart(5, '0')}`;
  const totalAmount = items.reduce((sum, i) => sum + i.quantity * i.unitPrice, 0);
  const grossProfit = items.reduce((sum, i) => sum + (i.unitPrice - i.costPrice) * i.quantity, 0);
  const sale = { id: saleId, saleNumber, customerName: form.get('customerName') || '', totalAmount, grossProfit, paymentMethod: form.get('paymentMethod'), status: 'COMPLETED', notes: form.get('notes') || '', createdBy: currentUser().displayName, createdAt };
  if (await commitRemote('sale', { saleNumber, customerName: sale.customerName, paymentMethod: sale.paymentMethod, notes: sale.notes, createdAt, items }, `${saleNumber} saved. Stock and sales totals updated.`)) return;
  db.sales.push(sale);
  items.forEach(item => {
    db.saleItems.push({ id: uid(), saleId, ...item, subtotal: item.quantity * item.unitPrice, grossProfit: (item.unitPrice - item.costPrice) * item.quantity });
    if (item.itemType === 'stock') {
      const p = byId(item.productId);
      const previous = p.currentStock;
      p.currentStock -= item.quantity;
      p.updatedAt = new Date().toISOString();
      moveStock(p, 'SALE', -item.quantity, previous, p.currentStock, saleNumber, 'Sale recorded', saleId);
    }
  });
  audit('CREATE_SALE', 'Sale', saleId, null, { saleNumber, totalAmount });
  save(); saleLines = [{ productId: '', itemType: 'stock', customName: '', quantity: 1, unitPrice: 0 }];
  setNotice(`${saleNumber} saved. Stock and sales totals updated.`);
}
async function addStock(event) {
  event.preventDefault(); if (!canManageStock()) return setNotice('Only administrators can add stock.', 'error');
  const form = new FormData(event.target); const p = byId(form.get('productId')); const quantity = Number(form.get('quantity'));
  if (!p || quantity <= 0) return setNotice('Select a product and enter a positive quantity.', 'error');
  if (await commitRemote('add-stock', { productId: p.id, quantity, costPrice: Number(form.get('costPrice')), supplier: form.get('supplier'), reference: `Purchase ${form.get('date')}`, notes: form.get('notes') || 'Stock received' }, `${quantity} units added to ${p.name}.`)) return;
  const previous = p.currentStock; p.currentStock += quantity; p.costPrice = Number(form.get('costPrice')); p.supplier = form.get('supplier'); p.updatedAt = new Date().toISOString();
  moveStock(p, 'STOCK PURCHASE', quantity, previous, p.currentStock, `Purchase ${form.get('date')}`, form.get('notes') || 'Stock received');
  audit('ADD_STOCK', 'Product', p.id, { currentStock: previous }, { currentStock: p.currentStock }); save(); setNotice(`${quantity} units added to ${p.name}.`);
}
async function adjustStock(event) {
  event.preventDefault(); if (!canManageStock()) return setNotice('Only administrators can adjust stock.', 'error');
  const form = new FormData(event.target); const p = byId(form.get('productId')); const actual = Number(form.get('actualQuantity'));
  if (!p || actual < 0 || !form.get('reason')) return setNotice('Provide a product, actual quantity and adjustment reason.', 'error');
  if (await commitRemote('adjust-stock', { productId: p.id, actualQuantity: actual, reason: form.get('reason') }, `Stock adjusted for ${p.name}.`)) return;
  const previous = p.currentStock; const delta = actual - previous; p.currentStock = actual; p.updatedAt = new Date().toISOString();
  moveStock(p, 'STOCK ADJUSTMENT', delta, previous, actual, 'Stock count', form.get('reason'));
  audit('ADJUST_STOCK', 'Product', p.id, { currentStock: previous }, { currentStock: actual, reason: form.get('reason') }); save(); setNotice(`Stock adjusted for ${p.name}.`);
}
async function processReturn(event) {
  event.preventDefault();
  const form = new FormData(event.target); const sale = db.sales.find(s => s.id === form.get('saleId')); const p = byId(form.get('productId')); const qty = Number(form.get('quantity'));
  const sold = db.saleItems.filter(i => i.saleId === sale?.id && i.productId === p?.id).reduce((sum, i) => sum + i.quantity, 0);
  const returned = db.returns.filter(r => r.saleId === sale?.id && r.productId === p?.id).reduce((sum, r) => sum + r.quantity, 0);
  if (!sale || !p || qty <= 0) return setNotice('Select a sale, product and valid returned quantity.', 'error');
  if (qty > sold - returned) return setNotice(`Return quantity exceeds remaining sold quantity. Available to return: ${sold - returned}.`, 'error');
  if (await commitRemote('return', { saleId: sale.id, productId: p.id, quantity: qty, reason: form.get('reason') }, `Return processed and ${p.name} stock increased.`)) return;
  const previous = p.currentStock; p.currentStock += qty; p.updatedAt = new Date().toISOString();
  const item = db.saleItems.find(i => i.saleId === sale.id && i.productId === p.id); const amount = qty * (item?.unitPrice || p.sellingPrice);
  db.returns.push({ id: uid(), saleId: sale.id, saleNumber: sale.saleNumber, productId: p.id, productName: p.name, quantity: qty, amount, reason: form.get('reason'), createdBy: currentUser().displayName, createdAt: new Date().toISOString() });
  sale.totalAmount -= amount; sale.grossProfit -= qty * ((item?.unitPrice || p.sellingPrice) - (item?.costPrice || p.costPrice)); sale.status = sale.totalAmount <= 0 ? 'RETURNED' : 'PARTIAL RETURN';
  moveStock(p, 'RETURN', qty, previous, p.currentStock, sale.saleNumber, form.get('reason'), sale.id);
  audit('PROCESS_RETURN', 'Sale', sale.id, { returned }, { product: p.name, quantity: qty, amount }); save(); setNotice(`Return processed and ${p.name} stock increased.`);
}
async function saveProduct(event) {
  event.preventDefault(); if (!isAdmin()) return setNotice('Only administrators can manage products.', 'error');
  const form = new FormData(event.target); const id = form.get('id'); const existing = byId(id); const data = Object.fromEntries(form.entries());
  const next = { id: id || uid(), name: data.name, category: data.category, description: data.description, type: data.type, color: data.color, sizeVolume: data.sizeVolume, supplier: data.supplier, costPrice: Number(data.costPrice), sellingPrice: Number(data.sellingPrice), currentStock: Number(data.currentStock), minimumStock: Number(data.minimumStock), active: data.active === 'true', trackStock: data.trackStock === 'true', createdAt: existing?.createdAt || new Date().toISOString(), updatedAt: new Date().toISOString() };
  if (await commitRemote('product', next, `${next.name} saved.`)) return;
  if (existing) Object.assign(existing, next); else { db.products.push(next); if (next.trackStock && next.currentStock > 0) moveStock(next, 'STOCK PURCHASE', next.currentStock, 0, next.currentStock, 'Opening stock', 'Initial stock at product creation'); }
  audit(existing ? 'UPDATE_PRODUCT' : 'CREATE_PRODUCT', 'Product', next.id, existing || null, next); save(); setNotice(`${next.name} saved.`);
}
async function toggleProduct(id) { const p = byId(id); if (!p || !isAdmin()) return; const previous = { active: p.active }; const payload = { ...p, active: !p.active }; if (await commitRemote('product', payload, `${p.name} is now ${payload.active ? 'active' : 'inactive'}.`)) return; p.active = !p.active; p.updatedAt = new Date().toISOString(); audit('SET_PRODUCT_STATUS', 'Product', p.id, previous, { active: p.active }); save(); setNotice(`${p.name} is now ${p.active ? 'active' : 'inactive'}.`); }
async function saveSupplier(event) { event.preventDefault(); if (!isAdmin()) return; const data = Object.fromEntries(new FormData(event.target).entries()); if (await commitRemote('supplier', data, `${data.name} saved.`)) return; db.suppliers.push({ id: uid(), ...data, active: true, createdAt: new Date().toISOString() }); audit('CREATE_SUPPLIER', 'Supplier', data.name, null, data); save(); setNotice(`${data.name} saved.`); }
async function saveUser(event) { event.preventDefault(); if (!isAdmin()) return; const data = Object.fromEntries(new FormData(event.target).entries()); if (await commitRemote('user', data, `${data.displayName} added.`)) return; db.users.push({ id: uid(), displayName: data.displayName, role: data.role, active: true, createdAt: new Date().toISOString() }); audit('CREATE_USER', 'User', data.displayName, null, data); save(); setNotice(`${data.displayName} added.`); }
function openModal(title, body) { document.body.insertAdjacentHTML('beforeend', `<div class="modal-backdrop"><div class="modal"><div class="split"><h3>${h(title)}</h3><button class="ghost close-modal">Close</button></div>${body}</div></div>`); document.querySelector('.close-modal').addEventListener('click', () => document.querySelector('.modal-backdrop').remove()); }
function openProductEditor(id) { const p = byId(id); openModal(`Edit ${p.name}`, productForm(p)); document.getElementById('productForm').addEventListener('submit', saveProduct); }
function openProductHistory(id) { const p = byId(id); const movements = db.stockMovements.filter(m => m.productId === id).sort((a,b) => b.createdAt.localeCompare(a.createdAt)); openModal(`${p.name} history`, movementTable(movements)); }
function openSale(id) { const s = db.sales.find(x => x.id === id); const items = db.saleItems.filter(i => i.saleId === id); openModal(`Sale ${s.saleNumber}`, `<p><strong>Customer:</strong> ${h(s.customerName || 'Walk-in')}<br><strong>Payment:</strong> ${h(s.paymentMethod)}<br><strong>Status:</strong> ${h(s.status)}</p><div class="table-wrap"><table><thead><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Subtotal</th><th>Gross profit</th></tr></thead><tbody>${items.map(i => `<tr><td>${h(i.productName)}</td><td>${i.quantity}</td><td>${money(i.unitPrice)}</td><td>${money(i.subtotal)}</td><td>${money(i.grossProfit)}</td></tr>`).join('')}</tbody></table></div><h3>Total: ${money(s.totalAmount)}</h3>`); }
function printSale(id) { openSale(id); setTimeout(() => window.print(), 100); }
function exportData() { const blob = new Blob([JSON.stringify(db, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `stamp-manager-backup-${todayText()}.json`; a.click(); URL.revokeObjectURL(url); }

function render() {
  const views = { dashboard, sales, inventory, products, suppliers, reports, settings };
  document.getElementById('app').innerHTML = appLayout(views[currentView]());
  bindCommon();
  bindView();
}

async function requestBackend(path, payload) {
  const options = payload ? { method: 'POST', headers: { 'content-type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify({ ...payload, actor: currentUser()?.displayName }) } : { credentials: 'same-origin' };
  const response = await fetch(`/functions/v1/app/${path}`, options);
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) throw new Error('The site service returned an invalid response.');
  const result = await response.json();
  if (!response.ok || !result.ok) {
    const error = new Error(result.error || 'request_failed');
    error.details = result;
    throw error;
  }
  return result.data;
}
async function hydrateRemote() {
  try {
    let remote = await requestBackend('state');
    if (!remote.products?.length) remote = await requestBackend('seed', {});
    db = { ...remote, mode: 'remote', sequence: remote.sequence || 1 };
    currentUserId = db.users[0]?.id || currentUserId;
    save();
    render();
  } catch {
    db.mode = 'local';
    save();
  }
}
async function commitRemote(path, payload, successMessage) {
  if (db.mode !== 'remote') return false;
  try {
    const remote = await requestBackend(path, payload);
    db = { ...remote, mode: 'remote', sequence: remote.sequence || db.sequence };
    currentUserId = db.users.find(u => u.displayName === currentUser()?.displayName)?.id || db.users[0]?.id || currentUserId;
    save();
    saleLines = [{ productId: '', itemType: 'stock', customName: '', quantity: 1, unitPrice: 0 }];
    setNotice(successMessage);
  } catch (error) {
    const details = error.details || {};
    const messages = {
      insufficient_stock: `Insufficient stock. Only ${details.available} units are currently available for ${details.product}.`,
      inactive_product: `${details.product || 'This product'} is inactive and cannot be sold.`,
      stock_changed_retry: 'Stock changed while saving. Refresh and try again.',
      return_exceeds_sale: `Return quantity exceeds remaining sold quantity. Available to return: ${details.available}.`,
      database_runtime_unavailable: 'The hosted database is not available yet. Try again after the backend finishes provisioning.'
    };
    setNotice(messages[error.message] || 'The request could not be saved. Please check the form and try again.', 'error');
  }
  return true;
}

render();
hydrateRemote();
