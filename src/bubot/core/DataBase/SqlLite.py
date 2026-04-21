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

        _id = data.get('_id')
        filter_dict = {'_id': _id} if _id else filter
        if not filter_dict:
            raise ValueError("filter_dict не может быть пустым")

        # 1. Для вставки новой записи объединяем все поля
        all_fields_for_insert = list(filter_dict.keys()) + [k for k in data.keys() if k not in filter_dict]

        # 2. Формируем INSERT часть
        columns_str = ', '.join(all_fields_for_insert)
        placeholders_str = ', '.join(['?'] * len(all_fields_for_insert))

        # 3. Формируем ON CONFLICT часть
        conflict_columns = list(filter_dict.keys())
        conflict_clause = ', '.join(conflict_columns)

        # 4. Формируем UPDATE часть
        update_parts = [f"{field} = excluded.{field}" for field in data.keys()]

        # 5. Собираем полный запрос
        sql = f"""
            INSERT INTO {table} ({columns_str})
            VALUES ({placeholders_str})
            ON CONFLICT ({conflict_clause})
            DO UPDATE SET {', '.join(update_parts) if update_parts else 'NOTHING'};
            """

        # 6. Подготавливаем параметры
        params = []
        for field in all_fields_for_insert:
            if field in filter_dict:
                params.append(filter_dict[field])
            else:
                # Для полей-ссылок извлекаем только _id
                value = data[field]
                if field.endswith('_') and isinstance(value, dict) and '_id' in value:
                    params.append(value['_id'])
                else:
                    params.append(value)

        # 7. Выполняем запрос
        try:
            with sqlite3.connect(
                    self.get_db_path(db),
                    timeout=10,
                    detect_types=sqlite3.PARSE_DECLTYPES
            ) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()

                row_id = cursor.lastrowid
                return row_id

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

        Args:
            db: имя базы данных
            table: имя таблицы
            **kwargs: параметры запроса (filter, projection, order, limit, skip)
        """

        def order_to_query(_query, _order):
            if not _order:
                return _query
            res = []
            for elem in _order:
                direction = 'ASC' if _order[elem] > 0 else 'DESC'
                res.append(f"{elem} {direction}")
            return f"{_query} ORDER BY {', '.join(res)}"

        try:
            # Получаем параметры запроса
            projection = kwargs.get('projection', None)
            filter_dict = kwargs.get('filter', {})
            order = kwargs.get('order', None)
            limit = kwargs.get('limit')
            skip = kwargs.get('skip', 0)

            # Формируем базовый SELECT запрос
            select_clause = self._projection_to_query('', projection)
            query = f"SELECT {select_clause} FROM {table}"

            # Добавляем WHERE условия с поддержкой JSON и полей-ссылок
            params = []
            if filter_dict:
                where_clause, where_params = MongoToSQLiteConverter.filter_to_sqlite(filter_dict)
                query += f" WHERE {where_clause}"
                params.extend(where_params)

            # Добавляем ORDER BY
            if order:
                query = order_to_query(query, order)

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
                    detect_types=sqlite3.PARSE_DECLTYPES  # Включаем автоматическую конвертацию типов
            ) as conn:

                # Устанавливаем row_factory для получения словарей
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(query, params)

                # Преобразуем Row в dict - JSON поля уже распарсены адаптерами!
                for row in cursor:
                    row_dict = dict(row)
                    # Для полей-ссылок (заканчиваются на _) преобразуем обратно в формат MongoDB
                    for key in list(row_dict.keys()):
                        if key.endswith('_'):
                            # Значение в SQLite - это _id (строка)
                            value = row_dict[key]
                            if value is not None:
                                # Создаем словарь с _id и добавляем поле для совместимости
                                row_dict[key] = {'_id': value}
                    result.append(row_dict)

            return result

        except Exception as err:
            raise ExtException(
                parent=err,
                message='SQL Lite error',
                detail=f"{str(err)} (db {db} table {table})"
            )

    def _build_where_clause(self, filter_dict):
        """
        Строит WHERE условие из фильтра с поддержкой JSON операторов
        Возвращает кортеж (where_clause, params)
        """
        return MongoToSQLiteConverter.filter_to_sqlite(filter_dict)

    @staticmethod
    def _projection_to_query(_query, _projection):
        """Преобразует проекцию в SQL SELECT часть"""
        if _projection:
            # Если проекция задана, выбираем только указанные поля
            fields = []
            for field, include in _projection.items():
                if include:  # только поля с True
                    fields.append(field)
            if fields:
                return f"{_query} {', '.join(fields)}"
        return f"{_query} *"

    # async def find_one_and_update(self, db, table, filter, data):
    #     return await self.client[db][table].find_one_and_update(filter, data)

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