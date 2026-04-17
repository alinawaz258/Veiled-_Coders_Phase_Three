(function () {
    const body = document.body;
    if (!body) return;

    const role = body.getAttribute('data-role');
    if (!role) return;

    const token = sessionStorage.getItem('authToken');
    const portalRole = sessionStorage.getItem('portalRole');
    const page = window.location.pathname.split('/').pop() || 'index.html';

    const requiresMatch = role !== 'any';
    const missingAuth = !token || !portalRole;
    const wrongRole = requiresMatch && portalRole !== role;

    if (missingAuth || wrongRole) {
        window.location.href = `portal.html?redirect=${encodeURIComponent(page)}`;
    }
})();

window.logoutUser = function () {
    sessionStorage.removeItem('portalRole');
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('riderName');
    sessionStorage.removeItem('driver_id');
    sessionStorage.removeItem('adminEmail');
    window.location.href = 'portal.html';
};

// ── Element-level RBAC: hide elements based on data-rbac attribute ──
document.addEventListener('DOMContentLoaded', function () {
    var portalRole = sessionStorage.getItem('portalRole');
    document.querySelectorAll('[data-rbac]').forEach(function (el) {
        var allowedRoles = el.getAttribute('data-rbac').split(',').map(function (r) { return r.trim(); });
        if (!portalRole || !allowedRoles.includes(portalRole)) {
            el.style.display = 'none';
        }
    });
});
