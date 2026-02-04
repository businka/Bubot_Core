import os
import sqlite3
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, KeyNotFound
import json
from typing import Any, Dict, Union, List


class SqlLite:
    def __init__(self, **kwargs):
        self.path = kwargs.get('path')
        self.clients = {}

    pass

    @classmethod
    async def connect(cls, device, **kwargs):
        path = None
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

        _id = data.get('_id')
        filter_dict = {'_id': _id} if _id else filter
        if not filter_dict:
            raise ValueError("filter_dict не может быть пустым")

            # 1. Для вставки новой записи объединяем все поля
            # Порядок: сначала все поля из filter_dict, потом из data
        all_fields_for_insert = list(filter_dict.keys()) + [k for k in data.keys() if k not in filter_dict]

        # 2. Формируем INSERT часть
        columns_str = ', '.join(all_fields_for_insert)
        placeholders_str = ', '.join(['?'] * len(all_fields_for_insert))

        # 3. Формируем ON CONFLICT часть
        # Конфликт проверяется по ВСЕМ полям из filter_dict
        conflict_columns = list(filter_dict.keys())
        conflict_clause = ', '.join(conflict_columns)

        # 4. Формируем UPDATE часть (только поля из data)
        # Для полей, которые есть и в data и в filter_dict, используем значения из data
        update_parts = []
        for field in data.keys():
            update_parts.append(f"{field} = excluded.{field}")

        # 5. Собираем полный запрос
        sql = f"""
            INSERT INTO {table} ({columns_str})
            VALUES ({placeholders_str})
            ON CONFLICT ({conflict_clause})
            DO UPDATE SET {', '.join(update_parts) if update_parts else 'NOTHING'};
            """

        # 6. Подготавливаем параметры в правильном порядке
        # Сначала значения для filter_dict полей, потом для data полей
        params = []
        for field in all_fields_for_insert:
            if field in filter_dict:
                params.append(filter_dict[field])
            else:
                params.append(data[field])


        # 3. Выполняем запрос с параметрами
        try:

            with sqlite3.connect(self.get_db_path(db), timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)  # <- Параметры передаются вторым аргументом
                conn.commit()

            # 4. Получаем результат
                row_id = cursor.lastrowid
                changes = cursor.rowcount

            print(f"Успешно! RowID: {row_id}, Затронуто строк: {changes}")

        # except sqlite3.IntegrityError as e:
        #     print(f"Ошибка: {e}")
            # Возможно, поля из filter_dict не являются уникальными

        finally:
            # conn.close()
            ...

        return row_id

    async def find_one(self, db, table, filter, *, projection=None):
        res = await self.list(db, table, filter=filter, projection=projection, limit=1, skip=0)
        return res[0] if res else None

    async def delete_one(self, db, table, filter):
        return await self.client[db][table].delete_one(filter)

    async def delete_many(self, db, table, filter):
        return await self.client[db][table].delete_many(filter)

    async def count(self, db, table, **kwargs):
        return await self.client[db][table].count_documents(
            kwargs.get('filter', {})
        )

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
        def order_to_query(_query, _order):
            if not _order:
                return _query
            res = []
            for elem in _order:
                res.append(f" {elem} {'ASC' if _order[elem] > 0 else 'DESC'}")
            return f"{query} ORDER BY {','.join(res)}"

        def row_to_dict_with_json(row):
            """Преобразует sqlite3.Row в dict с одновременным парсингом JSON полей"""
            result = {}
            for idx, column_name in enumerate(row.keys()):
                value = row[idx]

                if value is None:
                    result[column_name] = None
                elif isinstance(value, str):
                    value_stripped = value.strip()
                    if ((value_stripped.startswith('{') and value_stripped.endswith('}')) or
                            (value_stripped.startswith('[') and value_stripped.endswith(']'))):
                        try:
                            result[column_name] = json.loads(value)
                        except (json.JSONDecodeError, ValueError):
                            result[column_name] = value
                    else:
                        result[column_name] = value
                else:
                    result[column_name] = value
            return result
        try:
            projection = kwargs.get('projection', None)
            query = f"SELECT {self._projection_to_query('', projection)} FROM {table}"
            query = MongoToSQLiteConverter.filter_to_query(query, kwargs.get('filter', None))
            query = order_to_query(query, kwargs.get('', None))
            limit = kwargs.get('limit')
            skip = kwargs.get('skip', 0)
            if limit:
                query += f' LIMIT {limit}'
            if skip:
                query += f' OFFSET {skip}'

            result = []
            with sqlite3.connect(self.get_db_path(db), timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                for row in cursor.execute(query):
                    result.append(row_to_dict_with_json(row))
            return result
        except Exception as err:
            raise ExtException(parent=err, message='SQL Lite error', detail=f"{str(err)} (db {db} table {table})")

    @staticmethod
    def _projection_to_query(_query, _projection):
        if _projection:
            res = []
            for elem in _projection:
                if _projection[elem]:
                    res.append(elem)
            return f"{_query} {','.join(res)}"
        else:
            return f'{_query} *'

    @staticmethod
    def _filter_to_query(_query, _filter):
        if not _filter:
            return _query
        _where = []

        for elem in _filter:
            if _filter[elem] is None:
                _where.append(f'{elem} IS NULL')
            else:
                _where.append(f'{elem} = "{_filter[elem]}"')

        return f"{_query} WHERE {' AND '.join(_where)}"

    async def find_one_and_update(self, db, table, filter, data):
        return await self.client[db][table].find_one_and_update(filter, data)

    async def close(self):
        return


class MongoToSQLiteConverter:
    @staticmethod
    def filter_to_query(_query: str, _filter: Dict[str, Any]) -> str:
        """
        Конвертирует MongoDB-подобный фильтр в SQLite WHERE-условие

        Поддерживаемые операторы:
        - Простое равенство: {"field": "value"} - обычное сравнение
        - Оператор $in: {"field": {"$in": ["val1", "val2"]}}
        - Оператор $ne: {"field": {"$ne": "value"}}
        - Оператор $elemMatch: {"field": {"$elemMatch": "value"}} - поиск в JSON-массиве
        - Оператор $exists: {"field": {"$exists": True/False}}
        - Оператор $gt, $gte, $lt, $lte
        """
        if not _filter:
            return _query

        conditions = []

        for field, value in _filter.items():
            condition = MongoToSQLiteConverter._parse_condition(field, value)
            if condition:
                conditions.append(condition)

        if conditions:
            return f"{_query} WHERE {' AND '.join(conditions)}"
        return _query

    @staticmethod
    def _parse_condition(field: str, value: Any) -> str:
        """Парсит отдельное условие"""
        # Если значение - словарь (MongoDB операторы)
        if isinstance(value, dict):
            return MongoToSQLiteConverter._parse_operator(field, value)

        # Простое равенство - обычное сравнение (не JSON-массив)
        return MongoToSQLiteConverter._build_simple_condition(field, value)

    @staticmethod
    def _parse_operator(field: str, operator_dict: Dict[str, Any]) -> str:
        """Парсит MongoDB операторы"""
        operators = list(operator_dict.keys())

        # Оператор $elemMatch (для поиска в JSON-массиве)
        if "$elemMatch" in operators:
            elem_value = operator_dict["$elemMatch"]
            # Только для $elemMatch считаем поле JSON-массивом
            return MongoToSQLiteConverter._build_json_array_condition(field, elem_value)

        # Оператор $in
        if "$in" in operators:
            in_values = operator_dict["$in"]
            if isinstance(in_values, str):
                in_values = [in_values]
            if isinstance(in_values, list):
                # Для обычного поля (не массива)
                escaped_values = []
                for val in in_values:
                    if isinstance(val, str):
                        escaped_values.append(f"'{val}'")
                    else:
                        escaped_values.append(str(val))
                return f"{field} IN ({', '.join(escaped_values)})"

        # Оператор $ne (not equal)
        if "$ne" in operators:
            ne_value = operator_dict["$ne"]
            if ne_value is None:
                return f"{field} IS NOT NULL"
            # Обычное сравнение (не массив)
            if isinstance(ne_value, str):
                return f"{field} != '{ne_value}'"
            return f"{field} != {ne_value}"

        # Оператор $exists
        if "$exists" in operators:
            exists = operator_dict["$exists"]
            if exists:
                return f"{field} IS NOT NULL"
            else:
                return f"{field} IS NULL"

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
                if isinstance(op_value, str):
                    return f"{field} {sql_op} '{op_value}'"
                return f"{field} {sql_op} {op_value}"

        # Если оператор не распознан, считаем что это простой объект
        raise NotImplementedError(f"Unsupported operator: {operators}")

    @staticmethod
    def _build_simple_condition(field: str, value: Any) -> str:
        """Строит условие для простого поля (не JSON-массива)"""
        if value is None:
            return f"{field} IS NULL"
        elif isinstance(value, str):
            return f"{field} = '{value}'"
        elif isinstance(value, (int, float, bool)):
            value_str = str(value).lower() if isinstance(value, bool) else str(value)
            return f"{field} = {value_str}"
        else:
            # Для других типов сериализуем в JSON
            return f"{field} = '{json.dumps(value)}'"

    @staticmethod
    def _build_json_array_condition(field: str, value: Any) -> str:
        """
        Строит условие для поиска значения в JSON-массиве.
        Используется ТОЛЬКО для $elemMatch.
        """
        # Экранируем значение
        if value is None:
            # Для NULL ищем JSON null
            return f"EXISTS (SELECT 1 FROM json_each({field}) WHERE value IS NULL)"
        elif isinstance(value, str):
            escaped_value = f"'{value}'"
        elif isinstance(value, (int, float, bool)):
            escaped_value = str(value).lower() if isinstance(value, bool) else str(value)
        else:
            # Для сложных объектов
            escaped_value = f"'{json.dumps(value)}'"

        return f"EXISTS (SELECT 1 FROM json_each({field}) WHERE value = {escaped_value})"


