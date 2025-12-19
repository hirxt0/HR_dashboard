// ui.js - Все функции отображения UI

import { NEWS_PER_PAGE, elements, state } from './config.js';
import { getNewsSentimentColor, getResultSentimentColor, getThemeColors } from './theme.js';
import { runSearch } from './api.js';

/**
 * Показать предложения автодополнения
 */
export function showSuggestions(suggestions, input) {
    // Убираем старое автодополнение
    hideSuggestions();
    
    // Создаем контейнер для подсказок
    state.suggestionsContainer = document.createElement('div');
    state.suggestionsContainer.className = 'suggestions-container';
    
    // Позиционируем под полем ввода
    const inputRect = elements.searchInput.getBoundingClientRect();
    state.suggestionsContainer.style.position = 'absolute';
    state.suggestionsContainer.style.top = `${inputRect.bottom + window.scrollY + 5}px`;
    state.suggestionsContainer.style.left = `${inputRect.left + window.scrollX}px`;
    state.suggestionsContainer.style.width = `${inputRect.width}px`;
    state.suggestionsContainer.style.zIndex = '1000';
    
    // Добавляем стили для темной темы
    if (state.isDarkTheme) {
        state.suggestionsContainer.style.background = 'var(--dark-card)';
        state.suggestionsContainer.style.border = '1px solid var(--dark-border)';
        state.suggestionsContainer.style.color = 'var(--dark-text)';
    }
    
    // Добавляем каждую подсказку
    suggestions.forEach((suggestion, index) => {
        const suggestionEl = document.createElement('div');
        suggestionEl.className = 'suggestion-item';
        suggestionEl.dataset.tag = suggestion.tag;
        
        const isExact = suggestion.is_exact;
        const similarity = Math.round(suggestion.similarity * 100);
        
        const textColor = state.isDarkTheme ? 'var(--dark-text)' : 'var(--dark)';
        const exactColor = state.isDarkTheme ? 'var(--sber-green)' : 'var(--primary)';
        const metaColor = state.isDarkTheme ? 'var(--dark-gray)' : 'var(--gray)';
        
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
            if (state.isDarkTheme) {
                suggestionEl.style.background = 'rgba(33, 160, 56, 0.1)';
            }
        });
        
        suggestionEl.addEventListener('mouseleave', () => {
            suggestionEl.classList.remove('hovered');
            if (state.isDarkTheme) {
                suggestionEl.style.background = '';
            }
        });
        
        state.suggestionsContainer.appendChild(suggestionEl);
    });
    
    // Добавляем контейнер в DOM
    document.body.appendChild(state.suggestionsContainer);
}

/**
 * Скрыть предложения
 */
export function hideSuggestions() {
    if (state.suggestionsContainer) {
        state.suggestionsContainer.remove();
        state.suggestionsContainer = null;
    }
}

/**
 * Обновление элементов пагинации
 */
export function updatePaginationControls(page, total) {
    const totalPages = Math.ceil(total / NEWS_PER_PAGE);
    
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

/**
 * Отображение новостей
 */
export function displayNews(newsItems) {
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
        let sentimentIcon = 'fas fa-meh';
        let sentimentText = 'Нейтрально';
        
        if (item.sentiment === 'positive') {
            sentimentIcon = 'fas fa-smile';
            sentimentText = 'Позитивно';
        } else if (item.sentiment === 'negative') {
            sentimentIcon = 'fas fa-frown';
            sentimentText = 'Негативно';
        } else if (item.sentiment === 'neutral') {
            sentimentIcon = 'fas fa-meh';
            sentimentText = 'Нейтрально';
        }
        
        const sentimentColor = getNewsSentimentColor(item.sentiment);
        const date = item.date || item.created_at?.substring(0, 10) || 'Неизвестно';
        
        html += `
            <div class="news-item">
                <div class="news-header">
                    <div class="channel-info">
                        <div class="channel">
                            <i class="fas fa-newspaper"></i>
                            <span>${item.channel || 'Источник'}</span>
                        </div>
                        <div class="sentiment-badge ${item.sentiment}" style="background: ${sentimentColor}20; color: ${sentimentColor};">
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
                    <span class="news-stat clickable" onclick="window.runSearchGlobal('${(item.llm_tags || [])[0] || ''}')">
                        <i class="fas fa-search"></i>
                        Поиск по теме
                    </span>
                </div>
            </div>
        `;
    });
    
    elements.newsContainer.innerHTML = html;
}

/**
 * Отображение сигналов
 */
export function displaySignals(signals) {
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

/**
 * Отображение результатов поиска
 */
export function displayResults(results, searchTag, count) {
    // Сохраняем последние результаты
    state.lastSearchResults = results;
    state.lastSearchTag = searchTag;
    state.lastSearchCount = count;
    
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
    
    const colors = getThemeColors();
    
    let html = `
        <div class="search-info" style="
            background: ${colors.backgroundColor};
            color: ${colors.textColor};
            border: 1px solid ${colors.borderColor};
            border-radius: var(--border-radius);
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, ${colors.shadowOpacity});
        ">
            <h3 style="color: ${colors.textColor}; margin-bottom: 8px; font-size: 18px;">
                Найдено результатов: ${count.toLocaleString()}
            </h3>
            <p style="color: ${colors.infoColor};">
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
        let sentimentIcon = 'fas fa-meh';
        let sentimentText = 'Нейтрально';
        
        if (item.sentiment === 'positive') {
            sentimentIcon = 'fas fa-smile';
            sentimentText = 'Позитивно';
        } else if (item.sentiment === 'negative') {
            sentimentIcon = 'fas fa-frown';
            sentimentText = 'Негативно';
        } else if (item.sentiment === 'neutral') {
            sentimentIcon = 'fas fa-meh';
            sentimentText = 'Нейтрально';
        }
        
        const sentimentColor = getResultSentimentColor(item.sentiment);
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

/**
 * Показать сообщение об ошибке
 */
export function showError(message) {
    elements.resultsContainer.innerHTML = `
        <div class="placeholder">
            <i class="fas fa-exclamation-triangle" style="color: var(--danger);"></i>
            <h3>Ошибка</h3>
            <p>${message}</p>
        </div>
    `;
}

/**
 * Показать информационное сообщение
 */
export function showMessage(message, type = 'info') {
    const icon = type === 'warning' ? 'fas fa-exclamation-triangle' : 'fas fa-info-circle';
    const color = type === 'warning' ? 'var(--warning)' : 'var(--info)';
    
    elements.resultsContainer.innerHTML = `
        <div class="placeholder" style="margin-bottom: 20px;">
            <i class="${icon}" style="color: ${color};"></i>
            <p>${message}</p>
        </div>
    `;
}
