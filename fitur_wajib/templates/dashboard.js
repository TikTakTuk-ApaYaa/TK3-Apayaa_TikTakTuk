//  DATA
const ROLE_DATA = {
  admin: {
    name: 'System Admin', initial: 'A', color: '#b45309',
    badgeClass: 'bg-warning text-dark', badgeText: 'Administrator',
    username: 'sysadmin', password: 'admin123',
  },
  organizer: {
    name: 'Andi Wijaya', initial: 'A', color: '#2563eb',
    badgeClass: 'bg-primary', badgeText: 'Penyelenggara',
    username: 'organizer1', organizerName: 'Andi Wijaya',
    contactEmail: 'organizer1@example.com', password: 'organizer123',
  },
  customer: {
    name: 'Budi Santoso', initial: 'B', color: '#1a7a4a',
    badgeClass: 'bg-success', badgeText: 'Pelanggan',
    username: 'customer1', fullName: 'Budi Santoso',
    phoneNumber: '+62812345678', password: 'customer123',
  },
};

let currentRole = localStorage.getItem('role') || 'admin';
let currentPage = 'dashboard';

function adaptSidebarLinks() {
  document.querySelectorAll('.nav-link-custom').forEach(link => {
    const text = link.textContent.trim().toLowerCase();
    if (text === 'profile') {
      link.href = '#';
      link.setAttribute('onclick', "showPage('profile'); return false;");
    } else if (text === 'dashboard') {
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

  const titles = { dashboard:'Dashboard', profile:'Profil Saya' };
  document.getElementById('topBarTitle').textContent = titles[pageId] || pageId;

  if (pageId === 'profile') renderProfile();
}

//  DASHBOARD RENDER
function renderDashboard(role) {
  const r = role || currentRole;
  document.getElementById('dash-admin').classList.toggle('d-none',    r !== 'admin');
  document.getElementById('dash-organizer').classList.toggle('d-none', r !== 'organizer');
  document.getElementById('dash-customer').classList.toggle('d-none',  r !== 'customer');
}

//  PROFILE RENDER
function renderProfile() {
  const d = ROLE_DATA[currentRole];
  document.getElementById('profile-avatar-disp').textContent = d.initial;
  document.getElementById('profile-avatar-disp').style.background = d.color;
  document.getElementById('profile-name-disp').textContent = d.name;
  const badge = document.getElementById('profile-role-badge-disp');
  badge.textContent = d.badgeText;
  badge.className = `badge ${d.badgeClass} mt-1`;

  document.getElementById('profile-admin-info').classList.toggle('d-none',    currentRole !== 'admin');
  document.getElementById('profile-customer-info').classList.toggle('d-none', currentRole !== 'customer');
  document.getElementById('profile-organizer-info').classList.toggle('d-none',currentRole !== 'organizer');

  document.getElementById('editProfileBtn').classList.toggle('d-none', currentRole === 'admin');

  if (currentRole === 'customer') {
    document.getElementById('disp-fullname').textContent = d.fullName;
    document.getElementById('disp-phone').textContent    = d.phoneNumber;
  }
  if (currentRole === 'organizer') {
    document.getElementById('disp-orgname').textContent = d.organizerName;
    document.getElementById('disp-email').textContent   = d.contactEmail;
  }
}

function openEditProfile() {
  if (currentRole === 'customer') {
    const d = ROLE_DATA.customer;
    document.getElementById('edit-fullname').value = d.fullName;
    document.getElementById('edit-phone').value    = d.phoneNumber;
    new bootstrap.Modal(document.getElementById('modalEditCustomer')).show();
  } else if (currentRole === 'organizer') {
    const d = ROLE_DATA.organizer;
    document.getElementById('edit-orgname').value = d.organizerName;
    document.getElementById('edit-email').value   = d.contactEmail;
    new bootstrap.Modal(document.getElementById('modalEditOrganizer')).show();
  }
}

function saveProfileCustomer() {
  const name  = document.getElementById('edit-fullname').value.trim();
  const phone = document.getElementById('edit-phone').value.trim();
  if (!name) { showToast('Nama lengkap wajib diisi!', 'danger'); return; }
  ROLE_DATA.customer.fullName     = name;
  ROLE_DATA.customer.phoneNumber  = phone;
  ROLE_DATA.customer.name         = name;
  ROLE_DATA.customer.initial      = name.charAt(0).toUpperCase();
  bootstrap.Modal.getInstance(document.getElementById('modalEditCustomer')).hide();
  renderProfile();
  showToast('Profil berhasil diperbarui!', 'success');
}

function saveProfileOrganizer() {
  const orgname = document.getElementById('edit-orgname').value.trim();
  const email   = document.getElementById('edit-email').value.trim();
  if (!orgname) { showToast('Nama organizer wajib diisi!', 'danger'); return; }
  ROLE_DATA.organizer.organizerName = orgname;
  ROLE_DATA.organizer.contactEmail  = email;
  ROLE_DATA.organizer.name          = orgname;
  ROLE_DATA.organizer.initial       = orgname.charAt(0).toUpperCase();
  bootstrap.Modal.getInstance(document.getElementById('modalEditOrganizer')).hide();
  renderProfile();
  showToast('Profil berhasil diperbarui!', 'success');
}

//  PASSWORD UPDATE
function savePassword() {
  const oldPw  = document.getElementById('pw-old').value;
  const newPw  = document.getElementById('pw-new').value;
  const confPw = document.getElementById('pw-confirm').value;
  const d      = ROLE_DATA[currentRole];
  if (!oldPw || !newPw || !confPw) { showToast('Semua field password wajib diisi!', 'danger'); return; }
  if (oldPw !== d.password)        { showToast('Password lama tidak sesuai!', 'danger'); return; }
  if (newPw.length < 6)            { showToast('Password baru minimal 6 karakter!', 'danger'); return; }
  if (newPw !== confPw)            { showToast('Konfirmasi password tidak cocok!', 'danger'); return; }
  d.password = newPw;
  clearPassword();
  showToast('Password berhasil diperbarui!', 'success');
}

function clearPassword() {
  ['pw-old','pw-new','pw-confirm'].forEach(id => document.getElementById(id).value = '');
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