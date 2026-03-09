/**
 * Healer Nexus — спільний модуль sidebar навігації.
 * Залежить від auth.js (window.HealerAuth).
 * Підключення (після auth.js): <script src="/static/js/sidebar.js"></script>
 */
(function () {
    'use strict';

    var SIDEBAR_STYLE_ID = 'healer-sidebar-styles';

    function getStyles() {
        return '<style id="' + SIDEBAR_STYLE_ID + '">' +
            '.healer-sidebar { position: fixed; left: 0; top: 0; width: 260px; height: 100vh; background: #f8f9fa; display: flex; flex-direction: column; z-index: 1000; border-right: 1px solid #e9ecef; }' +
            '.healer-sidebar-nav { flex: 1; overflow-y: auto; padding: 8px 0; }' +
            '.healer-sidebar .nav { padding: 0; }' +
            '.healer-sidebar .nav a { display: flex; align-items: center; gap: 10px; padding: 12px 20px; color: #495057; text-decoration: none; font-size: 14px; transition: background 0.2s, color 0.2s; border: none; background: none; width: 100%; text-align: left; cursor: pointer; font-family: inherit; }' +
            '.healer-sidebar .nav a:hover { background: #e9ecef; color: #1a1a2e; }' +
            '.healer-sidebar .nav a.active { background: #4a7c59; color: #fff; }' +
            '.healer-sidebar .nav a.disabled { opacity: 0.5; cursor: not-allowed; pointer-events: none; }' +
            '.healer-sidebar .nav .badge { margin-left: auto; background: #e74c3c; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 10px; min-width: 20px; text-align: center; }' +
            '.healer-sidebar-footer { border-top: 1px solid #e0e0e0; padding: 12px 16px; flex-shrink: 0; background: #f8f9fa; }' +
            '.healer-sidebar-footer .user-name { font-weight: 600; font-size: 14px; color: #1a1a2e; margin: 0 0 4px 0; }' +
            '.healer-sidebar-footer .user-role { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 8px; background: #dee2e6; color: #495057; }' +
            '.healer-sidebar-footer .user-role.admin { background: #4a7c59; color: #fff; }' +
            '.healer-sidebar-footer .user-role.practitioner { background: #667eea; color: #fff; }' +
            '.healer-sidebar-footer .btn-logout { display: block; width: 100%; margin-top: 12px; padding: 10px 16px; background: #e74c3c; color: #fff; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }' +
            '.healer-sidebar-footer .btn-logout:hover { background: #c0392b; }' +
            '.healer-sidebar .sidebar-header p { margin: 0; font-size: 12px; color: #6c757d; }' +
            '.healer-sidebar .sidebar-header h3 { margin: 0 0 4px 0; font-size: 18px; color: #1a1a2e; font-weight: 700; }' +
            '</style>';
    }

    function getMenuItems(role) {
        if (role === 'admin') {
            return [
                { section: 'overview', label: 'Огляд', icon: '📊' },
                { section: 'applications', label: 'Заявки спеціалістів', icon: '📋', badge: true },
                { section: 'users', label: 'Спеціалісти', icon: '🧑‍⚕️' },
                { section: 'clients', label: 'Клієнти', icon: '🙋' },
                { section: 'brain', label: 'Brain Insights', icon: '🧠' },
                { section: 'stats', label: 'Статистика', icon: '📈' },
                { section: 'map', label: 'Анкети спеціалістів', icon: '📂' },
                { section: 'settings', label: 'Налаштування', icon: '⚙️' }
            ];
        }
        if (role === 'practitioner') {
            return [
                { section: 'overview', label: 'Огляд', icon: '📊' },
                { section: 'blog', label: 'Мій блог', icon: '📝' },
                { section: 'bookings', label: 'Бронювання', icon: '📅' },
                { section: 'ai-generator', label: 'AI Генератор', icon: '🤖' },
                { section: 'analytics', label: 'Аналітика', icon: '📈' },
                { section: 'social', label: 'Соцмережі', icon: '🌐' },
                { section: 'reviews', label: 'Відгуки', icon: '⭐', disabled: true },
                { section: 'profile', label: 'Мій профіль', icon: '👤' }
            ];
        }
        return [];
    }

    function renderSidebar(containerId) {
        if (!window.HealerAuth) return;
        var user = window.HealerAuth.getUser();
        if (!user) return;
        var role = user.role || '';
        var container = document.getElementById(containerId);
        if (!container) return;

        var displayName = user.full_name || user.name || user.username || user.email || 'Користувач';
        var roleLabel = role === 'admin' ? 'Admin' : (role === 'practitioner' ? 'Спеціаліст' : role);
        var roleClass = role === 'admin' ? 'admin' : (role === 'practitioner' ? 'practitioner' : '');

        var items = getMenuItems(role);
        var navHtml = items.map(function (item) {
            var cls = item.disabled ? ' disabled' : '';
            var badgeHtml = item.badge ? ' <span class="badge" data-badge-section="' + item.section + '" style="display:none">0</span>' : '';
            return '<a href="#" class="nav-item' + cls + '" data-section="' + item.section + '" onclick="return window.HealerSidebar && window.showSection && (showSection(\'' + item.section + '\'), false);">' +
                '<span class="icon">' + item.icon + '</span><span>' + item.label + '</span>' + badgeHtml + '</a>';
        }).join('');

        if (!document.getElementById(SIDEBAR_STYLE_ID)) {
            document.head.insertAdjacentHTML('beforeend', getStyles());
        }

        container.innerHTML =
            '<div class="healer-sidebar">' +
            '<div class="sidebar-header" style="padding: 16px; flex-shrink: 0;">' +
            '<h3>Healer Nexus</h3>' +
            '<p>Панель управління</p>' +
            '</div>' +
            '<div class="healer-sidebar-nav">' +
            '<nav class="nav">' + navHtml + '</nav>' +
            '</div>' +
            '<div class="healer-sidebar-footer">' +
            '<div class="user-name">' + escapeHtml(displayName) + '</div>' +
            '<span class="user-role ' + roleClass + '">' + escapeHtml(roleLabel) + '</span>' +
            '<button type="button" class="btn-logout" onclick="HealerAuth.logout()">Вийти</button>' +
            '</div>' +
            '</div>';
    }

    function escapeHtml(s) {
        if (s == null) return '';
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function setActiveSection(sectionName) {
        var container = document.querySelector('.healer-sidebar');
        if (!container) return;
        container.querySelectorAll('.nav a[data-section]').forEach(function (a) {
            if (a.getAttribute('data-section') === sectionName) {
                a.classList.add('active');
            } else {
                a.classList.remove('active');
            }
        });
    }

    function updateBadge(sectionName, count) {
        var badge = document.querySelector('.healer-sidebar .nav a[data-section="' + sectionName + '"] .badge[data-badge-section]');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? '' : 'none';
        }
    }

    window.HealerSidebar = {
        renderSidebar: renderSidebar,
        setActiveSection: setActiveSection,
        updateBadge: updateBadge
    };
})();
