# PDF Extractor — Plan v2.2

**Статус:** Canonical **Дата:** 2025-12-28 **Основание:** TechSpec v2.3.1 (Canonical) **Предыдущая версия:** Plan v2.1

---

## 1. Цель плана

Зафиксировать **исполняемую, детерминированную последовательность разработки PDF Extractor**, ориентированную на code-first реализацию и поэтапную валидацию.

*(Без изменений относительно Plan v2.1)*

---

## 2. Базовые принципы (NON-NEGOTIABLE)

1. Plan следует TechSpec.
2. Один core-компонент за раз.
3. Facts only.
4. Python — единственный вычислительный слой.
5. **Working Prototype Principle:**
   - для перехода дальше достаточно happy-path на 1 реальном PDF;
   - edge cases фиксируются, но не блокируют прогресс.
6. Runtime-семантика пайплайна остаётся all-or-nothing.
7. После каждого шага — git commit + фиксация результата.

*(Без изменений относительно Plan v2.1)*

---

## 3. Общая схема

1. Минимальная подготовка среды
2. Реализация Python Core (2.1–2.8)
3. Интеграция и оркестрация
4. Тесты и приёмка

**Изменение:** обновлён диапазон шагов Python Core.

---

## 4. Шаг 1. Минимальная подготовка (15 минут)

### 4.1. Цель

Создать минимум для старта InputValidator.

### 4.2. Действия

**Code:**

```bash
mkdir -p /opt/projects/pdf-extractor/agents/input_validator
```

**Runtime:**

```bash
mkdir -p /srv/pdf-extractor/{runs,logs,tmp}
cd /srv/pdf-extractor
python3 -m venv venv
source venv/bin/activate
pip install PyPDF2==3.0.1
```

**Создание файла:**

```bash
touch /opt/projects/pdf-extractor/agents/input_validator/validator.py
```

### 4.3. Acceptance

- каталог агента создан в `/opt/projects/...`
- venv создан в `/srv/pdf-extractor/venv`
- PyPDF2 установлен

*(Без изменений относительно Plan v2.1)*

---

## 5. Шаг 2. Реализация Python Core

Компоненты реализуются **строго по Pipeline Flow из TechSpec v2.3.1**.

### 5.1. Общие правила

- stdin/stdout JSON
- exit codes
- 1 happy-path + 1 negative test

*(Без изменений по содержанию, обновлена ссылка на версию TechSpec)*

---

### 5.2. Шаг 2.1. InputValidator

**Цель:** проверить, можем ли мы работать с входным PDF.

**Implementation Hints:**

- PyPDF2
- попытка открытия + smoke-check

**Acceptance:**

- корректный JSON-выход
- exit codes 0 / 10 / 50

*(Без изменений относительно Plan v2.1)*

---

### 5.3. Шаг 2.2. PDFInspector

**Цель:** получить структурную информацию о PDF.

**Implementation Hints:**

- PyMuPDF (fitz)
- page\_count
- эвристика пустых страниц

*(Без изменений относительно Plan v2.1)*

---

### 5.4. Шаги 2.3–2.8 (UPDATED)

Последовательная реализация core-компонентов **по одному**, с обязательной фиксацией результата после каждого шага:

2.3 **MetadataExtractor (FULL PDF)** — извлечение якорей (DOI и сигналы начала статей) из полного PDF.

2.4 **BoundaryDetector** — детерминированное преобразование якорей в диапазоны страниц.

2.5 **Splitter** — физическая разрезка PDF по готовым диапазонам страниц.

2.6 **MetadataVerifier** — проверка согласованности метаданных article-PDF.

2.7 **OutputBuilder** — формирование итоговых файлов и структуры.

2.8 **OutputValidator** — финальная валидация результатов.

**Изменение относительно Plan v2.1:**

- шаг `Splitter` смещён после BoundaryDetector;
- добавлен новый шаг `BoundaryDetector`;
- обновлена нумерация шагов (2.3–2.8 вместо 2.3–2.7).

---

## 6. Шаги 3–4 (детализируются после Step 2)

Интеграция, n8n и golden-тесты детализируются **после** завершения core-компонентов.

*(Без изменений относительно Plan v2.1)*

---

## 7. Time Budget

| Шаг               | Время   |
| ----------------- | ------- |
| Подготовка        | 15 мин  |
| InputValidator    | 1–2 ч   |
| PDFInspector      | 0.5–1 ч |
| MetadataExtractor | 2–4 ч   |
| BoundaryDetector  | 1–2 ч   |
| Splitter          | 2–4 ч   |
| MetadataVerifier  | 1–2 ч   |
| OutputBuilder     | 1–2 ч   |
| OutputValidator   | 0.5–1 ч |

**Изменение:** добавлена оценка BoundaryDetector.

---

## 8. Правило изменений

Любые изменения требуют новой версии Plan и согласования с TechSpec.

*(Без изменений относительно Plan v2.1)*

