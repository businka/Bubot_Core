# Class Obj
Объект - минимальная самостоятельная сущность с которой взаимодействует пользователь.
Критериеми для выделения объекта являются:
* необходимость отслеживания изменений

Новый объекты создаются путем наследования.

## Формы
Формы используются для описания вариантов представления данных объекта.
Если объекту требуются свои формы:
  * класс статический атрибут file = __file__
  * Рядом с классом должна быть папака forms в которой перечислены все формы - файлы {Имя формы}.form.json

### Реквизиты формы
  Весь файл формы передается на клиет при чтении формы
  
  Реквизиты формы испльзуемые классом объекта  
#### projection

Cписок реквизитов которые нужны форме из базы данных, словарь {имя поля}: {1 / 0} надо или нет

Например для организации ссылки на объект в Mongo нужно кроме идентификатора вернуть заголовок

    projection: { "_id": 1, "title": 1 }

Если нужно вернуть все поля
    
    projection: null
    
Если файла формы нет, или в форме нет свойства projection, методы будут возвращать только идентификатор записи
 