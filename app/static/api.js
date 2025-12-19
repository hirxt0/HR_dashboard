// api.js - Все API запросы

import { API_BASE_URL, NEWS_PER_PAGE, elements, state } from './config.js';
import { 
    displaySignals, 
    displayNews, 
    displayResults,
    showError,
    showMessage,
    updatePaginationControls 
} from './ui.js';

/**
 * Загрузка статистики
 */
export async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const data = await response.json();
        
        // Обновляем статистику
        elements.totalNews.textContent = data.total_news.toLocaleString();
        elements.totalTags.textContent = data.unique_tags.toLocaleString();
        elements.totalSignals.textContent = data.total_signals.toLocaleString();
        elements.signalsCount.textContent = data.signals.length;
        elements.updateTime.textContent = data.update_time;
        
        // Обновляем общее количество новостей для пагинации
        state.totalNews = data.total_news;
        elements.newsCountSpan.textContent = state.totalNews.toLocaleString();
        
        // Отображаем сигналы
        displaySignals(data.signals);
        
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        showError('Не удалось загрузить статистику');
    }
}

/**
 * Загрузка облака тегов
 */
export async function loadTagsCloud() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const data = await response.json();
        
        // Сохраняем популярные теги в кэш
        state.popularTagsCache = data.popular_tags || [];
        
        // Очищаем облако тегов
        elements.tagsCloud.innerHTML = '';
        
        // Добавляем теги
        data.popular_tags.forEach(tagData => {
            const tagElement = document.createElement('div');
            tagElement.className = 'tag-cloud';
            tagElement.textContent = tagData.tag;
            tagElement.title = `Упоминаний: ${tagData.count}`;
            
            // Добавляем счетчик использования
            const countBadge = document.createElement('span');
            countBadge.className = 'tag-count';
            countBadge.textContent = tagData.count;
            tagElement.appendChild(countBadge);
            
            elements.tagsCloud.appendChild(tagElement);
        });
        
    } catch (error) {
        console.error('Ошибка загрузки тегов:', error);
        elements.tagsCloud.innerHTML = '<div class="loading">Ошибка загрузки тегов</div>';
    }
}

/**
 * Загрузка последних новостей с пагинацией
 */
export async function loadRecentNews(page = 1) {
    try {
        const offset = (page - 1) * NEWS_PER_PAGE;
        elements.newsContainer.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Загрузка новостей...</p>
            </div>
        `;
        
        const response = await fetch(`${API_BASE_URL}/api/news?limit=${NEWS_PER_PAGE}&offset=${offset}`);
        const data = await response.json();
        
        if (data.news && data.news.length > 0) {
            displayNews(data.news);
            updatePaginationControls(page, data.total);
        } else {
            elements.newsContainer.innerHTML = `
                <div class="placeholder">
                    <i class="fas fa-newspaper"></i>
                    <h3>Новостей пока нет</h3>
                    <p>База данных пуста или произошла ошибка</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Ошибка загрузки новостей:', error);
        elements.newsContainer.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Ошибка загрузки</h3>
                <p>Не удалось загрузить новости</p>
            </div>
        `;
    }
}

/**
 * Автодополнение и предложение тегов
 */
export async function suggestTags(input) {
    if (input.trim().length < 2) {
        return null;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/tags/suggest?q=${encodeURIComponent(input)}`);
        const data = await response.json();
        
        if (data.suggestions && data.suggestions.length > 0) {
            return data.suggestions;
        }
        return null;
        
    } catch (error) {
        console.error('Ошибка получения подсказок:', error);
        return null;
    }
}

/**
 * Выполнение поиска
 */
export async function runSearch(tag = null) {
    const searchTag = tag || elements.searchInput.value.trim();
    
    if (!searchTag) {
        showMessage('Введите тег для поиска', 'warning');
        return;
    }
    
    // Показываем индикатор загрузки
    elements.resultsContainer.innerHTML = `
        <div class="loading">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Поиск по тегу: "${searchTag}"...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/search?tag=${encodeURIComponent(searchTag)}&smart=true`);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Показываем подсказку, если был исправлен тег
        if (data.was_corrected && data.corrected_tag !== searchTag.toLowerCase()) {
            showMessage(`Показаны результаты для тега: <strong>"${data.corrected_tag}"</strong> (исправлено с "${searchTag}")`, 'info');
        }
        
        // Сохраняем результаты для перерисовки при смене темы
        state.lastSearchResults = data.results;
        state.lastSearchTag = data.corrected_tag || searchTag;
        state.lastSearchCount = data.count;
        
        displayResults(data.results, state.lastSearchTag, state.lastSearchCount);
        
    } catch (error) {
        console.error('Ошибка поиска:', error);
        showError('Ошибка при выполнении поиска');
    }
}
