obj_meta_keys (list)
  * key (str) - key name
  * fields (list) - string index field (val1, val2, ...)
    * label - title field
    * path - path to value in object data
    * format - format value to string
    * not_null (boolean, default true) - is false null add to index

Ключ считается заполненным, только если получены значения всех полей

В объекте ключи хранятся в индексируемом поле.
Поле индексируется key, value0, value...

* keys
  * key
  * value0
  * value...


example
``` 
[{
    "key": "doc",
    "fields": [
        {
            "label": "Номер",
            "path": "Номер"
        },
        {
            "label": "Дата",
            "path": "Дата",
            "format": "date"
        },
        {
            "label": "Контрагент",
            "path": "Контрагент",
            "format": "link"
        },
        {
            "label": "Организация",
            "path": "НашаОрганизация",
            "format": "link"
        }
    ]
}]
```