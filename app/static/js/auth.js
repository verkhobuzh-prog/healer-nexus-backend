/**
 * Healer Nexus — спільний модуль авторизації для дашборду.
 * Підключення: <script src="/static/js/auth.js"></script>
 * Використання: HealerAuth.getAccessToken(), HealerAuth.checkAuth(), тощо.
 */
(function () {
    'use strict';

    function getAccessToken() {
        return localStorage.getItem('access_token');
    }

    function getRefreshToken() {
        return localStorage.getItem('refresh_token');
    }

    function getUser() {
        try {
            var raw = localStorage.getItem('user');
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    function isAdmin() {
        var user = getUser();
        return user && user.role === 'admin';
    }

    function isPractitioner() {
        var user = getUser();
        return user && user.role === 'practitioner';
    }

    function logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/dashboard/login';
    }

    function getAuthHeaders() {
        return {
            'Authorization': 'Bearer ' + getAccessToken(),
            'Content-Type': 'application/json'
        };
    }

    function refreshAccessToken() {
        var refreshToken = getRefreshToken();
        if (!refreshToken) {
            logout();
            return Promise.resolve(null);
        }
        return fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        }).then(function (res) {
            if (res && res.ok) {
                return res.json().then(function (data) {
                    if (data.access_token) {
                        localStorage.setItem('access_token', data.access_token);
                        if (data.refresh_token) {
                            localStorage.setItem('refresh_token', data.refresh_token);
                        }
                        return data.access_token;
                    }
                    return null;
                });
            }
            logout();
            return null;
        }).catch(function () {
            logout();
            return null;
        });
    }

    function checkAuth() {
        if (!getAccessToken()) {
            logout();
            return Promise.resolve(null);
        }
        return fetch('/api/auth/me', {
            headers: getAuthHeaders()
        }).then(function (res) {
            if (res && res.ok) {
                return res.json();
            }
            if (res && res.status === 401) {
                return refreshAccessToken().then(function (newToken) {
                    if (!newToken) return null;
                    return fetch('/api/auth/me', {
                        headers: getAuthHeaders()
                    }).then(function (retryRes) {
                        if (retryRes && retryRes.ok) {
                            return retryRes.json();
                        }
                        logout();
                        return null;
                    });
                });
            }
            logout();
            return null;
        }).catch(function () {
            logout();
            return null;
        });
    }

    window.HealerAuth = {
        getAccessToken: getAccessToken,
        getRefreshToken: getRefreshToken,
        getUser: getUser,
        isAdmin: isAdmin,
        isPractitioner: isPractitioner,
        refreshAccessToken: refreshAccessToken,
        logout: logout,
        checkAuth: checkAuth,
        getAuthHeaders: getAuthHeaders
    };
})();
