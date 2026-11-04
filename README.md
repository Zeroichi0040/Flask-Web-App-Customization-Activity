# Pastrydale

> *Every bite is a fairytale.*

Pastrydale is a bakery storefront prototype. Customers browse treats that are stored in the database, pick an option such as "Box of 6", add items to a cart, and place a delivery order. Bakery staff manage the products, orders, customer messages, accounts and website pages from an admin area.

It is a **CS111 Startup Simulation** project. It is an educational prototype: **no payment is collected, no real orders are fulfilled, and all business figures are hypothetical.**

*Last updated: 2026-11-04. This document describes the code in the project archive `Flask-Web-App-Customization-Activity`.*

---

## Features

### For customers

| Feature | What it does |
| --- | --- |
| Home page | Hero banner, the five newest products from the database, a story section, and any published website pages |
| Product catalog | Public product list and product pages with a photo gallery, subheading, description and up to four priced options |
| Accounts | Register, sign in, sign out, change name and password, "forgot password" reset link |
| Cart | Add products with a chosen option, change quantities (1 to 99), remove items, slide-out cart drawer |
| Checkout | Delivery details form with in-browser validation, then a saved order |
| My Orders | List of the customer's own orders and an order page with a progress tracker (Placed, Preparing, Out for delivery, Completed) |
| Contact page | Message form saved for the admins, with spam protection |
| Mobile friendly | Layouts, hamburger menu and cart drawer adapt to phones and tablets |

### For administrators

| Feature | What it does |
| --- | --- |
| Manage products | Create, edit, delete and search products; cover photo, up to 5 extra photos, up to 4 priced options; CSV export |
| Orders | View every order with customer details and items, and update its status |
| Messages | Read contact-form messages and mark them resolved |
| Accounts | Change a person's role (member or administrator) or deactivate the account |
| Website pages | Write pages and publish or unpublish them at a public URL |
| Audit log | Record of important admin actions, such as order status changes |

### Platform (inherited from the starter framework)

CSRF protection, scrypt password hashing, rate limiting, security headers, database migrations, optimistic version locking, health-check endpoints, a JSON API with OpenAPI docs, and SQLite or PostgreSQL support. See [System documentation](docs/SYSTEM_DOCUMENTATION.md) for details.

---

## Technology

| Area | Tools |
| --- | --- |
| Language | Python 3.11 to 3.14 (3.12 or 3.13 recommended) |
| Web framework | Flask 3.1 with Blueprints |
| Database | SQLite by default; PostgreSQL optional. SQLAlchemy 2.1 and Alembic migrations (Flask-SQLAlchemy, Flask-Migrate) |
| Accounts and forms | Flask-Login, Flask-WTF and WTForms, email-validator, Flask-Limiter |
| Images | Pillow (validation, metadata removal) |
| Frontend | Jinja2 templates, plain CSS, plain JavaScript modules. **No Node.js or build step.** |
| Fonts | Lexend and East Botany, served from the project |
| Server | Waitress (local), Gunicorn (Linux hosting) |
| Testing and quality | pytest, Ruff, pip-audit |
| Delivery | GitHub Actions CI, Dockerfile and Docker Compose, Render and PythonAnywhere files |

Exact versions are pinned in `requirements.txt`.

---

## Setup and run

You need **Python 3.11 to 3.14** and an internet connection for the first setup. Extract or clone the project first.

### Windows

```powershell
.\SETUP_WINDOWS.bat      # first time only: creates .venv, installs packages, creates .env, builds the database
.\START_WEBSITE.bat      # starts the website
```

If Windows says Python is missing, run `py install 3.13` and try again, or run `py -3.13 scripts\bootstrap.py`.

### macOS / Linux

```sh
bash setup.sh     # first time only
bash start.sh
```

Open **http://127.0.0.1:5000**. Keep the terminal open; press **Ctrl+C** to stop.

### What setup does

1. Creates a private virtual environment in `.venv`
2. Installs the packages in `requirements.txt`
3. Creates `.env` with a unique random `SECRET_KEY` (see [Configuration](#configuration))
4. Applies every database migration (`python manage.py db upgrade`), which creates `database/data/application.sqlite3`
5. Checks that the application is ready

Running setup again keeps your existing `.env` and data.

---

## First-time use (important for demos)

A fresh install has **no accounts and no products**. Do this once:

1. **Create an administrator.** In a terminal inside the project folder:
   - Windows: `.venv\Scripts\python.exe manage.py create-admin`
   - macOS / Linux: `.venv/bin/python manage.py create-admin`

   It asks for your email, a display name and a password of 12 to 128 characters. No default account exists.
2. **Sign in** at `/auth/login` and open **Manage products** (`/app/products`).
3. **Add products.** Give each a name, price and photo. Optionally add a subheading, up to four options (for example "Box of 5", "Box of 10") and extra photos.
4. **Create a customer account** (a second browser or a private window) at `/auth/register`.

## Demo walkthrough

A suggested path for Demo Day (about 5 minutes):

1. Home page: show the newest products, then resize the browser to show the mobile layout.
2. Open a product, choose an option, and press **Add to basket** (as a signed-in customer).
3. Open the cart drawer, change a quantity, then press **Checkout**.
4. On the checkout form, submit it empty to show validation messages, then fill it in and press **Place order**.
5. Open **My Orders** to show the new order and its progress tracker.
6. In the admin window, open **Orders** and change the status to **Preparing**.
7. Back as the customer, refresh the order page: the tracker moves forward.
8. Show **Messages** (send one from the Contact page first) and **Audit log**.

---

## Configuration

Settings live in `.env` (created by setup, never committed). `.env.example` shows every option.

| Setting | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | `development`, `testing` or `production` |
| `APP_NAME`, `APP_TAGLINE` | Pastrydale, Every bite is a fairytale | Shown in the site |
| `SECRET_KEY` | generated | Signs sessions. Production needs 32 or more characters |
| `DATABASE_URL` | empty | Empty means SQLite at `database/data/application.sqlite3`. Use `postgresql+psycopg://...` for PostgreSQL |
| `SIGNUP_ENABLED` | `true` | Set `false` to close registration |
| `MAIL_TRANSPORT` | `outbox` | `outbox` writes reset emails to `instance/outbox`, `smtp` sends real email, `disabled` sends none |

**Never upload `.env`, `.venv`, `database/data/*.sqlite3`, `instance/` or `database/backups/` to GitHub or share them.** `.gitignore` already excludes them.

## Database

- **Engine:** SQLite file by default, PostgreSQL if `DATABASE_URL` is set.
- **Schema:** defined by SQLAlchemy models in `database/models/` and built by the migrations in `database/migrations/versions/`. No separate SQL file is needed.
- **Create or update the database:** `python manage.py db upgrade` (setup runs this for you).
- **Reset to empty:** stop the site, delete `database/data/application.sqlite3`, run `python manage.py db upgrade`, then create the administrator again.
- **Back up (SQLite):** `python manage.py backup-db`
- **PostgreSQL for local testing:** `docker compose up` starts PostgreSQL and the app (see `compose.yaml`).

Tables: `users`, `products`, `product_variations`, `product_images`, `cart_items`, `orders`, `order_items`, `inquiries`, `pages`, `notes`, `attachments`, `audit_events`, `site_state`. The diagram is in [System documentation](docs/SYSTEM_DOCUMENTATION.md#5-data-model).

## Project structure

```
frontend/            Jinja2 pages, CSS, JavaScript, images, fonts
  templates/         shop/, auth/, admin/, account/, public/, components/, framework/
  static/css/        tokens.css, app.css, forms.css, customer-orders.css, admin.css
  static/js/         app.js, cart-drawer.js, form-validation.js, api-client.js
backend/
  modules/           shop, public, auth, account, admin, dashboard, files, api, health, products, pages, notes
  framework/         generic resource engine (forms, CRUD routes, policies, OpenAPI)
  common/            shared forms, errors, security helpers
database/
  models/            SQLAlchemy models
  migrations/        Alembic migration history
scripts/             setup, production start-up, resource generator
tests/               automated tests (pytest)
docs/                documentation
```

## Testing

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

The repository has 76 automated test functions covering accounts, the shop, checkout, orders, product options and photos, admin rules and the framework. Tests use temporary databases and never touch your data. The manual test cases and a results table for the team are in [docs/TEST_PLAN.md](docs/TEST_PLAN.md). **Record real results there; do not copy results from other documents.**

## Known limitations

This is a prototype. Be upfront about these during the demo:

- **No payment, delivery fee, tax or stock tracking.** Checkout saves the order and clears the cart.
- **No order confirmation email.** Email is only used for password reset links. After checkout the customer sees a message on the products page.
- **Customers cannot cancel an order.** Only administrators change statuses, and any status can be set at any time.
- **Phone format is checked only in the browser.** The server accepts any phone text up to 30 characters (the field is optional).
- **Shop browsing has no search or categories.** Products are listed alphabetically.
- **Inherited starter features** (Notes, My images file library, JSON API documentation) are still present and are not part of the bakery product.
- Rate limits are kept in memory, so they reset when the server restarts. Free hosting plans have their own quotas and sleep rules.

The full list is in [System documentation, section 13](docs/SYSTEM_DOCUMENTATION.md#13-known-limitations-and-cleanup-items).

## Team

| Name | Role |
| --- | --- |
| Adrianna Gomate | Project lead |
| Ann Joelle Batica | Frontend developer |
| Prince Lionel Duterte | Feature developer |
| Mika Rivera | UI and UX designer |
| Trisha Licmo-an | UI and UX designer |
| Ritz Gregorio | Content writer |
| Angelyn Sican | Content writer |
| Lorraine Badilla | Content writer |
| Ranille Robles | Content writer |
| Xander Balili | Content writer |
| Florido Akut III | Content writer |
| Gabriel Taran | Content writer |
| Clark Gayola | Content writer |
| Candy Abel | Content writer |
| Kyle Rapirap | QA tester |
| Shekienah Carrasco | QA tester |
| Carlos Clemente | QA tester |
| Justine Filipino | Documentation and demo lead |
| Servan Duller | Documentation and demo lead |

## Documentation

| Document | Contents |
| --- | --- |
| [docs/SYSTEM_DOCUMENTATION.md](docs/SYSTEM_DOCUMENTATION.md) | Architecture, data model, business rules, routes, validation, security, operations, limitations |
| [docs/TEST_PLAN.md](docs/TEST_PLAN.md) | Manual test cases with result columns for QA, defect log, automated test inventory |
| [docs/SUBMISSION_CHECKLIST.md](docs/SUBMISSION_CHECKLIST.md) | Final-submission requirements, repository hygiene, contribution evidence log |
| `docs/QUICKSTART.md`, `ARCHITECTURE.md`, `FRAMEWORK_API.md`, `BUILD_A_FEATURE.md`, `FRONTEND.md`, `API.md`, `OPERATIONS.md`, `FREE_DEPLOYMENT.md` | Guides for the starter framework this project is built on |
| `docs/VALIDATION.md` | The **starter framework's own** verification record. It is not Pastrydale's test report |

## Credits

Pastrydale was built on the *Flask Fullstack Framework* starter ([github.com/franku69/Flask-Stack-Webapp](https://github.com/franku69/Flask-Stack-Webapp)). The Pastrydale work added the product catalog (options, photos, subheadings), cart, checkout, customer and admin order management, the storefront design and the browser-side form validation. Third-party software notices are in `THIRD_PARTY.md`.
