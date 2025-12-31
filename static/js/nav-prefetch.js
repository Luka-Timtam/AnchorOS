(function() {
    'use strict';
    
    const PREFETCH_ROUTES = [
        '/',
        '/leads',
        '/clients',
        '/tasks',
        '/notes'
    ];
    
    const DEBOUNCE_MS = 150;
    const CACHE_TTL_MS = 60000;
    
    let prefetchCache = new Map();
    let currentPrefetch = null;
    let hoverTimeout = null;
    let lastInteractionTime = Date.now();
    
    function isPrefetchableRoute(href) {
        if (!href) return false;
        try {
            const url = new URL(href, window.location.origin);
            if (url.origin !== window.location.origin) return false;
            return PREFETCH_ROUTES.some(route => url.pathname === route);
        } catch (e) {
            return false;
        }
    }
    
    function isSlowNetwork() {
        if (!navigator.connection) return false;
        const conn = navigator.connection;
        if (conn.saveData) return true;
        const slowTypes = ['slow-2g', '2g'];
        if (slowTypes.includes(conn.effectiveType)) return true;
        return false;
    }
    
    function isUserIdle() {
        return (Date.now() - lastInteractionTime) < 5000;
    }
    
    function getCacheKey(href) {
        try {
            const url = new URL(href, window.location.origin);
            return url.pathname;
        } catch (e) {
            return href;
        }
    }
    
    function getCachedContent(href) {
        const key = getCacheKey(href);
        const cached = prefetchCache.get(key);
        if (!cached) return null;
        if (Date.now() - cached.timestamp > CACHE_TTL_MS) {
            prefetchCache.delete(key);
            return null;
        }
        return cached.content;
    }
    
    function setCachedContent(href, content) {
        const key = getCacheKey(href);
        prefetchCache.set(key, {
            content: content,
            timestamp: Date.now()
        });
    }
    
    function cancelCurrentPrefetch() {
        if (currentPrefetch) {
            if (currentPrefetch.controller) {
                currentPrefetch.controller.abort();
            }
            currentPrefetch = null;
        }
    }
    
    function prefetchRoute(href) {
        if (isSlowNetwork()) return;
        if (getCachedContent(href)) return;
        if (currentPrefetch && currentPrefetch.href === href) return;
        
        cancelCurrentPrefetch();
        
        const controller = new AbortController();
        currentPrefetch = { href: href, controller: controller };
        
        fetch(href, {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            signal: controller.signal,
            credentials: 'same-origin'
        })
        .then(function(response) {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.text();
        })
        .then(function(html) {
            setCachedContent(href, html);
            currentPrefetch = null;
        })
        .catch(function(err) {
            if (err.name !== 'AbortError') {
                console.debug('[Prefetch] Failed:', href, err.message);
            }
            currentPrefetch = null;
        });
    }
    
    function handleNavHover(e) {
        const link = e.target.closest('a.sidebar-item');
        if (!link) return;
        
        const href = link.getAttribute('href');
        if (!isPrefetchableRoute(href)) return;
        if (!isUserIdle()) return;
        
        if (hoverTimeout) clearTimeout(hoverTimeout);
        
        hoverTimeout = setTimeout(function() {
            prefetchRoute(href);
        }, DEBOUNCE_MS);
    }
    
    function handleNavLeave(e) {
        const link = e.target.closest('a.sidebar-item');
        if (!link) return;
        
        if (hoverTimeout) {
            clearTimeout(hoverTimeout);
            hoverTimeout = null;
        }
    }
    
    function trackUserActivity() {
        lastInteractionTime = Date.now();
    }
    
    function hookIntoSwup() {
        if (typeof Swup === 'undefined') return;
        
        const originalFetchPage = Swup.prototype.fetchPage;
        if (!originalFetchPage) return;
        
        Swup.prototype.fetchPage = function(url) {
            const cached = getCachedContent(url);
            if (cached) {
                console.debug('[Prefetch] Using cached content for:', url);
                return Promise.resolve({
                    url: url,
                    html: cached
                });
            }
            return originalFetchPage.apply(this, arguments);
        };
    }
    
    function init() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;
        
        sidebar.addEventListener('mouseenter', handleNavHover, true);
        sidebar.addEventListener('mouseleave', handleNavLeave, true);
        
        ['mousemove', 'keydown', 'scroll', 'touchstart'].forEach(function(event) {
            document.addEventListener(event, trackUserActivity, { passive: true });
        });
        
        hookIntoSwup();
        
        console.debug('[Prefetch] Navigation prefetching initialized');
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    window.navPrefetch = {
        clearCache: function() {
            prefetchCache.clear();
        },
        getCacheSize: function() {
            return prefetchCache.size;
        }
    };
})();
