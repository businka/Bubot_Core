[ISO/IEC 30118](https://www.iso.org/contents/data/standard/07/42/74243.html)

# 3 Термины, определения, символы и сокращения

## 3.1 Термины и определения

### 3.1.1 Атомные измерения

шаблон проектирования, который гарантирует, что клиент может получить доступ только к свойствам связанных ресурсов атомарно, то есть как единая группа

### 3.1.2 Клиент

логический объект, который обращается к ресурсу на сервере

### 3.1.3 Сбор

Ресурс, который содержит ноль или более ссылок

### 3.1.4 Общие свойства

Свойства, указанные для всех ресурсов

### 3.1.5 Составное устройство

Устройство, которое моделируется как несколько типов устройств; с каждым компонентом Тип устройства

выставлен как коллекция

### 3.1.6 Источник конфигурации

облачная или сервисная сеть или локальный файл только для чтения, который содержит и предоставляет конфигурацию соответствующая информация для устройств

### 3.1.7 Основные ресурсы

те ресурсы, которые определены в данной спецификации

### 3.1.8 Интерфейс по умолчанию

Интерфейс, используемый для генерации ответа, когда Интерфейс опущен в запросе

### 3.1.9 Устройство

логический объект, который принимает одну или несколько ролей (например, клиент, сервер)

Примечание 1 к записи: На физической платформе может существовать несколько устройств.

### 3.1.10 Тип устройства

определение с уникальным именем, указывающее минимальный набор типов ресурсов, которые поддерживает устройство

Примечание 1 к записи: Тип устройства предоставляет подсказку о том, что такое устройство, такое как подсветка или вентилятор, для использования во время обнаружения ресурса.

### 3.1.11 Обнаруживаемый ресурс

Ресурс, который указан в «/ oic / res»

### 3.1.12 Конечная точка

источник или назначение сообщений с запросами и ответами для данного набора транспортных протоколов

Примечание 1 к записи: Например, набор протоколов транспорта будет CoAP через UDP через IPv6.

### 3.1.13 Сущность

аспект физического мира, который открывается через устройство

Примечание 1 к записи: Примером может быть только ED.

### 3.1.14 Структура

набор связанных функций и взаимодействий, определенных в данной спецификации, которые обеспечивают совместимость с широким спектром сетевых устройств, включая IoT

### 3.1.15 Интерфейс

предоставляет представление и допустимые ответы на ресурсе

### 3.1.16 Самоанализ

механизм определения возможностей размещенных ресурсов устройства

### 3.1.17 Данные устройства самоанализа (IDD)

данные, которые описывают полезную нагрузку для каждого реализованного метода Ресурсов, которые составляют Устройство

Примечание 1 к записи: См. Раздел 1 1.8 для всех требований и исключений

### 3.1.18 Ссылки

расширяет типизированные веб-ссылки в соответствии с IETF RFC 5988

### 3.1.19. Не обнаруживаемый ресурс

Ресурс, который не указан в «/ oic / res». Ресурс может быть достигнут по ссылке, которая передается другим ресурсом. Например, ресурс, связанный с ресурсом коллекции, не обязательно должен быть указан в «/ oic / res», так как при обходе ресурса коллекции будет обнаружен ресурс, реализованный на устройстве.

### 3.1.20 Устройство без OCF

Устройство, которое не соответствует требованиям устройства OCF

### 3.1.21 Уведомление

механизм информирования клиента об изменениях состояния ресурса в ресурсе

### 3.1.22 Соблюдать

мониторинг ресурса путем отправки запроса RETRIEVE, который кэшируется сервером, на котором размещен ресурс, и обрабатывается при каждом изменении этого ресурса.

### 3.1.23 Параметр

элемент, предоставляющий метаданные о ресурсе, на который ссылается целевой URI ссылки

### 3.1.24 Частичное ОБНОВЛЕНИЕ

запрос UPDATE на ресурс, который включает в себя подмножество свойств, видимых через интерфейс, применяемый для типа ресурса

### 3.1.25 Физическое устройство

физическая вещь, на которой выставлены Устройства

### 3.1.26 Платформа

физическое устройство, содержащее одно или несколько устройств

### 3.1.27 Ресурс

представляет сущность, смоделированную и предоставляемую платформой

### 3.1.28 Каталог ресурсов

набор описаний ресурсов, где фактические ресурсы хранятся на серверах, внешних по отношению к устройству, на котором размещен каталог ресурсов, что позволяет выполнять поиск этих ресурсов

Примечание 1 к записи: Эта функциональность может использоваться неактивными серверами или серверами, которые предпочитают не прослушивать и не отвечать на многоадресные запросы напрямую.

### 3.1.29 Ресурсный интерфейс

квалификация разрешенных запросов на Ресурсе

### 3.1.30 Недвижимость

значительный аспект или параметр ресурса, включая метаданные, которые предоставляются через ресурс

### 3.1.31 Тип ресурса

уникально названное определение класса свойств и взаимодействий, которые поддерживаются этим классом

Примечание 1 к записи: Каждый ресурс имеет свойство «rt», значением которого является уникальное имя типа ресурса.

### 3.1.32 Сцена

статическая сущность, которая хранит набор определенных значений свойств для коллекции ресурсов

Примечание 1 к записи: Сцена - это заданная настройка набора ресурсов, каждый из которых имеет заранее определенное значение для свойства, которое должно измениться.

### 3.1.33 Коллекция сцен

ресурс коллекции, содержащий перечисление возможных значений сцены и текущее значение сцены

Примечание 1 к записи: Значения членов Ресурса Коллекции Сцены для Членов Сцены.

### 3.1.34 Участник сцены

Ресурс, который содержит сопоставления Значений Сцены со значениями свойства в ресурсе

### 3.1.35 Значение сцены

Перечислитель Сцен, представляющий состояние, в котором Ресурс может быть

### 3.1.36 Безопасная конечная точка

Конечная точка с защищенным соединением (например, CoAPS)

### 3.1.37 Сервер

Устройство с ролью предоставления информации о состоянии ресурса и облегчения удаленного взаимодействия с его ресурсами

Примечание 1 к записи: Может быть реализован сервер для предоставления клиентам не-OCF-ресурсов (раздел 5 .6)

### 3.1.38 Незащищенная конечная точка

Конечная точка с незащищенным соединением (например, CoAP)

### 3.1.39 Вертикальный тип ресурса

Тип ресурса в вертикальной спецификации домена

Примечание 1 к записи: Примером Вертикального Типа Ресурса будет «oic.r.switch.binary».

## 3.2 Символы и сокращения

### 3.2.1 ACL

Список контроля доступа

Нет 1 для записи: детали определены в OCF Security.

### 3.2.2 BLE

Bluetooth Low Energy

### 3.2.3 CBOR

Краткое представление двоичного объекта

### 3.2.4 CoAP

Протокол ограниченного применения

### 3.2.5 CoAPS

Безопасный ограниченный протокол приложения

### 3.2.6 DTLS

Безопасность дейтаграммы на транспортном уровне

Примечание 1 к записи: Детали определены в IETF RFC 6 347.

### 3.2.7 EXI

Эффективный обмен XML

### 3.2.8 IP

протокол Интернета

### 3.2.9 IRI

Интернационализированные идентификаторы ресурсов

### 3.2.10 Интернет-провайдер

Интернет-провайдер

### 3.2.11 JSON

Нотация объектов JavaScript

### 3.2.12 mDNS

Многоадресная служба доменных имен

### 3.2.13 MTU

Максимальная единица передачи

### 3.2.14 NAT

Трансляция сетевых адресов

### 3.2.15 OCF

Open Connectivity Foundation организация, создавшая эту спецификацию

### 3.2.16 RAML

Язык моделирования RESTful API

### 3.2.17 ОТДЫХ

Изобразительное State Transfer

### 3.2.18 RESTful

REST-совместимые веб-сервисы

### 3.2.19 UDP

Протокол пользовательских датаграмм

Примечание 1 к записи: Детали определены в IETF RFC 7 68.

### 3.2.20 URI

Единый идентификатор ресурса

### 3.2.21 URN

Единое имя ресурса

### 3.2.22 UTC

Всемирное координированное время

### 3.2.23 UUID

Универсальный уникальный идентификатор

### 3.2.24 XML

расширяемый язык разметки

## 3.3 Соглашения

 В этой спецификации ряд терминов, условий, механизмов, последовательностей, параметров, событий, состояний или аналогичных терминов печатаются с первой буквой каждого слова в верхнем регистре и остальными строчными буквами (например, Сетевая архитектура). Любое использование этих слов в нижнем регистре имеет нормальное техническое английское значение.

##  3.4 Типы данных

Ресурсы определяются с использованием типов данных, полученных из значений JSON, как определено в IETF RFC 7159. Однако Ресурс может перегрузить определенное значение JSON, чтобы указать конкретное подмножество значения JSON, используя ключевые слова проверки, определенные в Проверке схемы JSON.

Среди других ключевых слов проверки, раздел 7 в JSON Schema Validation определяет ключевое слово «format» с рядом атрибутов формата, таких как «uri» и «date-time», и ключевое слово «pattern» с регулярным выражением, которое можно использовать для проверить строку. В этом разделе определяются шаблоны, которые доступны для использования при описании ресурсов OCF. Имена шаблонов могут использоваться в тексте спецификации, где могут встречаться имена в формате JSON. Фактические схемы JSON должны использовать вместо этого тип и шаблон JSON.

Для всех строк, определенных в таблице 1 ниже, тип 

JSON \- это строка



Строки должны быть закодированы как UTF-8, если не указано иное.

В схеме JSON «maxLength» для строки указывает максимальное количество символов, а не октетов. Однако «maxLength» также указывает максимальное число октетов. Если для строки «maxLength» не определено, то максимальная длина должна составлять 64 октета