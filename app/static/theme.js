// theme.js - Управление темой приложения

import { elements, state } from './config.js';
import { displayResults } from './ui.js';
import { loadRecentNews } from './api.js';

/**
 * Инициализация темы при загрузке
 */
export function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    state.isDarkTheme = savedTheme === 'dark';
    
    elements.themeToggle.checked = state.isDarkTheme;
    setTheme(state.isDarkTheme);
}

/**
 * Установка темы
 */
export function setTheme(isDark) {
    state.isDarkTheme = isDark;
    
    if (isDark) {
        document.body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
    } else {
        document.body.classList.remove('dark-theme');
        localStorage.setItem('theme', 'light');
    }
    
    // Обновляем цвет текста в поле поиска
    updateSearchInputTheme();
    
    // Перерисовываем результаты поиска, если они есть
    if (state.lastSearchResults && state.lastSearchResults.length > 0) {
        displayResults(state.lastSearchResults, state.lastSearchTag, state.lastSearchCount);
    }
    
    // Перерисовываем новости
    if (state.currentNewsPage) {
        loadRecentNews(state.currentNewsPage);
    }
}

/**
 * Обновление цвета текста в поле поиска
 */
function updateSearchInputTheme() {
    if (state.isDarkTheme) {
        elements.searchInput.style.color = '#ffffff';
        elements.searchInput.style.setProperty('--placeholder-color', '#666666');
    } else {
        elements.searchInput.style.color = '#333333';
        elements.searchInput.style.setProperty('--placeholder-color', '#757575');
    }
}

/**
 * Получить цвет настроения для новостей
 */
export function getNewsSentimentColor(sentiment) {
    if (sentiment === 'positive') {
        return state.isDarkTheme ? 'var(--sber-green)' : 'var(--success)';
    } else if (sentiment === 'negative') {
        return 'var(--danger)';
    } else if (sentiment === 'neutral') {
        return state.isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)';
    }
    return state.isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)';
}

/**
 * Получить цвет настроения для результатов поиска
 */
export function getResultSentimentColor(sentiment) {
    if (sentiment === 'positive') {
        return state.isDarkTheme ? 'var(--sber-green)' : 'var(--success)';
    } else if (sentiment === 'negative') {
        return 'var(--danger)';
    } else if (sentiment === 'neutral') {
        return state.isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)';
    }
    return state.isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)';
}

/**
 * Получить цвета для текущей темы
 */
export function getThemeColors() {
    return {
        backgroundColor: state.isDarkTheme ? 'var(--dark-card)' : 'white',
        textColor: state.isDarkTheme ? 'var(--dark-text)' : 'var(--dark)',
        borderColor: state.isDarkTheme ? 'var(--dark-border)' : 'var(--light-gray)',
        infoColor: state.isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)',
        shadowOpacity: state.isDarkTheme ? '0.2' : '0.05'
    };
}
