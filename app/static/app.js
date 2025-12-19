// main.js - Главный файл приложения (точка входа)

import { AUTOCOMPLETE_MIN_LENGTH, AUTOCOMPLETE_DEBOUNCE_MS, elements, state } from './config.js';
import { initTheme, setTheme } from './theme.js';
import { loadStats, loadTagsCloud, loadRecentNews, suggestTags, runSearch } from './api.js';
import { showSuggestions, hideSuggestions } from './ui.js';

/**
 * Настройка обработчиков событий
 */
function setupEventListeners() {
    // Переключение темы
    elements.themeToggle.addEventListener('change', function() {
        setTheme(this.checked);
    });
    
    // Поиск по Enter
    elements.searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            hideSuggestions();
            runSearch();
        }
    });
    
    // Поиск по клику
    elements.btnSearch.addEventListener('click', function() {
        hideSuggestions();
        runSearch();
    });
    
    // Автодополнение с debounce
    elements.searchInput.addEventListener('input', async function(e) {
        clearTimeout(state.debounceTimer);
        
        if (this.value.trim().length === 0) {
            hideSuggestions();
            return;
        }
        
        // Debounce для избежания слишком частых запросов
        state.debounceTimer = setTimeout(async () => {
            if (this.value.length >= AUTOCOMPLETE_MIN_LENGTH) {
                const suggestions = await suggestTags(this.value);
                if (suggestions) {
                    showSuggestions(suggestions, this.value);
                } else {
                    hideSuggestions();
                }
            }
        }, AUTOCOMPLETE_DEBOUNCE_MS);
    });
    
    // Закрытие автодополнения при нажатии Escape
    elements.searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hideSuggestions();
        }
    });
    
    // Быстрый поиск по тегам в облаке
    elements.tagsCloud.addEventListener('click', function(e) {
        if (e.target.classList.contains('tag-cloud')) {
            const tag = e.target.textContent.replace(/\s*\(\d+\)$/, '');
            elements.searchInput.value = tag;
            hideSuggestions();
            runSearch(tag);
        }
    });
    
    // Пагинация новостей
    elements.prevNewsBtn.addEventListener('click', function() {
        if (state.currentNewsPage > 1) {
            state.currentNewsPage--;
            loadRecentNews(state.currentNewsPage);
        }
    });
    
    elements.nextNewsBtn.addEventListener('click', function() {
        const totalPages = Math.ceil(state.totalNews / 5);
        if (state.currentNewsPage < totalPages) {
            state.currentNewsPage++;
            loadRecentNews(state.currentNewsPage);
        }
    });
    
    // Закрытие автодополнения при клике вне
    document.addEventListener('click', function(e) {
        if (state.suggestionsContainer && 
            !state.suggestionsContainer.contains(e.target) && 
            e.target !== elements.searchInput) {
            hideSuggestions();
        }
    });
}

/**
 * Инициализация приложения
 */
function initApp() {
    initTheme();
    loadStats();
    loadTagsCloud();
    loadRecentNews(state.currentNewsPage);
    setupEventListeners();
}

// Запуск приложения при загрузке DOM
document.addEventListener('DOMContentLoaded', initApp);

// Экспортируем runSearch глобально для onclick в HTML
window.runSearchGlobal = runSearch;
