# PDF Extractor — Plan v2.3

**Статус:** Canonical (Self‑Contained)  
**Дата:** 2025‑12‑28  
**Фаза проекта:** Phase 2.5  

---

## 1. Цель плана

Зафиксировать **исполняемую, детерминированную последовательность разработки PDF Extractor**, синхронизированную с **TechSpec v2.4**.

План:
- самодостаточен;
- не требует обращения к предыдущим версиям;
- ориентирован на code‑first реализацию;
- используется как рабочая инструкция выполнения.

---

## 2. Базовые принципы (NON‑NEGOTIABLE)

1. **Plan следует TechSpec v2.4.**
2. **Один core‑компонент за раз.**
3. **Facts only.**
4. **Python — единственный вычислительный слой.**
5. **Working Prototype Principle.**
   - для продвижения достаточно happy‑path на одном реальном PDF;
   - edge‑cases фиксируются, но не блокируют переход к следующему шагу.
6. **All‑or‑nothing runtime.** Частичное выполнение пайплайна недопустимо.
7. **Фиксация каждого шага.** После каждого этапа — git‑commit и обновление project summary.

---

## 3. Общая схема реализации

1. Минимальная подготовка среды
2. Реализация Python Core (2.1–2.8)
3. Интеграция и оркестрация (n8n)
4. Golden‑тесты и приёмка

---

## 4. Шаг 1. Минимальная подготовка среды

### 4.1 Цель
Создать минимально достаточное окружение для начала разработки core‑компонентов.

### 4.2 Действия

**Code (Source of Truth):**
```bash
mkdir -p /opt/projects/pdf-extractor/agents/input_validator
```

**Runtime (не SoT):**
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

### 4.3 Acceptance Criteria
- каталог агента создан в `/opt/projects/pdf-extractor/agents/`;
- venv создан в `/srv/pdf-extractor/venv`;
- PyPDF2 установлен;
- runtime не содержит исходного кода.

---

## 5. Шаг 2. Реализация Python Core

Компоненты реализуются **строго в порядке, определённом TechSpec v2.4**.

### 5.1 Общие требования ко всем компонентам

- stdin → JSON
- stdout → JSON
- stderr → логи
- exit codes по TechSpec
- минимум: 1 happy‑path + 1 negative‑test

---

### 5.2 Шаг 2.1 InputValidator

**Цель:** Проверить валидность входного PDF.

**Реализация:**
- PyPDF2
- попытка открытия файла
- smoke‑check структуры

**Acceptance:**
- корректный JSON‑выход;
- exit codes: `0`, `10`, `50`.

---

### 5.3 Шаг 2.2 PDFInspector

**Цель:** Получить базовую структурную информацию о PDF.

**Реализация:**
- PyMuPDF (fitz)
- `total_pages`
- эвристика пустых страниц

**Acceptance:**
- детерминированный JSON‑выход;
- корректный `total_pages`.

---

### 5.4 Шаг 2.3 MetadataExtractor (FULL PDF)

**Цель:** Извлечь **сырые anchors** по всему PDF.

**Канон:**
- никакой политики;
- никакой фильтрации;
- только наблюдаемые факты.

**Acceptance:**
- anchors всех типов (DOI, layout, language, markers);
- стабильный JSON‑контракт.

---

### 5.5 Шаг 2.4 BoundaryDetector

**Цель:** Детерминированно определить начала статей.

**Зависимости:**
- ArticleStartPolicy v1.0

**Результат:**
- `article_starts`;
- confidence;
- audit‑signals.

**Acceptance:**
- confidence ≥ 0.70 для всех start_page;
- соблюдение policy;
- golden‑test на референсном PDF.

---

### 5.6 Шаг 2.5 Splitter

**Цель:** Физически разрезать PDF по готовым диапазонам.

**Канон:**
- не определяет границы;
- работает только по данным BoundaryDetector.

**Acceptance:**
- корректные article‑PDF;
- соответствие диапазонам страниц.

---

### 5.7 Шаг 2.6 MetadataVerifier

**Цель:** Проверить согласованность метаданных и PDF‑артефактов.

**Acceptance:**
- выявление несоответствий;
- корректный exit‑code при ошибке.

---

### 5.8 Шаг 2.7 OutputBuilder

**Цель:** Сформировать итоговую структуру выдачи.

**Acceptance:**
- корректные имена файлов;
- корректная структура каталогов.

---

### 5.9 Шаг 2.8 OutputValidator

**Цель:** Финальная валидация пайплайна.

**Acceptance:**
- инвариант `T = L = E` соблюдён;
- финальный статус `success`.

---

## 6. Шаги 3–4 (после Core)

Интеграция n8n, оркестрация и дополнительные тесты детализируются **только после завершения всех core‑компонентов**.

---

## 7. Time Budget (ориентиры)

| Шаг | Время |
|----:|-------|
| Подготовка | ~15 мин |
| InputValidator | 1–2 ч |
| PDFInspector | 0.5–1 ч |
| MetadataExtractor | 2–4 ч |
| BoundaryDetector | 1–2 ч |
| Splitter | 2–4 ч |
| MetadataVerifier | 1–2 ч |
| OutputBuilder | 1–2 ч |
| OutputValidator | 0.5–1 ч |

---

## 8. Правило изменений

Любые изменения плана:
- оформляются новой версией (v2.4+);
- требуют синхронизации с TechSpec;
- фиксируются в project summary.

---

**Plan v2.3 зафиксирован как Canonical.**

