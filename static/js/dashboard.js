
let currentRole = localStorage.getItem('role') || 'guest';
let currentPage = 'dashboard';

function adaptSidebarLinks() {
  document.querySelectorAll('.nav-link-custom').forEach(link => {
    const text = link.textContent.trim().toLowerCase();
    if (text === 'dashboard') {
      link.href = '#';
      link.setAttribute('onclick', "showPage('dashboard'); return false;");
    }
  });
}

window.updateRole = function(role) {
  currentRole = role;
  localStorage.setItem('role', role);

  if (typeof renderSidebar === 'function') renderSidebar(role);

  // Update label di topbar
  const roleLabel = document.getElementById('roleLabel');
  if (roleLabel) {
    const labels = { admin: 'Administrator', organizer: 'Event Organizer', customer: 'Customer', guest: 'Guest' };
    roleLabel.textContent = labels[role] || role;
  }
};

function showPage(pageId) {
  currentPage = pageId;
  document.querySelectorAll('.tt-page').forEach(p => p.classList.remove('active'));
  const pg = document.getElementById('page-' + pageId);
  if (pg) pg.classList.add('active');

  document.querySelectorAll('.nav-link-custom').forEach(n => {
    n.classList.remove('active');
    if (n.textContent.trim().toLowerCase() === pageId) n.classList.add('active');
  });

  const topTitle = document.getElementById('topBarTitle');
  if (topTitle) topTitle.textContent = 'Dashboard';
}

function showToast(msg, type = 'success') {
  const el = document.getElementById('liveToast');
  if (el) {
    el.className = `toast align-items-center border-0 text-bg-${type}`;
    document.getElementById('toastMsg').textContent = msg;
    new bootstrap.Toast(el, { delay: 3000 }).show();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    adaptSidebarLinks();
    showPage(currentPage);
  }, 50);
});