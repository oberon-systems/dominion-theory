proposal-go-grass = идём на луга
proposal-go-forest = идём в лес
proposal-go-hills = идём на холмы
proposal-go-mountain = идём в горы
proposal-go-outcrops = идём к скалам
proposal-go-water = идём к воде
proposal-go-shallows = идём на мелководье
proposal-go-swamp = идём в болото
proposal-go-marsh = идём в прибрежные топи
proposal-go-floodplain = идём в пойму
proposal-go-desert = идём в пустыню
proposal-go-dunes = идём в дюны
proposal-go-tundra = идём в тундру
proposal-go-snow = идём в снега
proposal-go-ice = идём на льды
proposal-go-through-grass = идём по лугам
proposal-go-through-forest = идём по лесу
proposal-go-through-hills = идём по холмам
proposal-go-through-mountain = идём по горам
proposal-go-through-outcrops = идём по скалам
proposal-go-through-water = идём по воде
proposal-go-through-shallows = идём по мелководью
proposal-go-through-swamp = идём по болоту
proposal-go-through-marsh = идём по топям
proposal-go-through-floodplain = идём по пойме
proposal-go-through-desert = идём по пустыне
proposal-go-through-dunes = идём по дюнам
proposal-go-through-tundra = идём по тундре
proposal-go-through-snow = идём по снегам
proposal-go-through-ice = идём по льдам
proposal-go-unknown = идём в незнакомые земли
proposal-go = идём дальше к намеченной земле
proposal-stay-and-gather = остаёмся собирать
proposal-winter-camp = ставим здесь зимний лагерь
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
proposal-failed = Вышло плохо: { $proposal }. Ваш вес теперь { NUMBER($status, maximumFractionDigits: 1) }.
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
