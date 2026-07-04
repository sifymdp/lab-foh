import html
import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Table, TableQRCode
from app.services import menu_service
from app.services.floor_service import get_current_floor

router = APIRouter(prefix="/guest", tags=["guest"])

RESTAURANT_NAME = "FOH Restaurant"
CATEGORY_ORDER = ["Starters", "Mains", "Drinks", "Desserts"]


def _resolve_qr(db: Session, token: str) -> TableQRCode:
    qr = (
        db.query(TableQRCode)
        .filter(TableQRCode.token == token, TableQRCode.is_active.is_(True))
        .first()
    )
    if not qr:
        raise HTTPException(404, "Invalid or expired table token")
    return qr


def _build_guest_menu_html(
    *,
    token: str,
    table: Table,
    restaurant_name: str,
    items_by_category: dict[str, list],
) -> str:
    menu_json = json.dumps(
        {
            "token": token,
            "tableId": table.id,
            "tableNumber": table.number,
            "apiBase": settings.guest_menu_base_url.rstrip("/"),
        }
    )

    sections_html = []
    ordered_cats = [c for c in CATEGORY_ORDER if c in items_by_category]
    ordered_cats += sorted(k for k in items_by_category if k not in CATEGORY_ORDER)

    for category in ordered_cats:
        items_html = []
        for item in items_by_category[category]:
            desc = html.escape(item.description or "")
            items_html.append(
                f"""
                <article class="menu-item" data-id="{html.escape(item.id)}"
                         data-name="{html.escape(item.name)}"
                         data-price="{float(item.price):.2f}">
                  <div class="menu-item__info">
                    <h3>{html.escape(item.name)}</h3>
                    {f'<p class="desc">{desc}</p>' if desc else ''}
                    <p class="price">£{float(item.price):.2f}</p>
                  </div>
                  <button type="button" class="btn-add" onclick="addItem('{html.escape(item.id)}')">
                    Add to Order
                  </button>
                </article>
                """
            )
        sections_html.append(
            f'<section class="category"><h2>{html.escape(category)}</h2>{"".join(items_html)}</section>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(restaurant_name)} — Table {html.escape(table.number)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: system-ui, -apple-system, sans-serif;
      background: #f8fafc; color: #0f172a; padding-bottom: 140px;
    }}
    header {{
      background: #1e293b; color: #fff; padding: 20px 16px;
      text-align: center; position: sticky; top: 0; z-index: 10;
    }}
    header h1 {{ margin: 0; font-size: 1.35rem; }}
    header p {{ margin: 6px 0 0; opacity: 0.85; font-size: 0.9rem; }}
    main {{ padding: 16px; max-width: 640px; margin: 0 auto; }}
    .category {{ margin-bottom: 28px; }}
    .category h2 {{
      font-size: 1.1rem; margin: 0 0 12px; color: #475569;
      border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;
    }}
    .menu-item {{
      display: flex; gap: 12px; align-items: flex-start;
      background: #fff; border-radius: 12px; padding: 14px;
      margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .menu-item__info {{ flex: 1; min-width: 0; }}
    .menu-item h3 {{ margin: 0 0 4px; font-size: 1rem; }}
    .desc {{ margin: 0 0 6px; font-size: 0.85rem; color: #64748b; }}
    .price {{ margin: 0; font-weight: 700; color: #0f766e; }}
    .btn-add {{
      flex-shrink: 0; border: none; background: #0f766e; color: #fff;
      padding: 10px 12px; border-radius: 8px; font-size: 0.85rem;
      cursor: pointer; white-space: nowrap;
    }}
    .btn-add:active {{ transform: scale(0.97); }}
    .cart {{
      position: fixed; bottom: 0; left: 0; right: 0;
      background: #fff; border-top: 1px solid #e2e8f0;
      padding: 12px 16px 20px; box-shadow: 0 -4px 20px rgba(0,0,0,0.08);
    }}
    .cart-inner {{ max-width: 640px; margin: 0 auto; }}
    .cart h3 {{ margin: 0 0 8px; font-size: 0.95rem; }}
    .cart-lines {{ max-height: 80px; overflow-y: auto; font-size: 0.85rem; color: #475569; }}
    .cart-lines.empty {{ color: #94a3b8; font-style: italic; }}
    .cart-footer {{
      display: flex; align-items: center; justify-content: space-between;
      margin-top: 10px; gap: 12px;
    }}
    .cart-total {{ font-weight: 700; font-size: 1.05rem; }}
    .btn-order {{
      border: none; background: #1e293b; color: #fff;
      padding: 12px 20px; border-radius: 10px; font-size: 1rem;
      font-weight: 600; cursor: pointer; flex-shrink: 0;
    }}
    .btn-order:disabled {{ opacity: 0.45; cursor: not-allowed; }}
    .toast {{
      position: fixed; top: 72px; left: 50%; transform: translateX(-50%);
      background: #166534; color: #fff; padding: 10px 16px; border-radius: 8px;
      font-size: 0.9rem; display: none; z-index: 20;
    }}
    .toast.error {{ background: #b91c1c; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(restaurant_name)}</h1>
    <p>Table {html.escape(table.number)} · Browse &amp; order</p>
  </header>
  <main>
    {"".join(sections_html) if sections_html else '<p>No menu items available right now.</p>'}
  </main>
  <div id="toast" class="toast"></div>
  <div class="cart">
    <div class="cart-inner">
      <h3>Your order</h3>
      <div id="cart-lines" class="cart-lines empty">Nothing added yet</div>
      <div class="cart-footer">
        <span class="cart-total" id="cart-total">£0.00</span>
        <button type="button" id="place-order" class="btn-order" disabled onclick="placeOrder()">
          Place Order
        </button>
      </div>
    </div>
  </div>
  <script>
    const CONFIG = {menu_json};
    const cart = {{}};

    function showToast(msg, isError) {{
      const el = document.getElementById('toast');
      el.textContent = msg;
      el.className = 'toast' + (isError ? ' error' : '');
      el.style.display = 'block';
      setTimeout(() => {{ el.style.display = 'none'; }}, 3500);
    }}

    function addItem(id) {{
      const row = document.querySelector('.menu-item[data-id="' + id + '"]');
      if (!row) return;
      const name = row.dataset.name;
      const price = parseFloat(row.dataset.price);
      if (!cart[id]) cart[id] = {{ id, name, price, qty: 0 }};
      cart[id].qty += 1;
      renderCart();
      showToast(name + ' added');
    }}

    function renderCart() {{
      const lines = document.getElementById('cart-lines');
      const totalEl = document.getElementById('cart-total');
      const btn = document.getElementById('place-order');
      const entries = Object.values(cart).filter(i => i.qty > 0);
      if (!entries.length) {{
        lines.className = 'cart-lines empty';
        lines.textContent = 'Nothing added yet';
        totalEl.textContent = '£0.00';
        btn.disabled = true;
        return;
      }}
      lines.className = 'cart-lines';
      let total = 0;
      lines.innerHTML = entries.map(i => {{
        total += i.price * i.qty;
        return i.qty + '× ' + i.name + ' — £' + (i.price * i.qty).toFixed(2);
      }}).join('<br>');
      totalEl.textContent = '£' + total.toFixed(2);
      btn.disabled = false;
    }}

    async function placeOrder() {{
      const entries = Object.values(cart).filter(i => i.qty > 0);
      if (!entries.length) return;
      const btn = document.getElementById('place-order');
      btn.disabled = true;
      btn.textContent = 'Sending…';
      try {{
        const res = await fetch(
          CONFIG.apiBase + '/orders?token=' + encodeURIComponent(CONFIG.token),
          {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
              tableId: CONFIG.tableId,
              items: entries.map(i => ({{ menuItemId: i.id, quantity: i.qty }})),
            }}),
          }}
        );
        if (!res.ok) {{
          const err = await res.json().catch(() => ({{}}));
          throw new Error(err.detail || res.statusText);
        }}
        Object.keys(cart).forEach(k => delete cart[k]);
        renderCart();
        showToast('Order placed — thank you!');
      }} catch (e) {{
        showToast(e.message || 'Could not place order', true);
      }} finally {{
        btn.textContent = 'Place Order';
        btn.disabled = Object.values(cart).filter(i => i.qty > 0).length === 0;
      }}
    }}
  </script>
</body>
</html>"""


@router.get("/menu")
def guest_menu(
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    qr = _resolve_qr(db, token)
    table = db.get(Table, qr.table_id)
    if not table:
        raise HTTPException(404, "Table not found")

    try:
        floor = get_current_floor(db)
        restaurant_name = floor.name or RESTAURANT_NAME
    except Exception:
        restaurant_name = RESTAURANT_NAME

    items = menu_service.list_available_models(db)
    by_category: dict[str, list] = defaultdict(list)
    for item in items:
        by_category[item.category].append(item)

    page = _build_guest_menu_html(
        token=token,
        table=table,
        restaurant_name=restaurant_name,
        items_by_category=dict(by_category),
    )
    return HTMLResponse(page)
