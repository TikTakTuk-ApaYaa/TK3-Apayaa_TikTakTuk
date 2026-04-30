let currentRole = localStorage.getItem('role') || 'admin';
let currentPage = 'dashboard';

function adaptSidebarLinks() {
  document.querySelectorAll('.nav-link-custom').forEach(link => {
    const text = link.textContent.trim().toLowerCase();
    // Cukup atur yang Dashboard aja, Profile biarkan normal pindah halaman
    if (text === 'dashboard') {
      link.href = '#';
      link.setAttribute('onclick', "showPage('dashboard'); return false;");
    }
  });
}

window.updateRole = function(role) {
  currentRole = role;
  localStorage.setItem('role', role);
  currentPage = 'dashboard';
  
  if (typeof renderSidebar === 'function') {
      renderSidebar(role);
  }
  
  adaptSidebarLinks();
  
  renderDashboard(role);
  showPage('dashboard');
};

//  PAGE NAVIGATION
function showPage(pageId) {
  currentPage = pageId;
  document.querySelectorAll('.tt-page').forEach(p => p.classList.remove('active'));
  const pg = document.getElementById('page-' + pageId);
  if (pg) pg.classList.add('active');

  document.querySelectorAll('.nav-link-custom').forEach(n => {
      n.classList.remove('active');
      if (n.textContent.trim().toLowerCase() === pageId) {
          n.classList.add('active');
      }
  });

  const titles = { dashboard:'Dashboard' };
  document.getElementById('topBarTitle').textContent = titles[pageId] || pageId;
}

//  DASHBOARD RENDER
function renderDashboard(role) {
  const r = role || currentRole;
  document.getElementById('dash-admin').classList.toggle('d-none',    r !== 'admin');
  document.getElementById('dash-organizer').classList.toggle('d-none', r !== 'organizer');
  document.getElementById('dash-customer').classList.toggle('d-none',  r !== 'customer');
}

//  TOAST
function showToast(msg, type='success') {
  const el = document.getElementById('liveToast');
  el.className = `toast align-items-center border-0 text-bg-${type}`;
  document.getElementById('toastMsg').textContent = msg;
  new bootstrap.Toast(el, { delay: 3000 }).show();
}

// INIT LOKAL
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
     adaptSidebarLinks();
     showPage(currentPage);
     renderDashboard(currentRole);
  }, 100); 
});