// Sign-up form: validate the fields, "create" the account (a fake request), then confirm.
(function () {
  const form = document.getElementById('signup');
  const message = document.getElementById('message');
  const overlay = document.getElementById('overlay');
  const button = document.getElementById('submit');
  const toast = document.getElementById('toast');

  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function value(id) { return document.getElementById(id).value; }

  // Each rule names the condition under which the form is not acceptable, and the message shown then.
  function rules() {
    const name = value('name').trim();
    const email = value('email').trim();
    const password = value('password');
    const confirm = value('confirm');
    const terms = document.getElementById('terms').checked;
    return [
      { failed: name.length < 2,        text: 'Enter your full name.' },
      { failed: EMAIL.test(email),      text: 'Enter a valid work e-mail address.' },
      { failed: password.length < 8,    text: 'Your password needs at least 8 characters.' },
      { failed: password !== confirm,   text: 'The two passwords do not match.' },
      { failed: !terms,                 text: 'Please accept the Terms of Service to continue.' },
    ];
  }

  function show(kind, text) {
    message.className = 'msg ' + kind;
    message.textContent = text;
  }

  function announce(text) {
    toast.textContent = text;
    toast.classList.add('show');
    setTimeout(function () { toast.classList.remove('show'); }, 2200);
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    message.className = 'msg';
    message.textContent = '';

    const broken = rules().find(function (rule) { return rule.failed; });
    if (broken) { show('error', broken.text); return; }

    // The account request is in flight: the form is covered until it answers.
    const firstName = value('name').trim().split(/\s+/)[0];
    const email = value('email').trim();
    button.disabled = true;
    button.textContent = 'Creating your account…';
    overlay.classList.add('on');
    setTimeout(function () {
      overlay.classList.remove('on');
      button.disabled = false;
      button.textContent = 'Create account';
      form.reset();
      show('success', 'Welcome, ' + firstName + '! We sent a confirmation link to ' + email + '. Check your inbox to activate your account.');
      announce('Account created');
    }, 1200);
  });
})();
