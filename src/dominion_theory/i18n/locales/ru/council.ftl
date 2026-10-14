proposal-move-north = идём на неподвижную звезду
proposal-move-north-east = идём между неподвижной звездой и восходом
proposal-move-east = идём туда, где встаёт солнце
proposal-move-south-east = идём между восходом и полуденным солнцем
proposal-move-south = идём туда, где солнце стоит в полдень
proposal-move-south-west = идём между полуденным солнцем и закатом
proposal-move-west = идём туда, где садится солнце
proposal-move-north-west = идём между закатом и неподвижной звездой
proposal-rest = отдыхаем здесь
proposal-stay-and-gather = остаёмся: нам не хватает еды
proposal-none = ничего особенного

council-opened = Совет дня собрался. Большинство склоняется: { $leader }.
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
seat-banished = Община изгнала вас. Ваш голос больше не слышен.
