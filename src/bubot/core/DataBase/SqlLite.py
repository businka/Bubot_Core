import os
import sqlite3
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, KeyNotFound


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

        try:
            projection = kwargs.get('projection', None)
            query = f"SELECT {self._projection_to_query('', projection)} FROM {table}"
            query = self._filter_to_query(query, kwargs.get('filter', None))
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
                    result.append(dict(row))
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
