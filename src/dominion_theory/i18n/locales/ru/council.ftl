proposal-move-north = идём на неподвижную звезду
proposal-move-north-east = идём между неподвижной звездой и восходом
proposal-move-east = идём туда, где встаёт солнце
proposal-move-south-east = идём между восходом и полуденным солнцем
proposal-move-south = идём туда, где солнце стоит в полдень
proposal-move-south-west = идём между полуденным солнцем и закатом
proposal-move-west = идём туда, где садится солнце
proposal-move-north-west = идём между закатом и неподвижной звездой
proposal-stay-and-gather = остаёмся собирать
proposal-none = ничего особенного

council-opened = Собрался совет: { $occasion }. Большинство склоняется: { $leader }.
council-agreed = Собрался совет: { $occasion }, но все единодушны: { $leader }.
occasion-first = первый вечер
occasion-death = погибли люди
occasion-hunger = подступает голод
occasion-closed = путь закрыт
occasion-restless = община хочет иного
occasion-season = сменилось время года
occasion-river = увидели реку
council-followed = Вы сказали то же, что и все: { $proposal }.
council-turned = Вы повернули общину: { $proposal }. За — { NUMBER($yes, maximumFractionDigits: 1) } голосов из { NUMBER($all, maximumFractionDigits: 1) }.
council-outvoted = Совет не согласился: { $proposal }; решили — { $winner }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
council-abstained = Вы промолчали на совете. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
proposal-worked = Всё вышло хорошо: { $proposal }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
proposal-failed =
    { $lost ->
        [0] Вышло плохо: { $proposal }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
        [one] Вышло плохо: { $proposal }; погиб { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
        [few] Вышло плохо: { $proposal }; погибли { $lost } человека. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
       *[many] Вышло плохо: { $proposal }; погибло { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
    }
proposal-disaster =
    { $lost ->
        [one] Беда: { $proposal }; погиб { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
        [few] Беда: { $proposal }; погибли { $lost } человека. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
       *[many] Беда: { $proposal }; погибло { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
    }
intent-ended = Пути нет, община отступилась: { $proposal }.
seat-blamed =
    { $lost ->
        [one] В день, за который вы голосовали, погиб { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
        [few] В день, за который вы голосовали, погибли { $lost } человека. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
       *[many] В день, за который вы голосовали, погибло { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
    }
seat-praised =
    { $born ->
        [one] В день, за который вы голосовали, родился { $born } ребёнок. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
        [few] В день, за который вы голосовали, родились { $born } ребёнка. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
       *[many] В день, за который вы голосовали, родилось { $born } детей. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 0) }.
    }
seat-banished = Община изгнала вас. Ваш голос больше не слышен.
