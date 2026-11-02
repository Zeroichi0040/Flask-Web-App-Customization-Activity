import {
  api
} from './api-client.js';
document.documentElement.classList.add('js');

const menu = document.querySelector('.menu-toggle');
const sidebar = document.querySelector('#sidebar');
if (menu && sidebar) {
  const smallScreen = window.matchMedia('(max-width:800px)');
  const setMenu = (open, restoreFocus = false) => {
    const expanded = smallScreen.matches && open;
    menu.setAttribute('aria-expanded', String(expanded));
    sidebar.classList.toggle('is-open', expanded);
    sidebar.inert = smallScreen.matches && !expanded;
    if (sidebar.inert) sidebar.setAttribute('aria-hidden', 'true');
    else sidebar.removeAttribute('aria-hidden');
    if (expanded) sidebar.querySelector('button, a')?.focus();
    else if (restoreFocus) menu.focus();
  };
  setMenu(false);
  menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
  sidebar.querySelector('.sidebar-close')?.addEventListener('click', () => setMenu(false, true));
  smallScreen.addEventListener('change', () => setMenu(false));
  document.addEventListener('click', event => {
    if (!sidebar.contains(event.target) && !menu.contains(event.target)) setMenu(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') setMenu(false, true);
  });
}

document.addEventListener('submit', event => {
  if (event.target.dataset.confirm && !window.confirm(event.target.dataset.confirm)) event.preventDefault();
});

/* Read current rows through the same resource's JSON endpoint. No HTML injection. */
for (const panel of document.querySelectorAll('[data-resource-list]')) {
  const refresh = panel.querySelector('[data-refresh]');
  refresh?.addEventListener('click', async () => {
    const status = panel.querySelector('[data-refresh-status]');
    refresh.disabled = true;
    status.textContent = 'Loading current records…';
    try {
      const result = await api(panel.dataset.apiUrl);
      const columns = [...panel.querySelectorAll('th[data-field]')].map(th => th.dataset.field);
      const rows = [];
      for (const record of result.data) {
        const row = document.createElement('tr');
        columns.forEach((name, index) => {
          const cell = document.createElement('td');
          const value = record[name] === true ? 'Yes' : record[name] === false ? 'No' : record[name] ?? '—';
          const text = String(value).slice(0, 100);
          if (index === 0) {
            const link = document.createElement('a');
            link.className = 'record-link';
            link.href = `${panel.dataset.recordBase}/${record.id}`;
            link.textContent = text;
            cell.append(link);
          } else cell.textContent = text;
          row.append(cell);
        });
        const updated = document.createElement('td');
        updated.textContent = new Date(record.updated_at).toLocaleDateString();
        const actions = document.createElement('td');
        const edit = document.createElement('a');
        edit.href = `${panel.dataset.recordBase}/${record.id}/edit`;
        edit.textContent = 'Edit';
        actions.append(edit);
        row.append(updated, actions);
        rows.push(row);
      }
      if (!rows.length) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = columns.length + 2;
        cell.textContent = 'No matching records. Add one or change your search.';
        row.append(cell);
        rows.push(row);
      }
      panel.querySelector('tbody').replaceChildren(...rows);
      panel.querySelector('[data-record-count]').textContent = `${result.pagination.total} records`;
      status.textContent = 'Updated from the server.';
    } catch (error) {
      status.textContent = error.message;
    } finally {
      refresh.disabled = false;
    }
  });
}

/* Profile menu: hover on mouse devices; tap, Enter or Space elsewhere; Escape or outside click closes. */
const profileMenu = document.querySelector('.profile-menu');
if (profileMenu) {
  const trigger = profileMenu.querySelector('.profile-trigger');
  const hoverDevice = window.matchMedia('(hover: hover)');
  const setProfile = open => {
    profileMenu.classList.toggle('is-open', open);
    trigger.setAttribute('aria-expanded', String(open));
  };
  trigger.addEventListener('click', event => {
    // A real mouse click already opened it on hover; keyboard clicks have detail 0.
    if (hoverDevice.matches && event.detail > 0) setProfile(true);
    else setProfile(!profileMenu.classList.contains('is-open'));
  });
  profileMenu.addEventListener('mouseenter', () => { if (hoverDevice.matches) setProfile(true); });
  profileMenu.addEventListener('mouseleave', () => { if (hoverDevice.matches) setProfile(false); });
  profileMenu.addEventListener('focusout', event => {
    if (!profileMenu.contains(event.relatedTarget)) setProfile(false);
  });
  document.addEventListener('click', event => {
    if (!profileMenu.contains(event.target)) setProfile(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && profileMenu.classList.contains('is-open')) {
      setProfile(false);
      trigger.focus();
    }
  });
}


document.addEventListener("DOMContentLoaded", () => {
  const drawer = document.getElementById("cart-drawer");
  const panel = drawer?.querySelector(".cart-drawer__panel");
  const content = document.getElementById("cart-drawer-content");

  if (!drawer || !panel || !content) return;

  let previousFocus = null;
  let isLoading = false;

  // Get the existing cart page URL from the basket icon.
  function getCartUrl() {
    return document.querySelector(".cart-icon")?.href;
  }

  // Fetch the existing cart page and extract its contents.
  async function loadCart() {
    if (isLoading) return;

    const cartUrl = getCartUrl();
    if (!cartUrl) return;

    isLoading = true;
    content.innerHTML = "<p>Loading your basket...</p>";

    try {
      const response = await fetch(cartUrl, {
        method: "GET",
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        }
      });

      if (!response.ok) {
        throw new Error("Could not load cart.");
      }

      const html = await response.text();
      const documentFromResponse =
        new DOMParser().parseFromString(html, "text/html");

      const cartContent =
        documentFromResponse.querySelector("#cart-page-content");

      if (!cartContent) {
        throw new Error("Cart content was not found.");
      }

      content.innerHTML = cartContent.innerHTML;

      // Keep the basket counter synchronized if it exists.
      const newCount =
        documentFromResponse.querySelector(".basket-number");

      const currentCount =
        document.querySelector(".basket-number");

      if (newCount && currentCount) {
        currentCount.textContent = newCount.textContent;
      }

    } catch (error) {
      console.error("Cart drawer error:", error);

      content.innerHTML = `
        <p>Unable to load your basket.</p>
        <a class="button primary" href="${cartUrl}">
          View cart
        </a>
      `;

    } finally {
      isLoading = false;
    }
  }

  // Open drawer.
  async function openCart() {
    previousFocus = document.activeElement;

    drawer.hidden = false;
    document.body.classList.add("cart-drawer-open");

    await loadCart();

    panel.querySelector(".cart-drawer__close")?.focus();
  }

  // Close drawer.
  function closeCart() {
    drawer.hidden = true;
    document.body.classList.remove("cart-drawer-open");

    previousFocus?.focus();
  }

  // Intercept basket icon clicks.
  document.addEventListener("click", (event) => {
    const cartLink = event.target.closest(".cart-icon");

    if (cartLink) {
      // Preserve normal browser behavior for modified clicks.
      if (
        event.button !== 0 ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      event.preventDefault();
      openCart();
      return;
    }

    // Close button or backdrop.
    if (event.target.closest("[data-cart-close]")) {
      closeCart();
    }
  });

  // Handle Escape key.
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !drawer.hidden) {
      closeCart();
    }
  });

  // Handle quantity updates and item removals without leaving the drawer.
  drawer.addEventListener("submit", async (event) => {
    const form = event.target.closest("#cart-drawer-content form");

    if (!form) return;

    event.preventDefault();

    const submitButton = form.querySelector('[type="submit"]');

    if (submitButton) {
      submitButton.disabled = true;
    }

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        }
      });

      if (!response.ok) {
        throw new Error("Cart update failed.");
      }

      // Reload the cart so the quantities and total are current.
      await loadCart();

    } catch (error) {
      console.error("Cart update error:", error);

      // Fall back to the normal server-rendered cart page.
      window.location.href = getCartUrl();

    }
  });
});

/* Home page: keep the header fixed at the top at all times. */

document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector(".topbar");

  if (!header || !document.querySelector(".home")) return;

  // Reserve the header's original space in the document.
  const spacer = document.createElement("div");
  spacer.className = "topbar-fixed-spacer";

  header.before(spacer);

  function updateHeaderSpace() {
    spacer.style.height = `${header.offsetHeight}px`;
  }

  header.classList.add("is-fixed");
  updateHeaderSpace();

  window.addEventListener("resize", updateHeaderSpace);
});

