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
    updateTime: document.getElementById('update-time'),
    newsContainer: document.getElementById('news-container'),
    prevNewsBtn: document.getElementById('prev-news'),
    nextNewsBtn: document.getElementById('next-news'),
    currentPageSpan: document.getElementById('current-page'),
    totalPagesSpan: document.getElementById('total-pages'),
    newsCountSpan: document.getElementById('news-count'),
    themeToggle: document.getElementById('theme-toggle')
};

// Кэш для популярных тегов
let popularTagsCache = [];
let suggestionsContainer = null;
let debounceTimer = null;

// Пагинация новостей
let currentNewsPage = 1;
let newsPerPage = 5;
let totalNews = 0;

// Текущая тема
let isDarkTheme = false;

// Последние результаты поиска (для перерисовки при смене темы)
let lastSearchResults = null;
let lastSearchTag = '';
let lastSearchCount = 0;

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    loadStats();
    loadTagsCloud();
    loadRecentNews(currentNewsPage);
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

// Инициализация темы
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    isDarkTheme = savedTheme === 'dark';
    
    elements.themeToggle.checked = isDarkTheme;
    setTheme(isDarkTheme);
}

// Переключение темы
function setTheme(isDark) {
    isDarkTheme = isDark;
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
    if (lastSearchResults && lastSearchResults.length > 0) {
        displayResults(lastSearchResults, lastSearchTag, lastSearchCount);
    }
    
    // Перерисовываем новости
    if (currentNewsPage) {
        loadRecentNews(currentNewsPage);
    }
}

// Обновление цвета текста в поле поиска
function updateSearchInputTheme() {
    if (isDarkTheme) {
        elements.searchInput.style.color = '#ffffff';
        elements.searchInput.style.setProperty('--placeholder-color', '#666666');
    } else {
        elements.searchInput.style.color = '#333333';
        elements.searchInput.style.setProperty('--placeholder-color', '#757575');
    }
}

// Настройка обработчиков событий
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
            const tag = e.target.textContent.replace(/\s*\(\d+\)$/, ''); // Убираем счетчик
            elements.searchInput.value = tag;
            hideSuggestions();
            runSearch(tag);
        }
    });
    
    // Пагинация новостей
    elements.prevNewsBtn.addEventListener('click', function() {
        if (currentNewsPage > 1) {
            currentNewsPage--;
            loadRecentNews(currentNewsPage);
        }
    });
    
    elements.nextNewsBtn.addEventListener('click', function() {
        const totalPages = Math.ceil(totalNews / newsPerPage);
        if (currentNewsPage < totalPages) {
            currentNewsPage++;
            loadRecentNews(currentNewsPage);
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

// Показать предложения с учетом темы
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
    
    // Добавляем стили для темной темы
    if (isDarkTheme) {
        suggestionsContainer.style.background = 'var(--dark-card)';
        suggestionsContainer.style.border = '1px solid var(--dark-border)';
        suggestionsContainer.style.color = 'var(--dark-text)';
    }
    
    // Добавляем каждую подсказку
    suggestions.forEach((suggestion, index) => {
        const suggestionEl = document.createElement('div');
        suggestionEl.className = 'suggestion-item';
        suggestionEl.dataset.tag = suggestion.tag;
        
        // Выделяем точные совпадения
        const isExact = suggestion.is_exact;
        const similarity = Math.round(suggestion.similarity * 100);
        
        // Используем правильные цвета для темной темы
        const textColor = isDarkTheme ? 'var(--dark-text)' : 'var(--dark)';
        const exactColor = isDarkTheme ? 'var(--sber-green)' : 'var(--primary)';
        const metaColor = isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)';
        
        suggestionEl.innerHTML = `
            <div class="suggestion-content">
                <span class="suggestion-tag ${isExact ? 'exact-match' : ''}" style="color: ${isExact ? exactColor : textColor};">
                    ${suggestion.tag}
                </span>
                <span class="suggestion-meta" style="color: ${metaColor};">
                    ${suggestion.count ? `${suggestion.count} упоминаний` : ''}
                    ${!isExact && similarity > 60 ? `<span class="similarity">${similarity}% совпадение</span>` : ''}
                </span>
            </div>
            ${isExact ? `<i class="fas fa-check exact-icon" style="color: ${exactColor};"></i>` : `<i class="fas fa-arrow-right" style="color: ${metaColor};"></i>`}
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
            if (isDarkTheme) {
                suggestionEl.style.background = 'rgba(33, 160, 56, 0.1)';
            }
        });
        
        suggestionEl.addEventListener('mouseleave', () => {
            suggestionEl.classList.remove('hovered');
            if (isDarkTheme) {
                suggestionEl.style.background = '';
            }
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
        elements.totalNews.textContent = data.total_news.toLocaleString();
        elements.totalTags.textContent = data.unique_tags.toLocaleString();
        elements.totalSignals.textContent = data.total_signals.toLocaleString();
        elements.signalsCount.textContent = data.signals.length;
        elements.updateTime.textContent = data.update_time;
        
        // Обновляем общее количество новостей для пагинации
        totalNews = data.total_news;
        elements.newsCountSpan.textContent = totalNews.toLocaleString();
        
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

// Загрузка последних новостей с пагинацией
async function loadRecentNews(page = 1) {
    try {
        const offset = (page - 1) * newsPerPage;
        elements.newsContainer.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Загрузка новостей...</p>
            </div>
        `;
        
        const response = await fetch(`${API_BASE_URL}/api/news?limit=${newsPerPage}&offset=${offset}`);
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

// Обновление элементов пагинации
function updatePaginationControls(page, total) {
    const totalPages = Math.ceil(total / newsPerPage);
    
    elements.currentPageSpan.textContent = page;
    elements.totalPagesSpan.textContent = totalPages;
    
    // Обновляем состояние кнопок
    elements.prevNewsBtn.disabled = page <= 1;
    elements.nextNewsBtn.disabled = page >= totalPages;
    
    // Добавляем/убираем классы для стилизации disabled
    if (page <= 1) {
        elements.prevNewsBtn.classList.add('disabled');
    } else {
        elements.prevNewsBtn.classList.remove('disabled');
    }
    
    if (page >= totalPages) {
        elements.nextNewsBtn.classList.add('disabled');
    } else {
        elements.nextNewsBtn.classList.remove('disabled');
    }
}

// Отображение новостей
function displayNews(newsItems) {
    if (!newsItems || newsItems.length === 0) {
        elements.newsContainer.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-newspaper"></i>
                <h3>Новостей пока нет</h3>
                <p>Попробуйте обновить позже</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    newsItems.forEach(item => {
        // Определяем иконку настроения (исправлено - негативные смайлики красные)
        let sentimentIcon = 'fas fa-meh';
        let sentimentColor = 'var(--gray)';
        let sentimentText = 'Нейтрально';
        
        if (item.sentiment === 'positive') {
            sentimentIcon = 'fas fa-smile';
            sentimentColor = isDarkTheme ? 'var(--sber-green)' : 'var(--success)';
            sentimentText = 'Позитивно';
        } else if (item.sentiment === 'negative') {
            sentimentIcon = 'fas fa-frown';
            sentimentColor = 'var(--danger)'; // Всегда красный!
            sentimentText = 'Негативно';
        } else if (item.sentiment === 'neutral') {
            sentimentIcon = 'fas fa-meh';
            sentimentColor = 'var(--gray)';
            sentimentText = 'Нейтрально';
        }
        
        // Форматируем дату
        const date = item.date || item.created_at?.substring(0, 10) || 'Неизвестно';
        
        html += `
            <div class="news-item">
                <div class="news-header">
                    <div class="channel-info">
                        <div class="channel">
                            <i class="fas fa-newspaper"></i>
                            <span>${item.channel || 'Источник'}</span>
                        </div>
                        <div class="sentiment-badge" style="background: ${sentimentColor}20; color: ${sentimentColor};">
                            <i class="${sentimentIcon}"></i>
                            <span>${sentimentText}</span>
                        </div>
                    </div>
                    <div class="date">${date}</div>
                </div>
                <div class="news-text">
                    ${item.text || item.short_text || 'Нет текста'}
                </div>
                <div class="news-tags">
                    ${(item.llm_tags || []).map(tag => `
                        <span class="tag">${tag}</span>
                    `).join('')}
                </div>
                <div class="news-stats">
                    <span class="news-stat">
                        <i class="fas fa-hashtag"></i>
                        ${item.llm_tags?.length || 0} тегов
                    </span>
                    <span class="news-stat clickable" onclick="runSearch('${(item.llm_tags || [])[0] || ''}')">
                        <i class="fas fa-search"></i>
                        Поиск по теме
                    </span>
                </div>
            </div>
        `;
    });
    
    elements.newsContainer.innerHTML = html;
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
        
        // Сохраняем результаты для перерисовки при смене темы
        lastSearchResults = data.results;
        lastSearchTag = data.corrected_tag || searchTag;
        lastSearchCount = data.count;
        
        displayResults(data.results, lastSearchTag, lastSearchCount);
        
    } catch (error) {
        console.error('Ошибка поиска:', error);
        showError('Ошибка при выполнении поиска');
    }
}

// Отображение результатов поиска с учетом темы
function displayResults(results, searchTag, count) {
    // Сохраняем последние результаты
    lastSearchResults = results;
    lastSearchTag = searchTag;
    lastSearchCount = count;
    
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
    
    // Определяем цвета для текущей темы
    const backgroundColor = isDarkTheme ? 'var(--dark-card)' : 'white';
    const textColor = isDarkTheme ? 'var(--dark-text)' : 'var(--dark)';
    const borderColor = isDarkTheme ? 'var(--dark-border)' : 'var(--light-gray)';
    const infoColor = isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)';
    const shadowOpacity = isDarkTheme ? '0.2' : '0.05';
    
    let html = `
        <div class="search-info" style="
            background: ${backgroundColor};
            color: ${textColor};
            border: 1px solid ${borderColor};
            border-radius: var(--border-radius);
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, ${shadowOpacity});
        ">
            <h3 style="color: ${textColor}; margin-bottom: 8px; font-size: 18px;">
                Найдено результатов: ${count.toLocaleString()}
            </h3>
            <p style="color: ${infoColor};">
                По тегу: <span class="search-tag" style="
                    background: linear-gradient(135deg, var(--sber-green), var(--sber-dark-green));
                    color: white;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                    margin-left: 8px;
                ">${searchTag}</span>
            </p>
        </div>
    `;
    
    results.forEach(item => {
        // Определяем иконку настроения (исправлено - негативные смайлики красные)
        let sentimentIcon = 'fas fa-meh';
        let sentimentColor = 'var(--gray)';
        
        if (item.sentiment === 'positive') {
            sentimentIcon = 'fas fa-smile';
            sentimentColor = isDarkTheme ? 'var(--sber-green)' : 'var(--success)';
        } else if (item.sentiment === 'negative') {
            sentimentIcon = 'fas fa-frown';
            sentimentColor = 'var(--danger)'; // Всегда красный!
        } else if (item.sentiment === 'neutral') {
            sentimentIcon = 'fas fa-meh';
            sentimentColor = 'var(--gray)';
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