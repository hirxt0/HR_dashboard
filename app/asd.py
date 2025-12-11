import csv

tags_list = [
    "ИИ", "AI", "Machine Learning", "Deep Learning", "LLM", "Нейросети",
    "Vision", "NLP", "Data Science", "Data Engineering", "MLOps",
    "Образование", "Университеты", "Финтех", "Экономика", "Аналитика",
    "Стартапы", "Инвестиции", "Банки", "Безопасность", "Медицина",
    "HR", "Рынок труда", "SaaS", "Open Source", "Linux", "Большие данные",
    "Cloud", "DevOps", "Ритейл", "Промышленность"
]

with open("unique_tags.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["tag"])  # заголовок

    for tag in tags_list:
        writer.writerow([tag])

print("CSV с уникальными тегами создан: unique_tags.csv")
