# Списки и документы

## Проекции и архив

```python
from megaplan_sdk import TaskQuery

query = TaskQuery().include_archive().statuses("completed").search("договор").with_time_fields()
first_page = await client.tasks.list_by(query)
async for task in client.tasks.iterate(**query.as_list_kwargs()):
    print(task.id, task.activity)
```

В обычном режиме SDK передаёт неизвестные поля серверу, в строгом режиме принимает поля проверенного маршрута. При запросе только нужных полей заполните fields. На проверенном аккаунте пустой список полей вместе с only_requested_fields=True вернул стандартные поля. Указание fields=["name"] вернуло тип, ID и имя.

## Связи и документы

```python
result = await client.get_entities_by_links(links, on_missing="report")
for link in result.missing:
    print(link)

async for doc in client.docs.iterate(folder_id, recursive=True):
    print(doc.id)
folder = await client.docs.get_folder(folder_id, compact=True)
doc = await client.docs.get(doc_id)
data = await client.docs.download(doc)
```

Компактное представление можно использовать в raw-запросе к папке. Оно уменьшает размер разобранного JSON. Для больших файлов открывайте `client.attachments.stream(path)` через async with.

## Сделки и комментарии

```python
async for deal in client.deals.iterate(state_in=["Новая заявка", "Договор"]):
    print(deal.id)

content = f"{client.comments.mention(employee)} проверьте документ"
await client.comments.create(entity_id=task_id, entity_type="task", content=content, work=2.5)
```

Значение work задаётся в часах. В карточке комментария запрашивайте workTime. Для полного обхода фильтр по имени состояния применяйте через iterate. Один вызов list(state_in=...) возвращает совпадения только на выбранной странице. Разные программы могут содержать состояния с одинаковыми нормализованными названиями.
