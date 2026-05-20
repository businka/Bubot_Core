import os
import sqlite3
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, KeyNotFound
import json
from typing import Any, Dict, Union, List


# Регистрируем адаптер для автоматической конвертации dict/list в JSON
def adapt_dict_or_list(value):
    """Конвертирует словарь или список в JSON строку"""
    return json.dumps(value, ensure_ascii=False)


def convert_json(value):
    """Конвертирует JSON строку обратно в Python объект"""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


sqlite3.register_adapter(dict, adapt_dict_or_list)
sqlite3.register_adapter(list, adapt_dict_or_list)
sqlite3.register_converter("JSON", convert_json)


class SqlLite:
    def __init__(self, *, path=None, **kwargs):
        self.path = path
        self.clients = {}
        self._schema_cache = {}

    pass

    @classmethod
    async def connect(cls, device, *, path=None, **kwargs):
        if device:
            default_path = device.path
            path = device.get_param('/oic/con', 'storage_url', default_path)
        return cls(path=path)

    async def find_data_base(self, name):
        data_bases = await self.client.list_database_names()
        if name in data_bases:
            return self.client[name]
        return None

    async def update(self, db, table, data, create=True, *, filter=None, pull=None, add_to_set=None, push=None,
                     _action=None, **kwargs):
        """
        Обновление или вставка записи в таблицу.

        Доработка: если в data есть поля, которых нет в основной таблице,
        то они сохраняются во вспомогательную таблицу (имя = table + поле)
        Связанные записи полностью заменяются на переданные.
        """

        _id = data.get('_id')
        filter_dict = {'_id': _id} if _id else filter
        if not filter_dict:
            raise ValueError("filter_dict не может быть пустым")

        # ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

        async def get_table_columns():
            """Получает список колонок таблицы"""
            cache_key = f"{db}:{table}"
            if cache_key in self._schema_cache:
                return self._schema_cache[cache_key]

            try:
                with sqlite3.connect(self.get_db_path(db), timeout=10) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    self._schema_cache[cache_key] = columns
                    return columns
            except sqlite3.Error:
                self._schema_cache[cache_key] = []
                return []

        def split_data_fields(table_columns):
            """Разделяет поля на основные и связанные"""
            regular = {}
            linked = {}

            for key, value in data.items():
                # Поля с точечной нотацией - всегда связанные
                if '.' in key and not key.endswith('_'):
                    linked[key] = value
                # Поля из основной таблицы или _id
                elif key in table_columns or key == '_id':
                    regular[key] = value
                # Остальные - связанные
                else:
                    linked[key] = value

            return regular, linked

        async def update_main_table(regular_data):
            """Обновляет или вставляет запись в основную таблицу"""
            if not regular_data:
                return filter_dict.get('_id')

            # Формируем запрос
            all_fields = list(filter_dict.keys()) + [k for k in regular_data.keys() if k not in filter_dict]
            columns_str = ', '.join(all_fields)
            placeholders_str = ', '.join(['?'] * len(all_fields))
            conflict_columns = ', '.join(filter_dict.keys())
            update_parts = [f"{field} = excluded.{field}" for field in regular_data.keys() if field != '_id']

            sql = f"""
                INSERT INTO {table} ({columns_str})
                VALUES ({placeholders_str})
                ON CONFLICT ({conflict_columns})
                DO UPDATE SET {', '.join(update_parts) if update_parts else 'NOTHING'};
            """

            # Подготавливаем параметры
            params = []
            for field in all_fields:
                if field in filter_dict:
                    params.append(filter_dict[field])
                else:
                    value = regular_data.get(field)
                    if field.endswith('_') and isinstance(value, dict) and '_id' in value:
                        params.append(value['_id'])
                    else:
                        params.append(value)

            with sqlite3.connect(self.get_db_path(db), timeout=10, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
                return cursor.lastrowid or filter_dict.get('_id')

        async def process_linked_table(conn, cursor, main_id, link_field, value):
            """Обрабатывает одну связанную таблицу"""
            import uuid

            # Определяем имя таблицы и поля
            if '.' in link_field:
                array_field, nested_field = link_field.split('.', 1)
                link_table = f"{table}{array_field}"
            else:
                link_table = f"{table}{link_field}"
                nested_field = None

            parent_key = f"{table}_"  # Например: Integration_

            # Получаем колонки связанной таблицы
            cursor.execute(f"PRAGMA table_info({link_table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Определяем наличие поля _id и автоинкремента
            has_id = '_id' in column_names
            has_parent_key = parent_key in column_names

            if not has_parent_key:
                # Если нет поля связи, не можем продолжить
                return

            # Удаляем старые записи
            cursor.execute(f"DELETE FROM {link_table} WHERE {parent_key} = ?", (main_id,))

            # Функция для вставки одной записи
            def insert_record(record_value, index=None):
                """Вставляет запись в связанную таблицу, автоматически добавляя поле связи"""
                fields = []
                values = []

                # 1. Добавляем поле связи
                fields.append(parent_key)
                values.append(main_id)

                # 2. Обрабатываем _id, если он есть в таблице
                if has_id:
                    fields.append('_id')
                    if isinstance(record_value, dict) and '_id' in record_value:
                        # Используем существующий _id
                        values.append(record_value['_id'])
                    else:
                        # Генерируем новый _id
                        values.append(str(uuid.uuid4()))

                # 3. Добавляем остальные поля
                if isinstance(record_value, dict):
                    for k, v in record_value.items():
                        if k == '_id':
                            continue  # Уже обработали
                        if k in column_names and k != parent_key:
                            fields.append(k)
                            values.append(v)
                else:
                    # Простое значение
                    if nested_field and nested_field in column_names:
                        fields.append(nested_field)
                        values.append(record_value)
                    else:
                        # Находим первую колонку, не являющуюся служебной
                        for col in column_names:
                            if col not in [parent_key, '_id']:
                                fields.append(col)
                                values.append(record_value)
                                break

                # Формируем и выполняем INSERT
                placeholders = ','.join(['?' for _ in values])
                sql = f"INSERT INTO {link_table} ({','.join(fields)}) VALUES ({placeholders})"
                cursor.execute(sql, values)

            # Вставляем все записи
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    insert_record(item, idx)
            else:
                insert_record(value)

        async def process_all_linked_tables(main_id, link_data):
            """Обрабатывает все связанные таблицы"""
            with sqlite3.connect(self.get_db_path(db), timeout=10, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                for link_field, value in link_data.items():
                    await process_linked_table(conn, cursor, main_id, link_field, value)
                conn.commit()

        # ========== ОСНОВНАЯ ЛОГИКА ==========

        try:
            # 1. Получаем схему таблицы
            table_columns = await get_table_columns()

            # 2. Разделяем поля
            regular_data, link_data = split_data_fields(table_columns)

            # 3. Обновляем основную таблицу
            main_id = await update_main_table(regular_data)

            # 4. Обновляем связанные таблицы
            if link_data:
                await process_all_linked_tables(main_id, link_data)

            return main_id

        except sqlite3.Error as e:
            raise ExtException(
                parent=e,
                message='SQLite update error',
                detail=f"Error updating {table} in {db}: {str(e)}"
            )

    async def find_one(self, db, table, filter, *, projection=None):
        res = await self.list(db, table, filter=filter, projection=projection, limit=1, skip=0)
        return res[0] if res else None

    # async def delete_one(self, db, table, filter):
    #     return await self.client[db][table].delete_one(filter)
    #
    # async def delete_many(self, db, table, filter):
    #     return await self.client[db][table].delete_many(filter)
    #
    # async def count(self, db, table, **kwargs):
    #     return await self.client[db][table].count_documents(
    #         kwargs.get('filter', {})
    #     )

    def get_db_path(self, name, create=True):
        if not name:
            raise KeyNotFound(message='Db not defined')
        try:
            return self.clients[name]
        except KeyError:
            path = os.path.normpath(f'{self.path}/{name}.db')
            if not create and not os.path.isfile(path):
                raise Exception('db not found')
        return path

    def get_table(self, name):
        pass

    async def list(self, db, table, **kwargs):
        """
        Получение списка записей из таблицы с поддержкой JSON полей
        При наличии в фильтре параметра Search выполняется полнотекстовый поиск по связанной fts таблице.

        Доработка: если в projection указано поле которого нет в таблице,
        то данные подтягиваются из вспомогательной таблицы (имя = table + поле)
        Связанные записи возвращаются в виде массива словарей без поля связи
        """

        try:
            filter_dict = kwargs.get('filter', {})
            has_dot_notation = any('.' in key and not key.endswith('_') for key in filter_dict.keys())

            if has_dot_notation:
                # Если есть точечная нотация - используем запрос со связанными таблицами
                return await self._list_with_links(db, table, kwargs)

            # Получаем параметры запроса
            projection = kwargs.get('projection', None)
            filter_dict = kwargs.get('filter', {})
            order = kwargs.get('order', None)
            limit = kwargs.get('limit')
            skip = kwargs.get('skip', 0)
            full_text_search = filter_dict.pop('Search', None)
            params = []

            # Получаем схему таблицы для проверки существования полей
            table_columns = await self._get_table_columns(db, table)

            # Разделяем projection на поля основной таблицы и связанных
            main_projection = {}
            linked_projections = {}

            if projection:
                for field, include in projection.items():
                    if include and field in table_columns:
                        main_projection[field] = include
                    elif include and field not in table_columns:
                        # Поле не найдено в основной таблице - будет подтягиваться из связанной
                        linked_projections[field] = include
            else:
                # Если projection не указан, берем все поля основной таблицы
                main_projection = {col: True for col in table_columns}

            # Формируем базовый SELECT запрос (только для полей основной таблицы)
            select_clause = self._projection_to_query('', main_projection, table) if main_projection else f"{table}.*"

            if full_text_search:
                if ' ' not in full_text_search:
                    full_text_search = f"{full_text_search}*"
                fts_table = f"{table}_fts"
                query = f"SELECT {select_clause} FROM {table} INNER JOIN {fts_table} ON {table}._id = {fts_table}.rowid"
                query += f" WHERE {fts_table} MATCH ?"
                params.append(full_text_search)

                if filter_dict:  # остальные фильтры
                    where_clause, where_params = MongoToSQLiteConverter.filter_to_sqlite(filter_dict)
                    if where_clause and where_clause != "1=1":
                        query += f" AND ({where_clause})"
                        params.extend(where_params)

                # Сортировка по релевантности если нет order
                if order:
                    query = self._list_order_to_query(query, order)
                else:
                    query += f" ORDER BY {fts_table}.rank"
            else:
                query = f"SELECT {select_clause} FROM {table}"

                # Добавляем WHERE условия с поддержкой JSON и полей-ссылок
                if filter_dict:
                    where_clause, where_params = MongoToSQLiteConverter.filter_to_sqlite(filter_dict)
                    query += f" WHERE {where_clause}"
                    params.extend(where_params)

                # Добавляем ORDER BY
                if order:
                    query = self._list_order_to_query(query, order)

            # Добавляем LIMIT и OFFSET
            if limit:
                query += f" LIMIT ?"
                params.append(limit)
            if skip:
                query += f" OFFSET ?"
                params.append(skip)

            # Выполняем запрос
            result = []
            with sqlite3.connect(
                    self.get_db_path(db),
                    timeout=10,
                    detect_types=sqlite3.PARSE_DECLTYPES
            ) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)

                # Преобразуем Row в dict - JSON поля уже распарсены адаптерами!
                rows = []
                for row in cursor:
                    row_dict = dict(row)

                    # Для полей-ссылок (заканчиваются на _) преобразуем обратно в формат MongoDB
                    for key in list(row_dict.keys()):
                        if key.endswith('_'):
                            value = row_dict[key]
                            if value is not None:
                                row_dict[key] = {'_id': value}

                    rows.append(row_dict)

                # BATCH LOAD: Загружаем все связанные данные одним запросом для каждого link_field
                if linked_projections and rows:
                    # Собираем все ID родительских записей
                    parent_ids = [row['_id'] for row in rows]

                    # Для каждого связанного поля загружаем данные batch-запросом
                    for link_field in linked_projections.keys():
                        # Используем batch загрузку вместо цикла по каждой записи
                        linked_data_map = await self._batch_load_linked_records(
                            db, table, parent_ids, link_field
                        )

                        # Присваиваем загруженные данные каждой записи
                        for row_dict in rows:
                            row_dict[link_field] = linked_data_map.get(row_dict['_id'], [])

                result = rows

            return result

        except Exception as err:
            raise ExtException(
                parent=err,
                message='SQL Lite error',
                detail=f"{str(err)} (db {db} table {table})"
            )

    async def _get_table_columns(self, db, table_name):
        """Получает список колонок таблицы с кэшированием"""
        cache_key = f"{db}:{table_name}"
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        try:
            with sqlite3.connect(
                    self.get_db_path(db),
                    timeout=10
            ) as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                self._schema_cache[cache_key] = columns
                return columns
        except sqlite3.Error:
            self._schema_cache[cache_key] = []
            return []

    async def _get_linked_records(self, conn, link_table, parent_key, parent_id):
        """
        Получает все связанные записи из дополнительной таблицы
        Возвращает массив словарей без поля связи

        Структура дополнительной таблицы:
        - поле связи: {имя_родительской_таблицы}_ (содержит _id основной таблицы)
        - остальные поля: данные, которые нужно вернуть

        Пример:
        Таблица users_roles:
        - users_ (поле связи)
        - role_id
        - role_name
        - priority

        Результат: [
            {'role_id': 1, 'role_name': 'admin', 'priority': 1},
            {'role_id': 2, 'role_name': 'user', 'priority': 2}
        ]
        """
        try:
            # Получаем информацию о структуре таблицы
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({link_table})")
            all_columns = cursor.fetchall()

            # Определяем колонки для выборки (исключая поле связи)
            data_columns = []
            for col in all_columns:
                col_name = col[1]
                if col_name != parent_key:
                    data_columns.append(col_name)

            if not data_columns:
                return []

            # Формируем запрос для получения данных
            columns_str = ', '.join(data_columns)
            cursor.execute(
                f"SELECT {columns_str} FROM {link_table} WHERE {parent_key} = ?",
                (parent_id,)
            )

            # Преобразуем результаты в список словарей
            results = []
            for row in cursor.fetchall():
                record_dict = {}
                for idx, col_name in enumerate(data_columns):
                    value = row[idx]

                    # Пробуем распарсить JSON значения
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass

                    record_dict[col_name] = value
                results.append(record_dict)

            return results

        except sqlite3.Error:
            return []

    # Также обновим метод _list_with_links для совместимости
    async def _list_with_links(self, db, table, kwargs):
        """
        Получение списка записей с поддержкой связанных таблиц (точечная нотация)
        Структура максимально повторяет оригинальный метод list
        """

        try:
            # Получаем параметры как в оригинале
            projection = kwargs.get('projection', None)
            filter_dict = kwargs.get('filter', {}).copy()
            order = kwargs.get('order', None)
            limit = kwargs.get('limit')
            skip = kwargs.get('skip', 0)
            full_text_search = filter_dict.pop('Search', None)
            params = []

            # Разделяем фильтры на обычные и для связанных таблиц
            link_filters = {}
            regular_filters = {}

            for key, val in filter_dict.items():
                if '.' in key and not key.endswith('_'):
                    link_filters[key] = val
                else:
                    regular_filters[key] = val

            # Формируем SELECT
            select_clause = self._projection_to_query('', projection, table)

            # Базовый запрос
            if full_text_search:
                if ' ' not in full_text_search:
                    full_text_search = f"{full_text_search}*"
                fts_table = f"{table}_fts"
                query = f"SELECT {select_clause} FROM {table} INNER JOIN {fts_table} ON {table}._id = {fts_table}.rowid"
                query += f" WHERE {fts_table} MATCH ?"
                params.append(full_text_search)
            else:
                query = f"SELECT {select_clause} FROM {table}"

            # Добавляем условия для связанных таблиц (через IN)
            where_parts = []

            for dot_field, value in link_filters.items():
                array_field, nested_field = dot_field.split('.', 1)
                link_table = f"{table}{array_field}"
                link_column = f"{table}_"

                if isinstance(value, dict):
                    if "$in" in value:
                        placeholders = ','.join(['?'] * len(value["$in"]))
                        where_parts.append(
                            f"{table}._id IN (SELECT {link_column} FROM {link_table} WHERE {nested_field} IN ({placeholders}))"
                        )
                        params.extend(value["$in"])
                    else:
                        op = list(value.keys())[0]
                        val = list(value.values())[0]
                        where_parts.append(
                            f"{table}._id IN (SELECT {link_column} FROM {link_table} WHERE {nested_field} {op} ?)"
                        )
                        params.append(val)
                else:
                    where_parts.append(
                        f"{table}._id IN (SELECT {link_column} FROM {link_table} WHERE {nested_field} = ?)"
                    )
                    params.append(value)

            # Добавляем обычные фильтры
            if regular_filters:
                where_clause, where_params = MongoToSQLiteConverter.filter_to_sqlite(regular_filters)
                if where_clause and where_clause != "1=1":
                    where_parts.append(f"({where_clause})")
                    params.extend(where_params)

            # Собираем WHERE
            if where_parts:
                if full_text_search:
                    query += f" AND ({' AND '.join(where_parts)})"
                else:
                    query += f" WHERE {' AND '.join(where_parts)}"

            # ORDER BY
            if full_text_search and not order:
                query += f" ORDER BY {fts_table}.rank"
            elif order:
                query = self._list_order_to_query(query, order)

            # LIMIT и OFFSET
            if limit:
                query += f" LIMIT ?"
                params.append(limit)
            if skip:
                query += f" OFFSET ?"
                params.append(skip)

            # Выполняем запрос
            result = []
            with sqlite3.connect(
                    self.get_db_path(db),
                    timeout=10,
                    detect_types=sqlite3.PARSE_DECLTYPES
            ) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)

                # Преобразуем Row в dict
                rows = []
                for row in cursor:
                    row_dict = dict(row)

                    # Для полей-ссылок
                    for key in list(row_dict.keys()):
                        if key.endswith('_'):
                            value = row_dict[key]
                            if value is not None:
                                row_dict[key] = {'_id': value}

                    rows.append(row_dict)

                # Определяем какие связанные данные нужно загрузить
                requested_links = set()
                if projection:
                    for field, include in projection.items():
                        if include and '.' in field:
                            requested_links.add(field.split('.')[0])
                        elif include and field in link_filters:
                            requested_links.add(field)
                else:
                    requested_links = {field.split('.')[0] for field in link_filters.keys()}

                # BATCH LOAD: Загружаем все связанные данные
                if requested_links and rows:
                    parent_ids = [row['_id'] for row in rows]

                    for link_field in requested_links:
                        linked_data_map = await self._batch_load_linked_records(
                            db, table, parent_ids, link_field
                        )

                        for row_dict in rows:
                            row_dict[link_field] = linked_data_map.get(row_dict['_id'], [])

                result = rows

            return result

        except Exception as err:
            raise ExtException(
                parent=err,
                message='SQL Lite error',
                detail=f"{str(err)} (db {db} table {table})"
            )

    async def _table_exists(self, db, table_name):
        """Проверяет существование таблицы"""
        try:
            with sqlite3.connect(
                    self.get_db_path(db),
                    timeout=10
            ) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                return cursor.fetchone() is not None
        except sqlite3.Error:
            return False

    @staticmethod
    def _list_order_to_query(_query, _order):
        if not _order:
            return _query
        res = []
        for elem in _order:
            direction = 'ASC' if _order[elem] > 0 else 'DESC'
            res.append(f"{elem} {direction}")
        return f"{_query} ORDER BY {', '.join(res)}"

    def _build_where_clause(self, filter_dict):
        """
        Строит WHERE условие из фильтра с поддержкой JSON операторов
        Возвращает кортеж (where_clause, params)
        """
        return MongoToSQLiteConverter.filter_to_sqlite(filter_dict)

    @staticmethod
    def _projection_to_query(_query, _projection, table_name):
        """Преобразует проекцию в SQL SELECT часть"""
        if _projection:
            fields = []
            for field, include in _projection.items():
                if include:
                    fields.append(f"{table_name}.{field}")
            if fields:
                return f"{_query} {', '.join(fields)}"
        return f"{_query} {table_name}.*"

    async def _batch_load_linked_records(self, db, table, parent_ids, link_field):
        """
        Загружает связанные записи для нескольких родительских записей одним запросом
        Возвращает словарь {parent_id: [records]}
        """
        if not parent_ids:
            return {}

        link_table = f"{table}{link_field}"
        parent_key = f"{table}_"

        # Проверяем существование таблицы
        if not await self._table_exists(db, link_table):
            return {pid: [] for pid in parent_ids}

        try:
            with sqlite3.connect(
                    self.get_db_path(db),
                    timeout=10,
                    detect_types=sqlite3.PARSE_DECLTYPES
            ) as conn:
                cursor = conn.cursor()

                # Получаем схему таблицы
                cursor.execute(f"PRAGMA table_info({link_table})")
                all_columns = cursor.fetchall()
                data_columns = [col[1] for col in all_columns if col[1] != parent_key]

                if not data_columns:
                    return {pid: [] for pid in parent_ids}

                # Загружаем все записи одним запросом
                placeholders = ','.join(['?'] * len(parent_ids))
                columns_str = ', '.join([parent_key] + data_columns)
                cursor.execute(
                    f"SELECT {columns_str} FROM {link_table} WHERE {parent_key} IN ({placeholders})",
                    parent_ids
                )

                # Группируем результаты по parent_id
                result = {pid: [] for pid in parent_ids}
                for row in cursor.fetchall():
                    parent_id = row[0]
                    record_dict = {}
                    for idx, col_name in enumerate(data_columns, 1):
                        value = row[idx]
                        if isinstance(value, str):
                            try:
                                value = json.loads(value)
                            except:
                                pass
                        record_dict[col_name] = value
                    result[parent_id].append(record_dict)

                return result

        except sqlite3.Error:
            return {pid: [] for pid in parent_ids}

    async def close(self):
        return


class MongoToSQLiteConverter:
    @staticmethod
    def filter_to_sqlite(filter_obj: Union[Dict[str, Any], List, None]) -> tuple:
        """
        Конвертирует MongoDB-подобный фильтр в SQLite WHERE-условие с параметрами
        Учитывает поля-ссылки (заканчивающиеся на _) и извлекает из них _id

        Returns:
            tuple: (where_clause, params_list)
        """
        if not filter_obj:
            return "1=1", []

        conditions, params = MongoToSQLiteConverter._parse_conditions(filter_obj)

        if conditions:
            return conditions, params
        return "1=1", []

    @staticmethod
    def _parse_conditions(filter_obj: Union[Dict[str, Any], List]) -> tuple:
        """Парсит условия верхнего уровня и возвращает (sql_condition, params)"""
        if isinstance(filter_obj, list):
            conditions = []
            params = []
            for cond in filter_obj:
                sql_cond, cond_params = MongoToSQLiteConverter._parse_conditions(cond)
                if sql_cond:
                    conditions.append(f"({sql_cond})")
                    params.extend(cond_params)
            return " AND ".join(conditions), params

        elif isinstance(filter_obj, dict):
            logical_conditions = []
            field_conditions = []
            params = []

            for key, value in filter_obj.items():
                if key == "$or":
                    sql_cond, cond_params = MongoToSQLiteConverter._parse_or(value)
                    if sql_cond:
                        logical_conditions.append(sql_cond)
                        params.extend(cond_params)
                elif key == "$and":
                    sql_cond, cond_params = MongoToSQLiteConverter._parse_and(value)
                    if sql_cond:
                        logical_conditions.append(sql_cond)
                        params.extend(cond_params)
                else:
                    sql_cond, cond_params = MongoToSQLiteConverter._parse_field_condition(key, value)
                    if sql_cond:
                        field_conditions.append(sql_cond)
                        params.extend(cond_params)

            all_conditions = field_conditions + logical_conditions
            if all_conditions:
                return " AND ".join(all_conditions), params
            return "", []

        return "", []

    @staticmethod
    def _parse_field_condition(field: str, value: Any) -> tuple:
        """Парсит условие для конкретного поля с поддержкой полей-ссылок"""

        # Обработка поля-ссылки (заканчивается на _)
        if field.endswith('_') and isinstance(value, dict) and '_id' in value:
            # Извлекаем _id из словаря для сравнения
            value = value['_id']

        if isinstance(value, dict):
            return MongoToSQLiteConverter._parse_operator(field, value)

        # Простое равенство
        if value is None:
            return f"{field} IS NULL", []

        return f"{field} = ?", [value]

    @staticmethod
    def _parse_operator(field: str, operator_dict: Dict[str, Any]) -> tuple:
        """Парсит MongoDB операторы с поддержкой полей-ссылок"""
        operators = list(operator_dict.keys())
        params = []

        # Оператор $in
        if "$in" in operators:
            in_values = operator_dict["$in"]
            if not isinstance(in_values, (list, tuple)):
                in_values = [in_values]

            # Обработка полей-ссылок в массиве $in
            processed_values = []
            for val in in_values:
                if field.endswith('_') and isinstance(val, dict) and '_id' in val:
                    processed_values.append(val['_id'])
                else:
                    processed_values.append(val)

            placeholders = ','.join(['?'] * len(processed_values))
            params.extend(processed_values)
            return f"{field} IN ({placeholders})", params

        # Оператор $nin (not in)
        if "$nin" in operators:
            nin_values = operator_dict["$nin"]
            if not isinstance(nin_values, (list, tuple)):
                nin_values = [nin_values]

            # Обработка полей-ссылок в массиве $nin
            processed_values = []
            for val in nin_values:
                if field.endswith('_') and isinstance(val, dict) and '_id' in val:
                    processed_values.append(val['_id'])
                else:
                    processed_values.append(val)

            placeholders = ','.join(['?'] * len(processed_values))
            params.extend(processed_values)
            return f"{field} NOT IN ({placeholders})", params

        # Оператор $ne
        if "$ne" in operators:
            ne_value = operator_dict["$ne"]
            # Обработка поля-ссылки
            if field.endswith('_') and isinstance(ne_value, dict) and '_id' in ne_value:
                ne_value = ne_value['_id']
            if ne_value is None:
                return f"{field} IS NOT NULL", []
            return f"{field} != ?", [ne_value]

        # Оператор $exists
        if "$exists" in operators:
            exists = operator_dict["$exists"]
            if exists:
                return f"{field} IS NOT NULL", []
            else:
                return f"{field} IS NULL", []

        # Операторы сравнения
        comparison_operators = {
            "$gt": ">",
            "$gte": ">=",
            "$lt": "<",
            "$lte": "<="
        }

        for mongo_op, sql_op in comparison_operators.items():
            if mongo_op in operators:
                op_value = operator_dict[mongo_op]
                # Обработка поля-ссылки
                if field.endswith('_') and isinstance(op_value, dict) and '_id' in op_value:
                    op_value = op_value['_id']
                return f"{field} {sql_op} ?", [op_value]

        # Оператор $regex
        if "$regex" in operators:
            regex_pattern = operator_dict["$regex"]
            return f"{field} REGEXP ?", [regex_pattern]

        # Оператор $elemMatch (для поиска в JSON массивах)
        if "$elemMatch" in operators:
            elem_value = operator_dict["$elemMatch"]
            return MongoToSQLiteConverter._build_json_array_condition(field, elem_value)

        raise NotImplementedError(f"Unsupported operator: {operators}")

    @staticmethod
    def _parse_or(or_conditions: List[Dict[str, Any]]) -> tuple:
        """Парсит $or оператор"""
        if not or_conditions:
            return "0", []  # Пустой OR всегда false

        conditions = []
        params = []

        for condition in or_conditions:
            if isinstance(condition, dict):
                sql_cond, cond_params = MongoToSQLiteConverter._parse_conditions(condition)
                if sql_cond:
                    conditions.append(f"({sql_cond})")
                    params.extend(cond_params)

        if conditions:
            return f"({' OR '.join(conditions)})", params
        return "0", []

    @staticmethod
    def _parse_and(and_conditions: List[Dict[str, Any]]) -> tuple:
        """Парсит $and оператор"""
        if not and_conditions:
            return "1", []  # Пустой AND всегда true

        conditions = []
        params = []

        for condition in and_conditions:
            if isinstance(condition, dict):
                sql_cond, cond_params = MongoToSQLiteConverter._parse_conditions(condition)
                if sql_cond:
                    conditions.append(f"({sql_cond})")
                    params.extend(cond_params)

        if conditions:
            return " AND ".join(conditions), params
        return "1", []

    @staticmethod
    def _build_json_array_condition(field: str, value: Any) -> tuple:
        """
        Строит условие для поиска значения в JSON-массиве.
        Используется для $elemMatch.
        """
        return f"EXISTS (SELECT 1 FROM json_each({field}) WHERE json_each.value = ?)", [value]
