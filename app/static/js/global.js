// static/js/global.js

// --- Simple Toast Notification System ---
function showToast(message, duration = 3000, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '10000';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '0.5rem';
        document.body.appendChild(container);
    }

    const toastElement = document.createElement('div');
    toastElement.textContent = message;
    toastElement.style.transition = 'opacity 0.3s ease-out'; // Apply transition before append for show class
    
    // Set base styles, then type-specific overrides
    toastElement.style.color = 'white';
    toastElement.style.padding = '10px 15px';
    toastElement.style.borderRadius = '5px';
    toastElement.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
    toastElement.style.fontSize = '0.875rem';
    
    if (type === 'success') {
        toastElement.style.backgroundColor = '#10b981';
    } else if (type === 'error') {
        toastElement.style.backgroundColor = '#ef4444';
    } else if (type === 'info') {
        toastElement.style.backgroundColor = '#3b82f6';
    } else {
        toastElement.style.backgroundColor = '#333'; // Default
    }
    
    container.appendChild(toastElement);
    
    // Force reflow for transition to apply on add
    // We set opacity to 0 initially, then to 1 to trigger fade-in
    toastElement.style.opacity = '0'; 
    requestAnimationFrame(() => { // Ensures opacity is applied after element is in DOM
        toastElement.style.opacity = '1';
    });

    setTimeout(() => {
        toastElement.style.opacity = '0';
        setTimeout(() => {
          toastElement.remove();
        }, 300); 
    }, duration);
}

// --- MAIN DOMContentLoaded ---
document.addEventListener('DOMContentLoaded', () => {
    // --- Initialize Lucide Icons ---
    try {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        } else {
            console.warn("Lucide library not found. Icons will not be rendered.");
        }
    } catch (e) {
        console.error("Error initializing Lucide icons:", e);
    }

    // --- Sidebar Toggle Functionality ---
    const sidebar = document.getElementById('sidebar');
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const sidebarCloseButton = document.getElementById('sidebar-close-button'); 
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    function openMobileMenu() {
        if (sidebar && sidebarOverlay) {
            sidebar.classList.remove('-translate-x-full');
            sidebar.classList.add('translate-x-0');
            sidebarOverlay.classList.remove('hidden');
            document.body.classList.add('overflow-hidden', 'md:overflow-auto');
        }
    }

    function closeMobileMenu() {
        if (sidebar && sidebarOverlay) {
            sidebar.classList.add('-translate-x-full');
            sidebar.classList.remove('translate-x-0');
            sidebarOverlay.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        }
    }

    if (mobileMenuButton) mobileMenuButton.addEventListener('click', openMobileMenu);
    if (sidebarCloseButton) sidebarCloseButton.addEventListener('click', closeMobileMenu);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeMobileMenu);

    document.querySelectorAll('#sidebar nav a').forEach(link => {
        link.addEventListener('click', (e) => { // Added 'e' parameter
            if (window.innerWidth < 768) {
                // If it's a link to a new page (not an anchor on the same page)
                if (link.getAttribute('href') && !link.getAttribute('href').startsWith('#')) {
                    closeMobileMenu();
                }
            }
        });
    });
    
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 768) {
            document.body.classList.remove('overflow-hidden');
            if (sidebarOverlay && !sidebarOverlay.classList.contains('hidden')) {
                sidebarOverlay.classList.add('hidden');
            }
        } else {
            if (sidebar && sidebar.classList.contains('translate-x-0') && !sidebar.classList.contains('-translate-x-full')) {
                if (!document.body.classList.contains('overflow-hidden')) {
                     document.body.classList.add('overflow-hidden', 'md:overflow-auto');
                }
            }
        }
    });

    // --- Theme Toggle ---
    const themeToggleButtonHeader = document.getElementById('theme-toggle-header'); 
    
    function updateThemeIcon() {
        if (themeToggleButtonHeader) { 
            if (document.documentElement.classList.contains('dark')) {
                themeToggleButtonHeader.innerHTML = '<i data-lucide="sun" class="w-5 h-5"></i>';
            } else {
                themeToggleButtonHeader.innerHTML = '<i data-lucide="moon" class="w-5 h-5"></i>';
            }
            if (typeof lucide !== 'undefined') lucide.createIcons({nodes: [themeToggleButtonHeader]}); // Target specific node
        }
    }

    // Set initial theme
    if (localStorage.getItem('theme') === 'dark' || 
        (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    updateThemeIcon(); 

    if (themeToggleButtonHeader) {
        themeToggleButtonHeader.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark');
            localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
            updateThemeIcon();
            // Dispatch a custom event that pages can listen to if they need to react (e.g., redraw charts)
            window.dispatchEvent(new CustomEvent('themeChangedGlobal')); 
        });
    } else {
        console.warn("Theme toggle button #theme-toggle-header not found.");
    }

    // --- User Info Display ---
    function updateGlobalUserInfoDisplay() {
        const storedUsername = localStorage.getItem('username');
        
        const commonUserDisplayElements = [
            { id: 'userDisplayNameHeader', default: 'User' },
            { id: 'userDisplayNameRightSidebar', default: 'User' }, // For pages that have this
            // Add other common user display elements if any
        ];

        commonUserDisplayElements.forEach(item => {
            const el = document.getElementById(item.id);
            if (el) {
                el.textContent = storedUsername || item.default;
            }
        });
        // You might have more specific role displays on header vs sidebar, handle them if needed
        const headerUserRoleEl = document.getElementById('headerUserRoleDisplay');
        if (headerUserRoleEl) headerUserRoleEl.textContent = "Role"; // Or fetch actual role

        const rightSidebarUserRoleEl = document.getElementById('userRoleDisplayRightSidebar');
        if (rightSidebarUserRoleEl) rightSidebarUserRoleEl.textContent = "Analyst"; // Or fetch actual role
    }
    updateGlobalUserInfoDisplay();

    // --- Global Logout Button Functionality ---
    const logoutButton = document.getElementById('global-logout-btn');
    const LOGIN_PAGE_URL = "/"; // **** CRITICAL: VERIFY THIS PATH ****
                               // Examples: "/", "/login.html", "/static/login.html"

    if (logoutButton) {
        logoutButton.addEventListener('click', (e) => { 
            e.preventDefault(); 
            console.log("Global logout clicked from page:", window.location.pathname); 
            
            try {
                localStorage.removeItem('accessToken'); 
                localStorage.removeItem('refreshToken'); 
                localStorage.removeItem('username');     
                localStorage.removeItem('user_id');      
                localStorage.removeItem('user_status');  
                
                showToast("Logged out successfully. Redirecting...", 1500, "success"); 
                
                // Using a try-catch around the redirect in case of very unusual browser issues,
                // though unlikely to be the cause.
                setTimeout(() => {
                    try {
                        console.log(`Redirecting to: ${LOGIN_PAGE_URL}`);
                        window.location.href = LOGIN_PAGE_URL; 
                    } catch (redirectError) {
                        console.error("Error during redirection:", redirectError);
                        alert("Logout successful, but redirection failed. Please navigate to the login page manually.");
                    }
                }, 1500); 

            } catch (error) {
                console.error("Error during logout process:", error);
                alert("An error occurred during logout. Please try again.");
            }
        });
    } else {
        console.warn("Logout button with ID 'global-logout-btn' not found on this page.");
    }

}); // End of DOMContentLoaded


allPannes = Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : []);