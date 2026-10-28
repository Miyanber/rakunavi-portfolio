// 基本、スクリプトは小さく割って必要なときimportする方針
// →スクリプト評価時間が低下しパフォーマンス向上
import { setUpDarkTheme } from './theme.js';
import { initModal } from './modal.js';
import { setUpSideMenu } from './side_menu.js';

document.addEventListener('DOMContentLoaded', () => {
    setUpDarkTheme();
    initModal();
    setUpSideMenu();
    const elements = document.querySelectorAll(".fade-in");

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("show");
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    elements.forEach(el => observer.observe(el));
    const cleanUrl = window.location.origin + window.location.pathname + window.location.hash;
    window.history.replaceState({}, document.title, cleanUrl);
});

