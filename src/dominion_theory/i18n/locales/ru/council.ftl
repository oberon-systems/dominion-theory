proposal-go-north = идём к земле у неподвижной звезды
proposal-go-north-east = идём к земле между неподвижной звездой и восходом
proposal-go-east = идём к земле, где встаёт солнце
proposal-go-south-east = идём к земле между восходом и полуденным солнцем
proposal-go-south = идём к земле, где солнце стоит в полдень
proposal-go-south-west = идём к земле между полуденным солнцем и закатом
proposal-go-west = идём к земле, где садится солнце
proposal-go-north-west = идём к земле между закатом и неподвижной звездой
proposal-go = идём дальше к намеченной земле
proposal-stay-and-gather = остаёмся собирать
proposal-none = ничего особенного

council-opened = Собрался совет: { $occasion }. Большинство склоняется: { $leader }.
council-agreed = Собрался совет: { $occasion }, но все единодушны: { $leader }.
occasion-first = первый вечер
occasion-death = погибли люди
occasion-arrived = община пришла туда, куда шла
occasion-hunger = подступает голод
occasion-closed = путь закрыт
occasion-restless = община хочет иного
occasion-season = сменилось время года
occasion-river = увидели реку
council-followed = Вы сказали то же, что и все: { $proposal }.
council-turned = Вы повернули общину: { $proposal }. За — { NUMBER($yes, maximumFractionDigits: 1) } голосов из { NUMBER($all, maximumFractionDigits: 1) }.
council-outvoted = Совет не согласился: { $proposal }; решили — { $winner }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
council-abstained = Вы промолчали на совете. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
proposal-worked = Всё вышло хорошо: { $proposal }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
proposal-even = Ни хорошо, ни плохо: { $proposal }. Ваш вес остаётся { NUMBER($status, maximumFractionDigits: 1) }.
proposal-failed =
    { $lost ->
        [0] Вышло плохо: { $proposal }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
        [one] Вышло плохо: { $proposal }; погиб { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
        [few] Вышло плохо: { $proposal }; погибли { $lost } человека. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
       *[many] Вышло плохо: { $proposal }; погибло { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
    }
proposal-disaster =
    { $lost ->
        [one] Беда: { $proposal }; погиб { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
        [few] Беда: { $proposal }; погибли { $lost } человека. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
       *[many] Беда: { $proposal }; погибло { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
    }
intent-ended = Пути нет, община отступилась: { $proposal }.
intent-arrived = Община пришла туда, куда шла.
seat-blamed =
    { $lost ->
        [one] В день, за который вы голосовали, погиб { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
        [few] В день, за который вы голосовали, погибли { $lost } человека. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
       *[many] В день, за который вы голосовали, погибло { $lost } человек. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
    }
seat-praised =
    { $born ->
        [one] В день, за который вы голосовали, родился { $born } ребёнок. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
        [few] В день, за который вы голосовали, родились { $born } ребёнка. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
       *[many] В день, за который вы голосовали, родилось { $born } детей. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
    }
seat-banished = Община изгнала вас. Ваш голос больше не слышен.
