document.addEventListener('DOMContentLoaded', function() {
    // Загружаем данные при старте
    loadDashboardData();
    
    // Устанавливаем время обновления
    document.getElementById('update-time').textContent = 
        new Date().toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
});

async function loadDashboardData() {
    try {
        // Загружаем сигналы
        const response = await fetch('/');
        const html = await response.text();
        
        // Парсим HTML для получения данных (в реальном приложении лучше сделать API эндпоинт)
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // В реальном приложении здесь был бы API запрос
        // Для демо используем тестовые данные
        const testSignals = [
            {
                "tag": "ИИ",
                "count": 15,
                "positive": 12,
                "negative": 2,
                "insiders": 8,
                "signal": "opportunity"
            },
            {
                "tag": "HR",
                "count": 8,
                "positive": 3,
                "negative": 4,
                "insiders": 1,
                "signal": "problem"
            },
            {
                "tag": "Финтех",
                "count": 5,
                "positive": 4,
                "negative": 0,
                "insiders": 3,
                "signal": "early_trend"
            },
            {
                "tag": "Банки",
                "count": 10,
                "positive": 6,
                "negative": 3,
                "insiders": 2,
                "signal": "opportunity"
            }
        ];
        
        // Обновляем статистику
        updateStats(testSignals);
        
        // Отображаем сигналы
        displaySignals(testSignals);
        
        // Отображаем популярные теги
        displayTagsCloud(testSignals);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        displayError();
    }
}

function updateStats(signals) {
    document.getElementById('total-news').textContent = '125'; // Пример
    document.getElementById('total-tags').textContent = '28'; // Пример
    document.getElementById('total-signals').textContent = signals.filter(s => s.signal !== 'none').length;
    document.getElementById('signals-count').textContent = signals.filter(s => s.signal !== 'none').length;
}

function displaySignals(signals) {
    const container = document.getElementById('signals-container');
    
    const activeSignals = signals.filter(s => s.signal !== 'none');
    
    if (activeSignals.length === 0) {
        container.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-check-circle"></i>
                <h3>Активных сигналов нет</h3>
                <p>Все теги в пределах нормы</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = activeSignals.map(signal => `
        <div class="signal-item ${signal.signal}">
            <div class="signal-header">
                <span class="signal-tag">${signal.tag}</span>
                <span class="signal-type ${signal.signal}">
                    ${getSignalLabel(signal.signal)}
                </span>
            </div>
            <div class="signal-info">
                <p>Упоминаний: ${signal.count}</p>
            </div>
            <div class="signal-stats">
                <div class="stat">
                    <i class="fas fa-thumbs-up"></i>
                    <span>${signal.positive}</span>
                </div>
                <div class="stat">
                    <i class="fas fa-thumbs-down"></i>
                    <span>${signal.negative}</span>
                </div>
                <div class="stat">
                    <i class="fas fa-user-secret"></i>
                    <span>${signal.insiders}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function displayTagsCloud(signals) {
    const container = document.getElementById('tags-cloud');
    
    // Создаем облако тегов
    const tags = signals.map(s => ({
        name: s.tag,
        count: s.count,
        signal: s.signal
    }));
    
    // Сортируем по количеству упоминаний
    tags.sort((a, b) => b.count - a.count);
    
    container.innerHTML = tags.map(tag => `
        <div class="tag-cloud" onclick="searchTag('${tag.name}')">
            ${tag.name} <span class="tag-count">${tag.count}</span>
        </div>
    `).join('');
}

function getSignalLabel(type) {
    const labels = {
        'problem': 'Проблема',
        'opportunity': 'Возможность',
        'early_trend': 'Ранний тренд',
        'none': 'Без сигнала'
    };
    return labels[type] || type;
}

async function runSearch() {
    const query = document.getElementById('search').value.trim();
    
    if (!query) {
        alert('Введите тег для поиска');
        return;
    }
    
    const resultsContainer = document.getElementById('results');
    resultsContainer.innerHTML = `
        <div class="loading">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Поиск...</p>
        </div>
    `;
    
    try {
        // В реальном приложении
        // const response = await fetch('/api/search?q=' + encodeURIComponent(query));
        // const data = await response.json();
        
        // Для демо - тестовые данные
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const testResults = [
            {
                "channel": "AI News",
                "text": "Новый прорыв в машинном обучении от Google. Исследователи представили модель, которая превосходит существующие аналоги на 15%.",
                "datetime": "2024-01-15 10:30:00",
                "tags": ["ИИ", "Machine Learning", "Google"]
            },
            {
                "channel": "Tech Insights",
                "text": "Рынок труда для AI-специалистов продолжает расти. Спрос превышает предложение на 40%.",
                "datetime": "2024-01-14 14:20:00",
                "tags": ["ИИ", "Рынок труда", "HR"]
            },
            {
                "channel": "Startup Digest",
                "text": "Стартап в области AI привлек $50 млн инвестиций. Компания разрабатывает решения для банковской сферы.",
                "datetime": "2024-01-13 09:15:00",
                "tags": ["ИИ", "Стартапы", "Инвестиции", "Банки"]
            }
        ];
        
        displayResults(testResults);
    } catch (error) {
        console.error('Search error:', error);
        resultsContainer.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Ошибка поиска</h3>
                <p>Попробуйте еще раз</p>
            </div>
        `;
    }
}

function displayResults(results) {
    const container = document.getElementById('results');
    
    if (results.length === 0) {
        container.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-search"></i>
                <h3>Ничего не найдено</h3>
                <p>Попробуйте другой тег</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = results.map(item => `
        <div class="news-item">
            <div class="news-header">
                <div class="channel">
                    <i class="fas fa-paper-plane"></i>
                    <span>${item.channel}</span>
                </div>
                <div class="date">${formatDate(item.datetime)}</div>
            </div>
            <div class="news-text">${item.text}</div>
            <div class="news-tags">
                ${item.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

function searchTag(tag) {
    document.getElementById('search').value = tag;
    runSearch();
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function displayError() {
    const container = document.getElementById('signals-container');
    container.innerHTML = `
        <div class="placeholder">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Ошибка загрузки</h3>
            <p>Проверьте подключение к серверу</p>
        </div>
    `;
}