# geodata-trimmed

Обрезанные `geoip.dat` и `geosite.dat` для Xray на роутере с малым объёмом ОЗУ.

Исходник — [runetfreedom/russia-v2ray-rules-dat](https://github.com/runetfreedom/russia-v2ray-rules-dat).
В нём 1543 категории и 92 МБ, из которых 63 МБ занимают `ru-blocked-all` и
`antifilter-download`. Здесь остаются только категории, перечисленные в
`categories/`, — те, что реально встречаются в правилах маршрутизации.

| файл | исходник | результат |
|---|---|---|
| geosite.dat | 73,70 МБ | 5,42 МБ |
| geoip.dat | 18,35 МБ | 1,03 МБ |

## Как это работает

`trim-geodata.py` обходит записи верхнего уровня protobuf и копирует побайтово
те, чей код категории есть в списке. Домены, атрибуты и CIDR внутри записей не
пересобираются, поэтому поведение правил не меняется.

Сборка идёт по расписанию в ночь на воскресенье и публикует релиз, только если
содержимое изменилось. Рядом с каждым файлом кладётся `.sha256sum` — по нему
`rule_update.lua` в PassWall2 понимает, что скачивать заново не нужно.

## Подключение к PassWall2

```
uci set passwall2.@global_rules[0].geoip_url='https://github.com/gn1024/geodata-trimmed/releases/latest/download/geoip.dat'
uci set passwall2.@global_rules[0].geosite_url='https://github.com/gn1024/geodata-trimmed/releases/latest/download/geosite.dat'
uci commit passwall2
```

Настройки лежат в `/etc/config/passwall2` и переживают обновление пакета.

## Изменение списка категорий

Списки в `categories/geosite.txt` и `categories/geoip.txt` должны совпадать с
тем, что встречается в конфиге Xray как `geosite:<имя>` и `geoip:<имя>`:

```sh
grep -o 'geosite:[a-zA-Z0-9_-]*' /tmp/etc/passwall2/acl/default.json | sort -u
grep -o 'geoip:[a-zA-Z0-9_-]*' /tmp/etc/passwall2/acl/default.json | sort -u
```

Сборка падает, если запрошенной категории нет в исходнике, — так опечатка или
переименование наверху не превратятся в тихо пустое правило.

## Локальный запуск

```sh
python3 trim-geodata.py geosite.dat out.dat --sha256 --strict $(grep -vE '^\s*(#|$)' categories/geosite.txt)
```
