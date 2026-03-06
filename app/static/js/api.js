/**
 * Healer Nexus — спільний API wrapper для дашборду.
 * Залежить від auth.js (window.HealerAuth).
 * Підключення (після auth.js): <script src="/static/js/api.js"></script>
 * Використання: HealerAPI.get('/api/...'), HealerAPI.post('/api/...', { ... }), тощо.
 */
(function () {
    'use strict';

    function apiRequest(url, options) {
        options = options || {};
        var headers = Object.assign({}, window.HealerAuth.getAuthHeaders(), options.headers || {});

        function doFetch(useHeaders) {
            return fetch(url, Object.assign({}, options, { headers: useHeaders || headers }));
        }

        return doFetch().then(function (response) {
            if (response.status === 401) {
                return window.HealerAuth.refreshAccessToken().then(function (newToken) {
                    if (!newToken) return null;
                    var newHeaders = Object.assign({}, window.HealerAuth.getAuthHeaders(), options.headers || {});
                    return doFetch(newHeaders);
                });
            }
            return response;
        }).then(function (response) {
            if (!response) return null;
            if (response.status === 401) {
                window.HealerAuth.logout();
                return null;
            }
            if (!response.ok) {
                throw new Error(response.status + ' ' + (response.statusText || ''));
            }
            return response.json();
        });
    }

    function get(url) {
        return apiRequest(url, { method: 'GET' });
    }

    function post(url, data) {
        return apiRequest(url, { method: 'POST', body: JSON.stringify(data || {}) });
    }

    function put(url, data) {
        return apiRequest(url, { method: 'PUT', body: JSON.stringify(data || {}) });
    }

    function del(url) {
        return apiRequest(url, { method: 'DELETE' });
    }

    window.HealerAPI = {
        apiRequest: apiRequest,
        get: get,
        post: post,
        put: put,
        del: del
    };
})();
