import {
  api
} from './api-client.js';
import './cart-drawer.js';
import './form-validation.js';
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
  requestAnimationFrame(() => requestAnimationFrame(() => sidebar.classList.add('is-ready')));
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


/* =========================================
   PRODUCT PAGE
   Variation price + image gallery
========================================= */

// Update displayed price when a variation is selected.
const priceLabel = document.querySelector("#product-price");

document.querySelectorAll('input[name="variation_id"]').forEach(option => {
  option.addEventListener("change", () => {
    if (priceLabel && option.checked) {
      priceLabel.textContent =
        `₱${Number(option.dataset.price).toFixed(2)}`;
    }
  });
});

// Product image gallery.
const productGallery = document.querySelector(".product-gallery");
const mainPhoto = document.querySelector("#product-main-photo");

if (productGallery && mainPhoto) {
  const thumbnails = [
    ...productGallery.querySelectorAll("[data-gallery-thumb]")
  ];

  const dots = [
    ...productGallery.querySelectorAll("[data-gallery-dot]")
  ];

  const previousButton = productGallery.querySelector("[data-gallery-prev]");
  const nextButton = productGallery.querySelector("[data-gallery-next]");

  let activePhoto = 0;

  function showPhoto(index) {
    if (!thumbnails.length) return;

    // Wrap around when moving past either end of the gallery.
    activePhoto = (index + thumbnails.length) % thumbnails.length;

    const activeThumbnail = thumbnails[activePhoto];
    const image = activeThumbnail.querySelector("img");

    if (!image) return;

    mainPhoto.src = image.src;
    mainPhoto.alt = mainPhoto.alt || "Product photo";

    // Update thumbnail selection.
    thumbnails.forEach((thumbnail, i) => {
      const active = i === activePhoto;

      thumbnail.classList.toggle("is-active", active);
      thumbnail.setAttribute("aria-pressed", String(active));
    });

    // Update pagination dots.
    dots.forEach((dot, i) => {
      const active = i === activePhoto;

      dot.classList.toggle("is-active", active);
      dot.setAttribute("aria-pressed", String(active));
    });
  }

  // Thumbnail navigation.
  thumbnails.forEach((thumbnail, index) => {
    thumbnail.addEventListener("click", () => {
      showPhoto(index);
    });
  });

  // Previous and next buttons.
  previousButton?.addEventListener("click", () => {
    showPhoto(activePhoto - 1);
  });

  nextButton?.addEventListener("click", () => {
    showPhoto(activePhoto + 1);
  });

  // Dot navigation.
  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => {
      showPhoto(index);
    });
  });

  // Keyboard navigation while the gallery is focused.
  productGallery.addEventListener("keydown", event => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      showPhoto(activePhoto - 1);
    }

    if (event.key === "ArrowRight") {
      event.preventDefault();
      showPhoto(activePhoto + 1);
    }
  });
}
