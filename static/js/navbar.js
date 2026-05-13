const ROLE_MENUS = {

  guest: [
    { label: 'Login',      icon: 'bi-box-arrow-in-right', href: '/login/' }, 
    { label: 'Registrasi', icon: 'bi-person-plus',        href: '/pilih-role/' }, 
  ],

  admin: [
    { label: 'Dashboard',       icon: 'bi-grid-1x2',           href: '/' },
    { label: 'Manajemen Venue', icon: 'bi-building',           href: '/venue/', },
    { label: 'Manajemen Kursi', icon: 'bi-grid-3x3',           href: '/fitur_merah/templates/seat-main.html' },
    { label: 'Kategori Tiket',  icon: 'bi-tags',               href: '/ticket-categories/' },
    { label: 'Manajemen Tiket', icon: 'bi-ticket-perforated',  href: '/fitur_merah/templates/ticket-main.html?mode=all' },
    // PERBAIKAN FITUR BIRU
    { label: 'Semua Order',     icon: 'bi-cart-check',         href: '/orders/admin/' },
    { label: 'Tiket (Aset)',    icon: 'bi-collection',         href: '/fitur_merah/templates/ticket-main.html?mode=asset'},
    // PERBAIKAN FITUR BIRU
    { label: 'Order (Aset)',    icon: 'bi-receipt',            href: '/orders/admin/' },
    { label: 'Semua Event',     icon: 'bi-calendar-event',     href: '/event/' },
    { label: 'Artis',           icon: 'bi-people',             href: '/artists/' },
    // PERBAIKAN FITUR BIRU
    { label: 'Promosi',         icon: 'bi-megaphone',          href: '/promotions/' },
    { label: 'Profile',         icon: 'bi-person-circle',      href: '/profile/' },
    { label: 'Logout',          icon: 'bi-box-arrow-right',    href: '/logout/', isLogout: true },
  ],

  organizer: [
    { label: 'Dashboard',       icon: 'bi-grid-1x2',           href: '/' },
    { label: 'Event Saya',      icon: 'bi-calendar-event',     href: '/event/' },
    { label: 'Manajemen Venue', icon: 'bi-building',           href: '/venue/', },
    { label: 'Manajemen Kursi', icon: 'bi-grid-3x3',           href: '/fitur_merah/templates/seat-main.html' },
    { label: 'Kategori Tiket',  icon: 'bi-tags',               href: '/ticket-categories/' },
    { label: 'Manajemen Tiket', icon: 'bi-ticket-perforated',  href: '/fitur_merah/templates/ticket-main.html?mode=all' },
    // PERBAIKAN FITUR BIRU
    { label: 'Semua Order',     icon: 'bi-cart-check',         href: '/orders/organizer/' },
    { label: 'Tiket (Aset)',    icon: 'bi-collection',         href: '/fitur_merah/templates/ticket-main.html?mode=asset'},
    // PERBAIKAN FITUR BIRU
    { label: 'Order (Aset)',    icon: 'bi-receipt',            href: '/orders/organizer/' },
    { label: 'Artis',           icon: 'bi-people',             href: '/artists/'},
    { label: 'Profile',         icon: 'bi-person-circle',      href: '/profile/' },
    { label: 'Logout',          icon: 'bi-box-arrow-right',    href: '/logout/', isLogout: true },
  ],

  customer: [
    { label: 'Dashboard',  icon: 'bi-grid-1x2',         href: '/' },
    { label: 'Tiket Saya', icon: 'bi-ticket',           href: '/fitur_merah/templates/ticket-main.html?view=customer' },
    // PERBAIKAN FITUR BIRU
    { label: 'Pesanan',    icon: 'bi-bag-check',        href: '/orders/' },
    { label: 'Cari Event', icon: 'bi-search',           href: '/event/' },
    // PERBAIKAN FITUR BIRU
    { label: 'Promosi',    icon: 'bi-megaphone',        href: '/promotions/' },
    { label: 'Venue',      icon: 'bi-geo-alt',          href: '/venue/' },
    { label: 'Artis',      icon: 'bi-people',           href: '/artists/' },
    { label: 'Logout',     icon: 'bi-box-arrow-right',  href: '/logout/', isLogout: true },
  ]

};

const ROLE_DISPLAY_NAMES = {
  admin:     'Administrator',
  organizer: 'Event Organizer',
  customer:  'Customer',
  guest:     'Guest'
};

// RENDER SIDEBAR 
function renderSidebar(role) {
  const menuContainer = document.getElementById('sidebarMenu');
  const roleLabel     = document.getElementById('roleLabel');

  const items    = ROLE_MENUS[role] || ROLE_MENUS.guest;
  const safeRole = ROLE_MENUS[role] ? role : 'guest';

  if (roleLabel) {
    roleLabel.innerText = ROLE_DISPLAY_NAMES[safeRole];
  }

  menuContainer.innerHTML = '';

  // Pakai cara simpel buat deteksi halaman aktif
  const currentPath = window.location.pathname;
  
  items.forEach(item => {
    const li = document.createElement('li');
    li.className = 'nav-item-custom';

    // Cek apakah menu ini lagi aktif (biar warnanya ijo)
    const isActive = currentPath === item.href;

    let onClickHandler = '';
    if (item.isLogout) {
      onClickHandler = 'onclick="simulateLogout(event)"';
    }

    li.innerHTML = `
      <a href="${item.href}" class="nav-link-custom ${isActive ? 'active' : ''} ${item.isLogout ? 'logout-link' : ''}" ${onClickHandler}>
        <i class="bi ${item.icon}"></i>
        <span>${item.label}</span>
      </a>`;
    menuContainer.appendChild(li);
  });
}

// UPDATE ROLE
function updateRole(newRole) {
  localStorage.setItem('role', newRole);
  renderSidebar(newRole);
}

// LOGOUT
function simulateLogout(event) {
  event.preventDefault();
  localStorage.removeItem('role');
  window.location.href = '/logout/'; 
}

// DARK MODE
function toggleDarkMode() {
  const html   = document.documentElement;
  const icon   = document.getElementById('themeIcon');
  const isDark = html.getAttribute('data-bs-theme') === 'dark';
  html.setAttribute('data-bs-theme', isDark ? 'light' : 'dark');
  icon.className = isDark ? 'bi bi-moon-stars' : 'bi bi-sun';
  localStorage.setItem('theme', isDark ? 'light' : 'dark');
}

// AUTO INIT 
(function init() {
  const savedRole  = localStorage.getItem('role')  || 'guest';
  const savedTheme = localStorage.getItem('theme') || 'light';

  document.documentElement.setAttribute('data-bs-theme', savedTheme);

  const themeIcon = document.getElementById('themeIcon');
  if (themeIcon) {
    themeIcon.className = savedTheme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
  }

  renderSidebar(savedRole);
})();