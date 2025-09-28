(function() {
  // Preloader
  window.addEventListener('load', function() {
    const el = document.getElementById('preloader');
    if (el) el.style.display = 'none';
    // Cookie bar
    if (!localStorage.getItem('cookieAccepted')) {
      document.getElementById('cookieBar')?.classList.remove('d-none');
    }
  });

  // Back to top button
  const back = document.getElementById('backToTop');
  window.addEventListener('scroll', function() {
    if (window.scrollY > 500) back && (back.style.display = 'block');
    else back && (back.style.display = 'none');
  });

  // Cookie bar actions
  const allow = document.getElementById('cookieAllow');
  const decline = document.getElementById('cookieDecline');
  allow && allow.addEventListener('click', () => {
    localStorage.setItem('cookieAccepted', '1');
    document.getElementById('cookieBar')?.classList.add('d-none');
  });
  decline && decline.addEventListener('click', () => {
    document.getElementById('cookieBar')?.classList.add('d-none');
  });

  // Footer year
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  // Sticky navbar shadow after scroll
  const nav = document.getElementById('mainNav');
  const toggleShadow = () => {
    if (!nav) return;
    if (window.scrollY > 10) nav.classList.add('shadow-sm');
    else nav.classList.remove('shadow-sm');
  };
  window.addEventListener('scroll', toggleShadow);
  toggleShadow();

})();