proposal-camp = стоим здесь
proposal-winter-camp = ставим здесь зимний лагерь
proposal-roam = кочуем
proposal-explore = идём в незнакомые земли
proposal-roam-n = кочуем на север
proposal-roam-ne = кочуем на северо-восток
proposal-roam-e = кочуем на восток
proposal-roam-se = кочуем на юго-восток
proposal-roam-s = кочуем на юг
proposal-roam-sw = кочуем на юго-запад
proposal-roam-w = кочуем на запад
proposal-roam-nw = кочуем на северо-запад
proposal-explore-n = идём в разведку на север
proposal-explore-ne = идём в разведку на северо-восток
proposal-explore-e = идём в разведку на восток
proposal-explore-se = идём в разведку на юго-восток
proposal-explore-s = идём в разведку на юг
proposal-explore-sw = идём в разведку на юго-запад
proposal-explore-w = идём в разведку на запад
proposal-explore-nw = идём в разведку на северо-запад
proposal-none = ничего особенного

council-opened = Собрался совет: { $occasion }. Большинство склоняется: { $leader }.
council-agreed = Собрался совет: { $occasion }, но все единодушны: { $leader }.
occasion-first = первый вечер
occasion-death = погибли люди
occasion-hunger = подступает голод
occasion-thirst = подступает жажда
occasion-encounter = на общину напали
occasion-found = увидели новую землю
occasion-spent = план исчерпан
occasion-term = месяц плана прошёл
occasion-season = сменилось время года
council-followed = Вы сказали то же, что и все: { $proposal }.
council-turned = Вы повернули общину: { $proposal }. За — { NUMBER($yes, maximumFractionDigits: 1) } голосов из { NUMBER($all, maximumFractionDigits: 1) }.
council-outvoted = Совет не согласился: { $proposal }; решили — { $winner }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
council-abstained = Вы промолчали на совете. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
proposal-worked = Всё вышло хорошо: { $proposal }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
proposal-even = Ни хорошо, ни плохо: { $proposal }. Ваш вес остаётся { NUMBER($status, maximumFractionDigits: 1) }.
proposal-failed = Вышло плохо: { $proposal }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
plan-ended =
    { $why ->
        [reached] Община пришла туда, куда шла: { $proposal }.
        [nothing] Дальше в ту сторону ничего лучше нет: { $proposal }.
       *[closed] Пути нет, община отступилась: { $proposal }.
    }
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
