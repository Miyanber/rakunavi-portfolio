export function setUpSideMenu() {
    const menu = document.getElementById('side-menu');
    const overlay = document.getElementById('side-menu-overlay');
    const toggleButton = document.getElementById('side-menu-toggle');
    const closeButton = document.getElementById('side-menu-close');
    const toggleIcon = toggleButton?.querySelector('.material-symbols-rounded');

    const updateToggleState = (isOpen) => {
        if (!toggleButton || !toggleIcon) return;
        toggleButton.classList.toggle('open', isOpen);
        toggleButton.setAttribute('aria-expanded', String(isOpen));
        toggleButton.setAttribute('aria-label', isOpen ? 'メニューを閉じる' : 'メニューを開く');
        toggleIcon.textContent = isOpen ? 'close' : 'menu';
    };

    const openMenu = () => {
        if (!menu || !overlay) return;
        menu.classList.add('open');
        menu.setAttribute('aria-hidden', 'false');
        overlay.classList.add('active');
        updateToggleState(true);
    };

    const closeMenu = () => {
        if (!menu || !overlay) return;
        menu.classList.remove('open');
        menu.setAttribute('aria-hidden', 'true');
        overlay.classList.remove('active');
        updateToggleState(false);
    };

    const toggleMenu = () => {
        if (!menu?.classList.contains('open')) {
            openMenu();
        } else {
            closeMenu();
        }
    };

    toggleButton?.addEventListener('click', toggleMenu);
    closeButton?.addEventListener('click', closeMenu);
    overlay?.addEventListener('click', closeMenu);

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });

    updateToggleState(false);
}
