[Copyright Open Connectivity Foundation, Inc. © 2016-2018. All rights Reserved](https://openconnectivity.org/)

# 6 Идентификация и адресация

## 6.1 Введение

Для правильного и эффективного взаимодействия между элементами фреймворка для каждого элемента требуется идентификатор, имя и адрес.

Идентификатор однозначно идентифицирует элемент в контексте или домене. Контекст или домен могут определяться использованием или приложением. Ожидается, что идентификатор будет неизменным в течение жизненного цикла этого элемента и недвусмыслен в контексте или области.

Адрес используется для определения места, способа или средства достижения или доступа к элементу, чтобы взаимодействовать с ним. Адрес может изменяться в зависимости от контекста.

Имя - это дескриптор, который отличает элемент от других элементов в структуре. Имя может быть изменено в течение жизненного цикла этого элемента.

Могут быть методы или схемы разрешения, которые позволяют определить любой из них на основе знания одного или нескольких других (например, определить имя из адреса или адреса от имени).

Каждый из этих аспектов может быть определен отдельно для множества контекстов (например, контекст может быть слоем в стеке). Таким образом, адрес может быть URL-адресом для адресации ресурса и IP-адресом для адресации на уровне подключения. В некоторых ситуациях оба этих адреса потребуются.

Например, чтобы выполнить операцию RETRIEVE (раздел 8.3) в конкретном представлении ресурса, клиенту необходимо знать адрес целевого ресурса и адрес сервера, через который этот ресурс открывается.

В контексте или области использования имя или адрес можно использовать в качестве идентификатора или наоборот. Например, URL-адрес может использоваться как идентификатор ресурса и обозначается как URI.

Остальная часть этого раздела обсуждает идентификатор, адрес и именование с точки зрения модели ресурсов и взаимодействий, которые должны поддерживаться моделью ресурсов. Примерами взаимодействий являются взаимодействия RESTful, то есть операция CRUDN (раздел 8) ресурса. Также описано их сопоставление с транспортными протоколами, например CoAP.

## 6.2 Идентификация

Идентификатор недвусмыслен в контексте или области использования. Существует множество схем, которые могут использоваться для генерации идентификатора, обладающего требуемыми свойствами. Идентификатор может быть контекстно-зависимым, поскольку ожидается, что идентификатор будет и должен быть однозначным только в пределах этого контекста или домена. Идентификатор также может быть контекстно-независимым, если эти идентификаторы гарантированно будут однозначными во всех контекстах и доменах как пространственно, так и временно.

Контекстные идентификаторы могут быть определены с помощью простых схем, таких как монотонное перечисление, или могут быть определены путем перегрузки адреса или имени, например, IP-адрес может быть идентификатором в частном домене за шлюзом в интеллектуальном доме. С другой стороны, контекстно-независимые идентификаторы требуют более сильной схемы, которая выводит универсально уникальные идентификаторы, например, любую из версий универсально уникальных идентификаторов (UUID). Контекстно-зависимый идентификатор также может быть сгенерирован с использованием иерархии доменов, где корень иерархии идентифицирован с помощью UUID, а поддомены могут генерировать контекстно-независимый идентификатор, объединяя идентификаторы контекста для этого домена с контекстно-независимым идентификатором их родителя.

### 6.2.1 Идентификация ресурсов и адресация

Ресурс может быть идентифицирован с использованием URI и адресован тем же URI, если URI является URL-адресом. В некоторых случаях ресурсу может понадобиться идентификатор, отличный от URI; в этом случае ресурс может иметь свойство, значение которого является идентификатором. Когда URI находится в форме URL-адреса, URI может использоваться для адресации ресурса.

URI OCF основан на общей форме URI, как определено в IETF RFC 3986, следующим образом:

```
<scheme>://<authority>/<path>?<query>
```

В частности, URI OCF указан в следующем виде:

```
ocf://<authority>/<path>?<query>
```

Ниже приводится описание значений, которые принимает каждый компонент.

scheme для URI используется "ocf". Схема "ocf" представляет семантику, определения и использование, как определено в этом документе. Если URI имеет часть, предшествующую "//" (двойная косая черта), опущенная, тогда должна быть принята схема "ocf".

Каждое связывание транспорта отвечает за указание того, как URI OCF преобразуется в URI транспортного протокола перед отправкой по сети запрашивающим. Точно так же на стороне приемника каждое привязку к транспорту отвечает за указание того, как URI OCF преобразуется из URI транспортного протокола, прежде чем передать его на уровень модели ресурсов на приемнике.

authority URI OCF - это идентификатор устройства ("di"), как определено в [Безопасность OCF], Сервера.

path - это строка, которая однозначно идентифицирует или ссылается на ресурс в контексте Сервера. В этой версии спецификации путь не должен содержать pct-кодированные символы, отличные от ASCII, или символы NUL. Путь должен предшествовать "/" (косая черта). Путь может иметь разделенные сегменты "/" (косой чертой) для удобства чтения человеком. В контексте OCF сегменты, разделенные "/" (косой чертой), рассматриваются как одна строка, которая напрямую ссылается на ресурсы (т. е. на плоскую структуру) и не анализируется как иерархия. На сервере путь или некоторая подстрока в пути может быть сокращена с помощью хеширования или какой-либо другой схемы, если результирующая ссылка уникальный в контексте хоста.

После создания пути клиент, обращающийся к ресурсу или получателю URI, должен использовать этот путь как непрозрачную строку и не должен анализировать, чтобы вывести структуру, организацию или семантику.

query должен содержать список сегментов <name> = <value> (ака "пара значений имен"), каждый из которых разделяется символом "&" (амперсанд). Строка запроса будет сопоставлена с соответствующим синтаксисом протокола, используемого для обмена сообщениями. (например, CoAP).

URI может быть либо

- Абсолютным или
- Относительным

Создание URI:

URI может быть определен Клиентом, который является создателем этого ресурса. Такой URI может быть относительным или абсолютным (полностью квалифицированным). Относительный URI должен относиться к устройству, на котором он размещен. В качестве альтернативы, URI может быть сгенерирован сервером этого ресурса автоматически на основе заранее определенного соглашения или организации ресурсов на основе интерфейса, основанного на некоторых правилах или в отношении разных корней или оснований.

Использование URI:

Абсолютную ссылку на путь URI следует рассматривать как непрозрачную строку, и Клиент не должен вызывать явную или подразумеваемую структуру в URI - URI - это просто адрес. Также рекомендуется, чтобы устройства, на которых размещен ресурс, обрабатывали URI каждого ресурса как непрозрачную строку, которая адресует только этот ресурс. (например, URI /a и /a/b рассматриваются как разные адреса, а ресурс b не может быть истолкован как дочерний ресурс a).

## 6.3 Пространство имен:

Относительный префикс URI "/oic/" зарезервирован как пространство имен для URI, определенных в спецификациях OCF, и не должно использоваться для URI, которые не определены в спецификациях OCF.

## 6.4 Сетевая адресация

Ниже перечислены адреса, используемые в этой спецификации:

• IP адрес

IP-адрес используется, когда устройство использует настроенный IP-интерфейс.

Когда устройство имеет только идентификационную информацию своего однорангового узла, необходим механизм разрешения для сопоставления идентификатора с соответствующим адресом.