/* Basket drawer + in-place cart updates.
   Progressive enhancement: every link and form still works without JavaScript
   (the cart icon links to the cart page, quantity and remove are normal POST forms). */

const drawer = document.querySelector('#cart-drawer');
const drawerContent = document.querySelector('#cart-drawer-content');
const drawerCount = document.querySelector('#cart-drawer-count');
const live = document.querySelector('#cart-live');
const CART_SELECTOR = '#cart-page-content';
const SAVE_DELAY = 450;

let opener = null;
let saveTimers = new WeakMap();

const itemWord = n => (n === 1 ? 'item' : 'items');
const announce = text => { if (live) live.textContent = text; };

/* ---------- header badge + drawer title ---------- */
function setCount(count) {
  const link = document.querySelector('.cart-icon');
  if (link) {
    let badge = link.querySelector('.basket-number');
    if (count > 0) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'basket-number';
        badge.setAttribute('aria-hidden', 'true');
        link.append(badge);
      }
      badge.textContent = count;
    } else badge?.remove();
    const label = count > 0 ? `Cart, ${count} ${itemWord(count)}` : 'Cart';
    link.setAttribute('aria-label', label);
  }
  if (drawerCount) drawerCount.textContent = count > 0 ? `(${count} ${itemWord(count)})` : '';
}

/* ---------- fetching and swapping the cart markup ---------- */
async function parseCart(response) {
  const html = await response.text();
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.querySelector(CART_SELECTOR);
}

function showCart(root, fresh) {
  const wasInDrawer = drawer?.contains(root);
  const focusKey = rememberFocus(root);
  const next = fresh.cloneNode(true);
  if (wasInDrawer) {
    drawerContent.replaceChildren(next);
  } else {
    root.replaceWith(next);
  }
  setCount(Number(next.dataset.cartCount || 0));
  restoreFocus(next, focusKey);
  return next;
}

function rememberFocus(root) {
  const el = document.activeElement;
  if (!el || !root.contains(el)) return null;
  const line = el.closest('.cart-line');
  const part = ['qty-input', 'qty-btn', 'cart-remove', 'cart-line-name']
    .find(name => el.classList.contains(name));
  return {
    item: line?.dataset.item ?? null,
    part,
    step: el.dataset?.qtyStep ?? null,
    index: line ? [...line.parentElement.children].indexOf(line) : -1
  };
}

function restoreFocus(root, key) {
  if (!key) return;
  const lines = [...root.querySelectorAll('.cart-line')];
  let line = lines.find(l => l.dataset.item === key.item);
  let target = null;
  if (line) {
    const selector = key.part === 'qty-btn'
      ? `.qty-btn[data-qty-step="${key.step}"]:not(:disabled)`
      : `.${key.part}`;
    target = line.querySelector(selector) || line.querySelector('.qty-input');
  } else {
    // The line was removed: move to the neighbour that took its place.
    line = lines[Math.min(key.index, lines.length - 1)];
    target = line?.querySelector('.cart-line-name')
      || root.querySelector('.cart-checkout');
  }
  (target || drawer?.querySelector('.cart-drawer__panel'))?.focus({ preventScroll: true });
}

async function loadDrawer() {
  drawerContent.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(opener?.href || '/cart', { credentials: 'same-origin' });
    const fresh = response.ok ? await parseCart(response) : null;
    if (!fresh) throw new Error('No cart in response');
    showCart(drawerContent, fresh);
  } catch {
    // Anything unexpected (signed out, offline): fall back to the normal cart page.
    if (opener?.href) window.location.assign(opener.href);
  } finally {
    drawerContent.removeAttribute('aria-busy');
  }
}

/* ---------- open / close ---------- */
const focusable = () => [...drawer.querySelectorAll(
  'a[href], button:not(:disabled), input:not(:disabled), [tabindex]:not([tabindex="-1"])'
)].filter(el => el.offsetParent !== null);

function openDrawer(trigger) {
  opener = trigger;
  drawer.hidden = false;
  document.body.classList.add('cart-drawer-open');
  trigger.setAttribute('aria-expanded', 'true');
  drawer.querySelector('.cart-drawer__panel').focus();
  loadDrawer();
}

function closeDrawer() {
  if (drawer.hidden) return;
  drawer.hidden = true;
  document.body.classList.remove('cart-drawer-open');
  opener?.removeAttribute('aria-expanded');
  opener?.focus();
}

if (drawer && drawerContent) {
  document.addEventListener('click', event => {
    const trigger = event.target.closest('[data-cart-open]');
    // On the cart page itself the link just goes there; modified clicks behave like normal links.
    const onCartPage = document.querySelector(`main ${CART_SELECTOR}`);
    if (trigger && !onCartPage && !(event.metaKey || event.ctrlKey || event.shiftKey || event.button)) {
      event.preventDefault();
      openDrawer(trigger);
      return;
    }
    if (event.target.closest('[data-cart-close]')) closeDrawer();
    // Following a link inside the drawer should not leave it stuck open.
    const link = event.target.closest('a[href]');
    if (link && drawer.contains(link) && !event.defaultPrevented) closeDrawer();
  });

  document.addEventListener('keydown', event => {
    if (drawer.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeDrawer();
    } else if (event.key === 'Tab') {
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === drawer.querySelector('.cart-drawer__panel'))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
}

/* ---------- quantity steppers ---------- */
function syncStepper(form) {
  const input = form.querySelector('.qty-input');
  const value = Number(input.value) || 1;
  const min = Number(input.min || 1);
  const max = Number(input.max || 99);
  form.querySelector('[data-qty-step="-1"]').disabled = value <= min;
  form.querySelector('[data-qty-step="1"]').disabled = value >= max;
}

function clampQuantity(input) {
  const min = Number(input.min || 1);
  const max = Number(input.max || 99);
  const value = Math.round(Number(input.value));
  input.value = Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : min;
}

function scheduleSave(form) {
  clearTimeout(saveTimers.get(form));
  saveTimers.set(form, setTimeout(() => saveForm(form), SAVE_DELAY));
}

document.addEventListener('click', event => {
  const button = event.target.closest('[data-qty-step]');
  if (!button || button.disabled) return;
  const form = button.closest('.cart-quantity');
  const input = form.querySelector('.qty-input');
  input.value = Number(input.value || 1) + Number(button.dataset.qtyStep);
  clampQuantity(input);
  syncStepper(form);
  scheduleSave(form);
});

document.addEventListener('change', event => {
  const input = event.target.closest?.('.qty-input');
  if (!input) return;
  const form = input.closest('.cart-quantity');
  clampQuantity(input);
  syncStepper(form);
  scheduleSave(form);
});

/* ---------- saving (quantity + remove) without a page reload ---------- */
async function saveForm(form) {
  const root = form.closest(CART_SELECTOR) || (drawer?.contains(form) ? drawerContent : null);
  if (!root) { form.submit(); return; }
  const container = drawer?.contains(form) ? drawerContent : root;
  const removing = form.classList.contains('cart-remove-form');
  const name = form.closest('.cart-line')?.querySelector('.cart-line-name')?.textContent.trim();
  container.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'fetch' }
    });
    const fresh = response.ok ? await parseCart(response) : null;
    if (!fresh) throw new Error('No cart in response');
    showCart(root, fresh);
    announce(removing ? `${name} removed from your basket.` : `Quantity updated${name ? ` for ${name}` : ''}.`);
  } catch {
    form.submit(); // Fall back to the normal full-page flow (handles errors and sign-out).
  } finally {
    container.removeAttribute('aria-busy');
  }
}

document.addEventListener('submit', event => {
  const form = event.target;
  if (!form.matches?.('.cart-quantity, .cart-remove-form')) return;
  event.preventDefault();
  if (form.classList.contains('cart-quantity')) {
    clampQuantity(form.querySelector('.qty-input'));
    clearTimeout(saveTimers.get(form));
  }
  saveForm(form);
});

setCount(Number(document.querySelector(CART_SELECTOR)?.dataset.cartCount
  ?? document.querySelector('.basket-number')?.textContent ?? 0));
