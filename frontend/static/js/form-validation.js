/*
  Progressive client-side validation.

  Forms opt in with `data-validate-form`. Individual fields choose a rule with
  `data-validate="<rule>"`. Required-ness comes from the native `required`
  attribute. The server remains the source of truth: this only gives people
  quick, friendly feedback before the request is sent.
*/

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PERSON_NAME = /^[\p{L}\p{M}][\p{L}\p{M}\s.'’-]*$/u;

const rules = {
  fullname(value) {
    if (value.length > 100) return 'Please keep your name under 100 characters.';
    if (!PERSON_NAME.test(value)) return 'Names can only include letters, spaces, apostrophes, periods and hyphens.';
    if (value.split(/\s+/).length < 2) return 'Please enter your first and last name.';
    return '';
  },
  name(value) {
    if (value.length < 2) return 'Please enter at least 2 characters.';
    if (value.length > 100) return 'Please keep your name under 100 characters.';
    if (!PERSON_NAME.test(value)) return 'Names can only include letters, spaces, apostrophes, periods and hyphens.';
    return '';
  },
  email(value) {
    if (value.length > 254 || !EMAIL.test(value)) return 'Enter a valid email address, like name@example.com.';
    return '';
  },
  phone(value) {
    const digits = value.replace(/[\s().-]/g, '');
    const mobile = /^(\+?63|0)9\d{9}$/.test(digits);          // 0917…, 63917…, +63917…
    const landline = /^0\d{8,10}$/.test(digits);               // 082 123 4567
    const international = /^\+\d{8,15}$/.test(digits);
    if (!(mobile || landline || international)) {
      return 'Enter a valid phone number, like 0917 123 4567 or +63 917 123 4567.';
    }
    return '';
  },
  address(value) {
    if (value.length < 10) return 'Please include your street, barangay and unit or building so we can find you.';
    if (value.length > 255) return 'Please keep your address under 255 characters.';
    return '';
  },
  city(value) {
    if (value.length < 2 || !/\p{L}/u.test(value)) return 'Please enter a valid city.';
    if (value.length > 100) return 'Please keep the city under 100 characters.';
    return '';
  },
  notes(value, input) {
    const max = Number(input.maxLength) > 0 ? input.maxLength : 500;
    return value.length > max ? `Please keep your notes under ${max} characters.` : '';
  },
  message(value) {
    if (value.length < 10) return 'Tell us a little more, at least 10 characters.';
    if (value.length > 2000) return 'Please keep your message under 2,000 characters.';
    return '';
  },
  'password-new'(value) {
    if (value.length < 12) return `Use at least 12 characters (you have ${value.length}).`;
    if (value.length > 128) return 'Use 128 characters or fewer.';
    return '';
  },
  confirm(value, input, form) {
    const original = form.querySelector('input[autocomplete="new-password"]:not([data-validate="confirm"])');
    return original && value !== original.value ? 'Passwords do not match.' : '';
  }
};

function labelFor(input) {
  const label = input.form?.querySelector(`label[for="${CSS.escape(input.id)}"]`);
  return (label?.textContent || input.name || 'This field')
    .replace(/\(.*?\)/g, '').replace(/\*/g, '').trim();
}

function validateInput(input, form) {
  if (input.disabled || input.closest('.honeypot')) return '';
  // Passwords must keep their exact characters; everything else is trimmed.
  const value = input.type === 'password' ? input.value : input.value.trim();
  if (!value) {
    return input.required ? `${labelFor(input)} is required.` : '';
  }
  const rule = rules[input.dataset.validate];
  return rule ? rule(value, input, form) : '';
}

function showError(input, message) {
  const hint = document.getElementById(`${input.id}-hint`);
  if (!hint) return;
  // Any message from the server is now stale, so replace it.
  hint.querySelectorAll('.field-error').forEach(node => node.remove());
  if (message) {
    const error = document.createElement('p');
    error.className = 'field-error';
    error.dataset.client = '';
    error.setAttribute('role', 'alert');
    error.textContent = message;
    hint.append(error);
  }
  input.setAttribute('aria-invalid', message ? 'true' : 'false');
  input.classList.toggle('is-valid', !message && input.value.trim() !== '');
}

function wirePasswordToggle(input) {
  const wrap = document.createElement('div');
  wrap.className = 'input-wrap';
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'input-toggle';
  toggle.textContent = 'Show';
  toggle.setAttribute('aria-pressed', 'false');
  toggle.setAttribute('aria-label', 'Show password');
  toggle.addEventListener('click', () => {
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    toggle.textContent = show ? 'Hide' : 'Show';
    toggle.setAttribute('aria-pressed', String(show));
    toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });
  input.replaceWith(wrap);
  wrap.append(input, toggle);
}

function wireCounter(input) {
  const max = Number(input.maxLength);
  if (!(max > 0) || input.tagName !== 'TEXTAREA') return;
  const hint = document.getElementById(`${input.id}-hint`);
  const counter = document.createElement('small');
  counter.className = 'hint field-counter';
  counter.setAttribute('aria-hidden', 'true');
  hint?.prepend(counter);
  const update = () => { counter.textContent = `${input.value.length} / ${max}`; };
  input.addEventListener('input', update);
  update();
}

function initForm(form) {
  form.noValidate = true; // we show friendlier messages than the browser does
  const inputs = [...form.querySelectorAll('input, textarea, select')]
    .filter(input => !['hidden', 'submit', 'button'].includes(input.type) && !input.closest('.honeypot'));
  const touched = new WeakSet();

  inputs.filter(input => input.type === 'password').forEach(wirePasswordToggle);
  inputs.forEach(wireCounter);

  const check = input => {
    const message = validateInput(input, form);
    showError(input, message);
    return !message;
  };

  inputs.forEach(input => {
    input.addEventListener('blur', () => { touched.add(input); check(input); });
    input.addEventListener('input', () => {
      if (touched.has(input) || input.getAttribute('aria-invalid') === 'true') check(input);
      // Editing the password re-checks the confirmation field.
      if (input.autocomplete === 'new-password' && input.dataset.validate !== 'confirm') {
        const confirm = form.querySelector('[data-validate="confirm"]');
        if (confirm && touched.has(confirm)) check(confirm);
      }
    });
  });

  form.addEventListener('submit', event => {
    let firstInvalid = null;
    for (const input of inputs) {
      touched.add(input);
      if (!check(input) && !firstInvalid) firstInvalid = input;
    }
    if (firstInvalid) {
      event.preventDefault();
      firstInvalid.focus();
      firstInvalid.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }
    // Stop accidental double submits (double orders, double messages).
    const submit = form.querySelector('[type="submit"]');
    if (submit && form.dataset.loadingText) {
      submit.dataset.label = submit.value || submit.textContent;
      setTimeout(() => {
        submit.disabled = true;
        submit.setAttribute('aria-busy', 'true');
        if (submit.tagName === 'INPUT') submit.value = form.dataset.loadingText;
        else submit.textContent = form.dataset.loadingText;
      }, 0);
    }
  });

  // Back/forward cache can restore a page mid-submit.
  window.addEventListener('pageshow', event => {
    const submit = form.querySelector('[type="submit"]');
    if (event.persisted && submit?.disabled) {
      submit.disabled = false;
      submit.removeAttribute('aria-busy');
      if (submit.tagName === 'INPUT') submit.value = submit.dataset.label;
      else submit.textContent = submit.dataset.label;
    }
  });
}

document.querySelectorAll('form[data-validate-form]').forEach(initForm);
