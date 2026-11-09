# ValqLegends

Thirteen legendary weapons for Paper 1.21.11 (Java 21). Every weapon has a passive effect, a **primary** ability (right click)
and a **secondary** ability (sneak + right click), each with its own cooldown. Nothing breaks or burns blocks in the world.

Works on its own. Other plugins can use the small API: `LegendsPlugin.create(id)`, `LegendsPlugin.ids()`, `LegendsPlugin.idOf(item)`.
Made for the VALQAUYM server (battle royale loot) and used together with its ValqCore plugin, but has no dependency on it.

## Weapons

| id | Name | Base item | Passive | Right click | Shift + right click |
|---|---|---|---|---|---|
| `crimson_fang` | Клык крови | netherite_sword | Вампиризм: 15% урона возвращается вам здоровьем | Рывок крови: рывок вперёд, рубит всех на пути (8 s) | Кровотечение: наносит врагам в 8 блоках иссушение (25 s) |
| `inferno_scythe` | Коса пекла | netherite_hoe | Огнеупорность: полный иммунитет к огню и лаве | Огненная дуга: конус пламени перед вами (7 s) | Метеор: огненный шар обрушивается туда, куда вы смотрите (30 s) |
| `soul_staff` | Посох душ | blaze_rod | — | Болт души: быстрый снаряд, 8 урона (3 s) | Всевидящее око: подсвечивает всех живых в 30 блоках (35 s) |
| `warden_mace` | Булава стража | mace | Сердце стража: +4 сердца, пока булава в руке | Ударная волна: отбрасывает и ранит всех в 6 блоках (10 s) | Щит стража: 8 поглощённых сердец на 6 секунд (30 s) |
| `storm_trident` | Громовой трезубец | trident | Аура бури: мелкие молнии вокруг | Цепная молния: перескакивает по 4 ближайшим врагам (9 s) | Ливень молний: град ударов по области, куда вы смотрите (40 s) |
| `thorn_blade` | Шипастый клинок | netherite_sword | — | Хватка лозы: притягивает цель к вам (8 s) | Ядовитый шип: яд и урон по цели (20 s) |
| `time_daggers` | Кинжалы времени | iron_sword | — | Остановка времени: замораживает цель на 3 секунды (14 s) | Перемотка: вернёт вас на 5 секунд назад со здоровьем того момента (45 s) |
| `umbral_knives` | Теневые ножи | netherite_sword | — | Жемчуг бездны: короткий прыжок в точку взгляда (5 s) | Веер ножей: три быстрых снаряда (20 s) |
| `void_axe` | Секира бездны | netherite_axe | Пустота: замедляет врагов рядом с вами | Затягивание: притягивает всех в 8 блоках (12 s) | Разлом: короткий телепорт вперёд (15 s) |
| `frost_brand` | Ледяной клинок | diamond_sword | Холод: удар замедляет цель | Ледяная вспышка: замедляет и ранит всех в 6 блоках (10 s) | Ледяной шаг: скорость и защита от падения на 5 секунд (25 s) |
| `gale_blade` | Клинок бури | diamond_sword | — | Прыжок ветра: мощный прыжок вперёд и вверх (6 s) | Вихрь: вращающийся удар по всем рядом (18 s) |
| `earth_hammer` | Молот земли | iron_axe | — | Удар о землю: подбрасывает и ранит врагов вокруг (11 s) | Землетрясение: замедляет всех в 10 блоках (35 s) |
| `life_staff` | Жезл жизни | stick | Дыхание жизни: медленная регенерация, пока жезл в руке | Исцеление: возвращает вам 8 сердец (12 s) | Благословение: лечит союзников в 8 блоках на 6 сердец (25 s) |

## Commands

- `/legend list`: list ids
- `/legend give <id> [player]`
- `/legend gui`: click a weapon to take it
- `/legend reload`

Permission: `legends.admin` (default: op).

## Build

```bash
PAPER_API=path/to/paper-api-1.21.11-R0.1-SNAPSHOT.jar PAPER_LIBS=path/to/libraries bash build.sh
```

The weapons use `custom_model_data` 1 to 13, so a resource pack can give each its own model.

## License

MIT
