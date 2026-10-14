# Профили контрагентов и плательщики

## Выгрузка и поиск

```python
async for profile in client.contractors.iterate(limit=100):
    print(profile.content_type, profile.id, profile.display_name())

matches = await client.contractors.search("Название", limit=20)
async for profile in client.contractors.iterate_search("Название", limit=100):
    print(profile.display_name())

# Старый вызов сохранён и направляется на рабочий поиск.
matches = await client.contractors.list(q="Название", limit=20)
```

Поиск возвращает компании и физлиц, сокращённые карточки без плательщиков.
Для ручной пагинации нужен конкретный тип ContractorCompany/ContractorHuman,
а не Contractor. Обычный list(category_id=...) сохранён; сочетание q и
category_id отклоняется, поскольку серверная семантика категории в поиске
не подтверждена.

## Реквизиты

```python
profile = await client.contractors.get(contractor_id)
for payer in profile.payers or []:
    print(payer.id, payer.inn, payer.country.id if payer.country else None)

payers = await client.contractors.get_payers(contractor_id, limit=100)
for contact in profile.contact_info or []:
    print(contact.content_type, contact.value)
```

Основного плательщика нет; SDK не выбирает первый автоматически. Старые поля
компании inn/kpp/ogrn/legal_* сохранены, но устарели и обычно пусты. Они не
вычисляются из payers. Незагруженные payers=None отличаются от пустого списка.
Payer и контакты сохраняют неизвестные поля и кастомные значения через
model_extra и model_dump(by_alias=True). Страна имеет строковый ID, например RU.
Контакт может быть Address; его форма отличается от обычного ContactInfo.

Поиск по ИНН на сервере ненадёжен. Для точного сопоставления обходите плательщиков:

```python
target_inn = "1234567890"
async for payer in client.payers.iterate(limit=100):
    if payer.inn == target_inn and not payer.is_dropped and payer.contractor:
        profile = await client.contractors.get(payer.contractor.id)
        print(profile.display_name())
```

## Ресурс плательщиков

```python
from megaplan_sdk import PayerCreate

created = await client.payers.create(
    contractor_id,
    PayerCreate(type="Legal", country={"id": "RU"}, name="Название плательщика"),
)
payer = await client.payers.get(created.id)
definitions = await client.payers.extra_fields("RU", "Legal")
# Удаление выполняется только явно:
# await client.payers.delete(created.id)
```

Модель создания требует type (Legal/Natural) и country. Сервер может требовать
дополнительные поля: на ruvents.megaplan.ru название Legal-плательщика
обязательно и не допускает очистки.
extra_fields() без аргументов читает определения всех стран и типов.
Идентификаторы определений не обязательно совпадают с JSON-ключами кастомных
полей: SDK не строит эти ключи по числовому id.

## Просмотр, применение и аудит

```python
from megaplan_sdk import UpdateAuditError, UpdateConflictError

preview = await client.payers.update(payer_id, {"inn": "1234567890"}, dry_run=True)
for change in preview.changes:
    before = change.before if change.before_exists else "<поле отсутствовало>"
    print(change.field, before, "->", change.after)

# После рассмотрения изменений оператором:
try:
    updated = await client.payers.apply_update(
        preview, audit_path="/existing/private/directory/profiles.jsonl", actor="operator-id",
    )
except UpdateConflictError:
    # Подготовить и рассмотреть новый preview.
    raise
except UpdateAuditError as error:
    # True: сервер подтвердил POST, но результат не записался в аудит.
    # None: исход записи неизвестен. Проверить объект и operation_id,
    # не повторять POST автоматически.
    print(error.operation_id, error.server_changed)
    raise
```

Тот же контракт есть у contractors.update(..., dry_run=True) и apply_update.
Обычный contractors.update(id, dict) сохраняет исторический прямой POST без
валидации, сравнения и аудита. Прямой payers.update валидирует patch, но не
защищает от конкурирующих правок. Для пакетной актуализации используйте preview/apply.

Dry-run не выполняет POST и не создаёт аудит. Незаданные поля исключаются;
явные null и пустая строка сохраняются. Сохранность остальных полей и очищение
значений должны быть проверены на отдельном тестовом объекте аккаунта до
массовой записи.

Preview привязан к аккаунту и сущности. Перед применением SDK повторно читает
редактируемые поля, timeUpdated и признаки удаления/слияния. Счётчики и online
вложенных сотрудников не вызывают ложных конфликтов. GET и POST не атомарны:
серверная блокировка или условная запись не реализованы.

Динамический ключ разрешён, когда он имеет форму Category…CustomField… и
присутствует в исходной карточке. Неизвестные ключи, счётчики и устаревшие
реквизиты компании в preview отклоняются. Для нового плательщика сначала
создайте обязательный минимум, затем прочитайте доступные кастомные поля.

JSONL-аудит содержит намерение до POST и результат/ошибку после него с общим
operation_id. Каждая запись включает UTC-время, actor, тип, id и diff.
Ответ сервера хранится отдельно от обычных SDK-логов; токены и авторизационные
поля исключаются. Приложение выбирает приватное расположение и срок хранения:
аудит содержит контактные данные и прежние реквизиты. Новый файл создаётся с
правами 0600; права существующего файла SDK не меняет. Если запись намерения
не удалась, POST не выполняется.

Новые POST и apply_update не повторяются после network/5xx/429: исход записи
может быть неизвестен. После отклонённого 401 авторефреш и однократный повтор
сохраняются. Старый прямой contractors.update оставляет прежние ретраи.

## Отчёт дублей

```python
candidates = await client.contractors.possible_duplicates(
    contractor_id, content_type="ContractorCompany", limit=100,
)
by_name = await client.contractors.find_duplicates(name="Название", limit=100)
marked = await client.contractors.get_similar(contractor_id, content_type="ContractorCompany")
for candidate in candidates:
    payers = await client.contractors.get_payers(candidate.id)
    print(candidate.id, candidate.display_name(), [p.inn for p in payers if p.inn])
```

Без указанного подтипа методы по ID делают дополнительный get(). Выдача может
содержать оба типа. Кандидат не является доказанным дублем; слияние и пометку
похожести SDK не выполняет. Решение принимает оператор в интерфейсе Мегаплана.

## Архив задач

На проверенном аккаунте обычный /task отдаёт активную выборку, а термин status
расширяет её, игнорируя своё значение. Параметр statuses давал пустой список.
Архивная выдача пропускает некоторые карточки, доступные по прямому ID.
Это наблюдения одного аккаунта; include_archive пока не добавлен. Ключ записи —
(contentType, id): Task и Project могут иметь одинаковый числовой ID.

## Проверено на аккаунте 14.10.2026

Чтение на ruvents.megaplan.ru выгрузило 908 контрагентов обоих подтипов.
На отдельно созданной компании и плательщике подтверждены частичное обновление
без потери банка/названия, очистка необязательного банка пустой строкой и null,
запись/очистка кастомного поля и замена contactInfo целиком. Это результаты
конкретного аккаунта, а не гарантия семантики любого поля на всех инстансах.

Компания автоматически получает плательщика при создании. Сценарий проверяет
очистку и явно созданного, и автоматического плательщика. Компания помечается
на удаление через only_fake_drop.

Сценарий требует явного opt-in записи. Выберите действующий ContractorType ID
своего аккаунта (в примере — 1), приватный аудит и авторизацию через окружение
или .env.local:

```bash
PYTHONPATH=src .venv/bin/python scripts/verify_contractor_writes.py --allow-test-writes --contractor-type-id 1 --audit-path /tmp/sdk-write-probe.jsonl --actor operator-id
```

При отмене или остановке процесса между намерением и результатом исход записи
нужно сверить с сервером. Незавершённое намерение в аудите не означает,
что сервер ничего не записал.
