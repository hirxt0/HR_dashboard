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

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTagsCloud();
    loadRecentNews();
    setupEventListeners();
});

// Настройка обработчиков событий
function setupEventListeners() {
    // Поиск по Enter
    elements.searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            runSearch();
        }
    });
    
    // Поиск по клику
    elements.btnSearch.addEventListener('click', runSearch);
    
    // Быстрый поиск по тегам в облаке
    elements.tagsCloud.addEventListener('click', function(e) {
        if (e.target.classList.contains('tag-cloud')) {
            const tag = e.target.textContent;
            elements.searchInput.value = tag;
            runSearch(tag);
        }
    });
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
        const response = await fetch(`${API_BASE_URL}/api/search?tag=${encodeURIComponent(searchTag)}`);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        displayResults(data.results, searchTag, data.count);
        
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
    
    let html = '';
    
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
                        <span class="tag">${tag}</span>
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
        <div class="placeholder">
            <i class="${icon}" style="color: ${color};"></i>
            <p>${message}</p>
        </div>
    `;
}