/* SHIRA сайт — скрипт интерфейса */

(function () {
  'use strict';

  var toggle = document.getElementById('nav-toggle');
  var nav = document.getElementById('main-nav');

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Закрытие меню при выборе ссылки
    var links = nav.querySelectorAll('a');
    links.forEach(function (link) {
      link.addEventListener('click', function () {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // Аккордеон FAQ
  var questions = document.querySelectorAll('.faq-question');
  questions.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var expanded = btn.getAttribute('aria-expanded') === 'true';
      var answer = btn.nextElementSibling;

      // Скрыть все остальные ответы
      questions.forEach(function (other) {
        if (other !== btn) {
          other.setAttribute('aria-expanded', 'false');
          var otherAnswer = other.nextElementSibling;
          if (otherAnswer) {
            otherAnswer.hidden = true;
          }
        }
      });

      btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      if (answer) {
        answer.hidden = expanded;
      }
    });
  });
})();
