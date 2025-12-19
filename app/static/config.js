// config.js - Конфигурация приложения

// API конфигурация
export const API_BASE_URL = window.location.origin;

// Настройки пагинации
export const NEWS_PER_PAGE = 5;

// Настройки автодополнения
export const AUTOCOMPLETE_MIN_LENGTH = 2;
export const AUTOCOMPLETE_DEBOUNCE_MS = 300;

// DOM элементы
export const elements = {
    searchInput: document.getElementById('search'),
    btnSearch: document.querySelector('.btn-search'),
    resultsContainer: document.getElementById('results'),
    signalsContainer: document.getElementById('signals-container'),
    tagsCloud: document.getElementById('tags-cloud'),
    totalNews: document.getElementById('total-news'),
    totalTags: document.getElementById('total-tags'),
    totalSignals: document.getElementById('total-signals'),
    signalsCount: document.getElementById('signals-count'),
    updateTime: document.getElementById('update-time'),
    newsContainer: document.getElementById('news-container'),
    prevNewsBtn: document.getElementById('prev-news'),
    nextNewsBtn: document.getElementById('next-news'),
    currentPageSpan: document.getElementById('current-page'),
    totalPagesSpan: document.getElementById('total-pages'),
    newsCountSpan: document.getElementById('news-count'),
    themeToggle: document.getElementById('theme-toggle')
};

// Глобальное состояние приложения
export const state = {
    popularTagsCache: [],
    suggestionsContainer: null,
    debounceTimer: null,
    currentNewsPage: 1,
    totalNews: 0,
    isDarkTheme: false,
    lastSearchResults: null,
    lastSearchTag: '',
    lastSearchCount: 0
};
