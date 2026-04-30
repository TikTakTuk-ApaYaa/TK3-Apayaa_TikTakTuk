const ROLE_MENUS = {

  guest: [
    { label: 'Login',      icon: 'bi-box-arrow-in-right', href: '/fitur_wajib/templates/login.html' },
    { label: 'Registrasi', icon: 'bi-person-plus',        href: 'Cpengguna_pilihRole.html' },
  ],

  admin: [
    { label: 'Dashboard',       icon: 'bi-grid-1x2',           href: '/fitur_wajib/templates/dashboard.html' },
    { label: 'Manajemen Venue', icon: 'bi-building',           href: '/fitur_kuning/templates/venue.html' },
    { label: 'Manajemen Kursi', icon: 'bi-grid-3x3',           href: '/fitur_merah/templates/seat-main.html' },
    { label: 'Kategori Tiket',  icon: 'bi-tags',               href: '/fitur_hijau/templates/ticket_category_list.html' },
    { label: 'Manajemen Tiket', icon: 'bi-ticket-perforated',  href: '/fitur_merah/templates/ticket-main.html?mode=all' },
    { label: 'Semua Order',     icon: 'bi-cart-check',         href: '/fitur_biru/templates/read_order_admin.html?mode=all' },
    { label: 'Tiket (Aset)',    icon: 'bi-collection',         href: '/fitur_merah/templates/ticket-main.html?mode=asset'},
    { label: 'Order (Aset)',    icon: 'bi-receipt',            href: '/fitur_biru/templates/read_order_admin.html?mode=asset' },
    { label: 'Semua Event',     icon: 'bi-calendar-event',     href: '/fitur_kuning/templates/event.html' },
    { label: 'Artis',           icon: 'bi-people',             href: '/fitur_hijau/templates/artist_list.html' },
    { label: 'Promosi',         icon: 'bi-megaphone',          href: '/fitur_biru/templates/CRUD_promo_admin.html' },
    { label: 'Profile',         icon: 'bi-person-circle',      href: '../../fitur_wajib/templates/profile.html' },
    { label: 'Logout',          icon: 'bi-box-arrow-right',    href: '/fitur_wajib/templates/login.html', isLogout: true },
  ],

  organizer: [
    { label: 'Dashboard',       icon: 'bi-grid-1x2',           href: '/fitur_wajib/templates/dashboard.html' },
    { label: 'Event Saya',      icon: 'bi-calendar-event',     href: '/fitur_kuning/templates/event.html' },
    { label: 'Manajemen Venue', icon: 'bi-building',           href: '/fitur_kuning/templates/venue.html' },
    { label: 'Manajemen Kursi', icon: 'bi-grid-3x3',           href: '/fitur_merah/templates/seat-main.html' },
    { label: 'Kategori Tiket',  icon: 'bi-tags',               href: '/fitur_hijau/templates/ticket_category_list.html' },
    { label: 'Manajemen Tiket', icon: 'bi-ticket-perforated',  href: '/fitur_merah/templates/ticket-main.html?mode=all' },
    { label: 'Semua Order',     icon: 'bi-cart-check',         href: '/fitur_biru/templates/read_order_organizer.html?mode=all' },
    { label: 'Tiket (Aset)',    icon: 'bi-collection',         href: '/fitur_merah/templates/ticket-main.html?mode=asset'},
    { label: 'Order (Aset)',    icon: 'bi-receipt',            href: '/fitur_biru/templates/read_order_organizer.html?mode=asset' },
    { label: 'Artis',           icon: 'bi-people',             href: '/fitur_hijau/templates/artist_list.html' },
    { label: 'Profile',         icon: 'bi-person-circle',      href: '../../fitur_wajib/templates/profile.html' },
    { label: 'Logout',          icon: 'bi-box-arrow-right',    href: '/fitur_wajib/templates/login.html', isLogout: true },
  ],

  customer: [
    { label: 'Dashboard',  icon: 'bi-grid-1x2',         href: '/fitur_wajib/templates/dashboard.html' },
    { label: 'Tiket Saya', icon: 'bi-ticket',           href: '/fitur_merah/templates/ticket-main.html?view=customer' },
    { label: 'Pesanan',    icon: 'bi-bag-check',        href: '/fitur_biru/templates/read_order_cust.html' },
    { label: 'Cari Event', icon: 'bi-search',           href: '/fitur_kuning/templates/event.html' },
    { label: 'Promosi',    icon: 'bi-megaphone',        href: '/fitur_biru/templates/read_promo_cust.html' },
    { label: 'Venue',      icon: 'bi-geo-alt',          href: '/fitur_kuning/templates/venue.html' },
    { label: 'Artis',      icon: 'bi-people',           href: '/fitur_hijau/templates/artist_list.html' },
    { label: 'Logout',     icon: 'bi-box-arrow-right',  href: '/fitur_wajib/templates/login.html', isLogout: true },
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


  const currentFullPath = window.location.pathname + window.location.search;
  
  items.forEach(item => {
    const li = document.createElement('li');

    let isActive = false;
    if (item.href !== '#' && !item.isLogout) {
      const itemUrl = new URL(item.href, window.location.origin);
      const itemFullPath = itemUrl.pathname + itemUrl.search;

      isActive = currentFullPath === itemFullPath;
    }

    li.className = 'nav-item-custom';

    let onClickHandler = '';
    if (item.isLogout) {
      onClickHandler = 'onclick="simulateLogout(event)"';
    } else if (item.action) {
      onClickHandler = `onclick="${item.action}; return false;"`; 
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
  window.location.href = '/fitur_wajib/templates/navbar.html';
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
