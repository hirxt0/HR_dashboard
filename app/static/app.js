// app.js
// Конфигурация
const API_BASE_URL = window.location.origin;

// DOM элементы
const elements = {
    searchInput: document.getElementById('search'),
    btnSearch: document.querySelector('.btn-search'),
    resultsContainer: document.getElementById('results'),
    signalsContainer: document.getElementById('signals-container'),
    tagsCloud: document.getElementById('tags-cloud'),
    totalNews: document.getElementById('total-news'),
    totalTags: document.getElementById('total-tags'),
    totalSignals: document.getElementById('total-signals'),
    signalsCount: document.getElementById('signals-count'),
    updateTime: document.getElementById('update-time')
};

// Кэш для популярных тегов
let popularTagsCache = [];
let suggestionsContainer = null;
let debounceTimer = null;

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTagsCloud();
    loadRecentNews();
    setupEventListeners();
    
    // Закрытие автодополнения при клике вне
    document.addEventListener('click', function(e) {
        if (suggestionsContainer && 
            !suggestionsContainer.contains(e.target) && 
            e.target !== elements.searchInput) {
            hideSuggestions();
        }
    });
});

// Настройка обработчиков событий
function setupEventListeners() {
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
    elements.searchInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        
        if (this.value.trim().length === 0) {
            hideSuggestions();
            return;
        }
        
        // Debounce для избежания слишком частых запросов
        debounceTimer = setTimeout(() => {
            if (this.value.length >= 2) {
                suggestTags(this.value);
            }
        }, 300);
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
            const tag = e.target.textContent;
            elements.searchInput.value = tag;
            hideSuggestions();
            runSearch(tag);
        }
    });
}

// Автодополнение и предложение тегов
async function suggestTags(input) {
    if (input.trim().length < 2) {
        hideSuggestions();
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/tags/suggest?q=${encodeURIComponent(input)}`);
        const data = await response.json();
        
        if (data.suggestions && data.suggestions.length > 0) {
            showSuggestions(data.suggestions, input);
        } else {
            hideSuggestions();
        }
    } catch (error) {
        console.error('Ошибка получения подсказок:', error);
        hideSuggestions();
    }
}

// Показать предложения
function showSuggestions(suggestions, input) {
    // Убираем старое автодополнение
    hideSuggestions();
    
    // Создаем контейнер для подсказок
    suggestionsContainer = document.createElement('div');
    suggestionsContainer.className = 'suggestions-container';
    
    // Позиционируем под полем ввода
    const inputRect = elements.searchInput.getBoundingClientRect();
    suggestionsContainer.style.position = 'absolute';
    suggestionsContainer.style.top = `${inputRect.bottom + window.scrollY + 5}px`;
    suggestionsContainer.style.left = `${inputRect.left + window.scrollX}px`;
    suggestionsContainer.style.width = `${inputRect.width}px`;
    suggestionsContainer.style.zIndex = '1000';
    
    // Добавляем каждую подсказку
    suggestions.forEach((suggestion, index) => {
        const suggestionEl = document.createElement('div');
        suggestionEl.className = 'suggestion-item';
        suggestionEl.dataset.tag = suggestion.tag;
        
        // Выделяем точные совпадения
        const isExact = suggestion.is_exact;
        const similarity = Math.round(suggestion.similarity * 100);
        
        suggestionEl.innerHTML = `
            <div class="suggestion-content">
                <span class="suggestion-tag ${isExact ? 'exact-match' : ''}">
                    ${suggestion.tag}
                </span>
                <span class="suggestion-meta">
                    ${suggestion.count ? `${suggestion.count} упоминаний` : ''}
                    ${!isExact && similarity > 60 ? `<span class="similarity">${similarity}% совпадение</span>` : ''}
                </span>
            </div>
            ${isExact ? '<i class="fas fa-check exact-icon"></i>' : '<i class="fas fa-arrow-right"></i>'}
        `;
        
        // Обработчик клика
        suggestionEl.addEventListener('click', () => {
            elements.searchInput.value = suggestion.tag;
            hideSuggestions();
            runSearch(suggestion.tag);
        });
        
        // Обработчик наведения
        suggestionEl.addEventListener('mouseenter', () => {
            suggestionEl.classList.add('hovered');
        });
        
        suggestionEl.addEventListener('mouseleave', () => {
            suggestionEl.classList.remove('hovered');
        });
        
        suggestionsContainer.appendChild(suggestionEl);
    });
    
    // Добавляем контейнер в DOM
    document.body.appendChild(suggestionsContainer);
}

// Скрыть предложения
function hideSuggestions() {
    if (suggestionsContainer) {
        suggestionsContainer.remove();
        suggestionsContainer = null;
    }
}

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const data = await response.json();
        
        // Обновляем статистику
        elements.totalNews.textContent = data.total_news;
        elements.totalTags.textContent = data.unique_tags;
        elements.totalSignals.textContent = data.total_signals;
        elements.signalsCount.textContent = data.signals.length;
        elements.updateTime.textContent = data.update_time;
        
        // Отображаем сигналы
        displaySignals(data.signals);
        
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        showError('Не удалось загрузить статистику');
    }
}

// Загрузка облака тегов
async function loadTagsCloud() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const data = await response.json();
        
        // Сохраняем популярные теги в кэш
        popularTagsCache = data.popular_tags || [];
        
        // Очищаем облако тегов
        elements.tagsCloud.innerHTML = '';
        
        // Добавляем теги
        data.popular_tags.forEach(tagData => {
            const tagElement = document.createElement('div');
            tagElement.className = 'tag-cloud';
            tagElement.textContent = tagData.tag;
            tagElement.title = `Упоминаний: ${tagData.count}`;
            elements.tagsCloud.appendChild(tagElement);
        });
        
    } catch (error) {
        console.error('Ошибка загрузки тегов:', error);
        elements.tagsCloud.innerHTML = '<div class="loading">Ошибка загрузки тегов</div>';
    }
}

// Загрузка последних новостей
async function loadRecentNews() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/news?limit=5`);
        const data = await response.json();
        
        if (data.news && data.news.length > 0) {
            displayNews(data.news);
        }
        
    } catch (error) {
        console.error('Ошибка загрузки новостей:', error);
    }
}

// Отображение сигналов
function displaySignals(signals) {
    if (!signals || signals.length === 0) {
        elements.signalsContainer.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-info-circle"></i>
                <h3>Нет активных сигналов</h3>
                <p>Данные еще не обработаны</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    signals.forEach(signal => {
        const typeClass = signal.type;
        const icon = signal.icon || 'fas fa-exclamation-circle';
        const trendIcon = signal.trend === 'up' ? 'fas fa-arrow-up' : 
                         signal.trend === 'down' ? 'fas fa-arrow-down' : 
                         'fas fa-minus';
        const trendColor = signal.trend === 'up' ? 'color: var(--success);' : 
                          signal.trend === 'down' ? 'color: var(--danger);' : 
                          'color: var(--gray);';
        
        html += `
            <div class="signal-item ${typeClass}">
                <div class="signal-header">
                    <div class="signal-tag">
                        <i class="${icon}"></i> ${signal.title}
                    </div>
                    <span class="signal-type ${typeClass}">${typeClass === 'problem' ? 'Проблема' : 
                                                           typeClass === 'opportunity' ? 'Возможность' : 
                                                           'Ранний тренд'}</span>
                </div>
                <p>${signal.description}</p>
                <div class="signal-stats">
                    <div class="stat">
                        <i class="fas fa-eye"></i>
                        <span>${signal.mentions} упоминаний</span>
                    </div>
                    <div class="stat">
                        <i class="fas fa-chart-line" style="${trendColor}"></i>
                        <span>Тренд: ${signal.trend === 'up' ? 'растет' : 
                                     signal.trend === 'down' ? 'падает' : 
                                     'стабилен'}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    elements.signalsContainer.innerHTML = html;
}

// Выполнение поиска
async function runSearch(tag = null) {
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
        
        displayResults(data.results, data.corrected_tag || searchTag, data.count);
        
    } catch (error) {
        console.error('Ошибка поиска:', error);
        showError('Ошибка при выполнении поиска');
    }
}

// Отображение результатов поиска
function displayResults(results, searchTag, count) {
    if (!results || results.length === 0) {
        elements.resultsContainer.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-search"></i>
                <h3>Ничего не найдено</h3>
                <p>По тегу "${searchTag}" не найдено ни одной записи</p>
                <p class="hint">Попробуйте другой тег или проверьте написание</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="search-info">
            <h3>Найдено результатов: ${count}</h3>
            <p>По тегу: <span class="search-tag">${searchTag}</span></p>
        </div>
    `;
    
    results.forEach(item => {
        // Определяем иконку настроения
        let sentimentIcon = 'fas fa-meh';
        let sentimentColor = 'var(--gray)';
        
        if (item.sentiment === 'positive') {
            sentimentIcon = 'fas fa-smile';
            sentimentColor = 'var(--success)';
        } else if (item.sentiment === 'negative') {
            sentimentIcon = 'fas fa-frown';
            sentimentColor = 'var(--danger)';
        }
        
        // Форматируем дату
        const date = item.metadata?.date || item.created_at?.substring(0, 10) || 'Неизвестно';
        
        html += `
            <div class="news-item">
                <div class="news-header">
                    <div class="channel">
                        <i class="${sentimentIcon}" style="color: ${sentimentColor};"></i>
                        <span>${item.metadata?.source || 'Источник'}</span>
                    </div>
                    <div class="date">${date}</div>
                </div>
                <div class="news-text">
                    ${item.text}
                </div>
                ${item.explanation ? `<p class="hint" style="margin-bottom: 10px;"><i>${item.explanation}</i></p>` : ''}
                <div class="news-tags">
                    ${item.llm_tags.map(tag => `
                        <span class="tag ${tag.toLowerCase() === searchTag.toLowerCase() ? 'tag-highlight' : ''}">
                            ${tag}
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    });
    
    elements.resultsContainer.innerHTML = html;
}

// Отображение новостей
function displayNews(newsItems) {
    if (!newsItems || newsItems.length === 0) return;
    
    // Можно добавить отображение новостей в какой-то другой раздел
    console.log('Загружены новости:', newsItems);
}

// Показать сообщение об ошибке
function showError(message) {
    elements.resultsContainer.innerHTML = `
        <div class="placeholder">
            <i class="fas fa-exclamation-triangle" style="color: var(--danger);"></i>
            <h3>Ошибка</h3>
            <p>${message}</p>
        </div>
    `;
}

// Показать информационное сообщение
function showMessage(message, type = 'info') {
    const icon = type === 'warning' ? 'fas fa-exclamation-triangle' : 'fas fa-info-circle';
    const color = type === 'warning' ? 'var(--warning)' : 'var(--info)';
    
    elements.resultsContainer.innerHTML = `
        <div class="placeholder" style="margin-bottom: 20px;">
            <i class="${icon}" style="color: ${color};"></i>
            <p>${message}</p>
        </div>
    `;
}