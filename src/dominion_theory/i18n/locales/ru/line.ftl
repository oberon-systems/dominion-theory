line-people =
    { $count ->
        [one] { $count } человек
        [few] { $count } человека
       *[many] { $count } человек
    }
line-stage-child =
    { $count ->
        [one] { $count } ребёнок
        [few] { $count } ребёнка
       *[many] { $count } детей
    }
line-stage-adult =
    { $count ->
        [one] { $count } взрослый
       *[other] { $count } взрослых
    }
line-stage-elder =
    { $count ->
        [one] { $count } старик
        [few] { $count } старика
       *[many] { $count } стариков
    }
line-pregnant = беременных { $count }
line-injured = раненых { $count }
line-injured-badly = раненых { $count } (тяжело { $badly })
line-store = { NAME("resource", $resource) } { NUMBER($amount, maximumFractionDigits: 1) }
line-camp = в зимнем лагере
line-skills = умеет { $skills }
line-status = Ваш вес { NUMBER($status, maximumFractionDigits: 1) }.
line-council = Голоса: { $table }.
line-votes = { $proposal } - { $votes }

line-action-camp = стоит лагерем
line-action-build = ставит зимний лагерь
line-action-gather = собирает { $what }
line-gathered = { NAME("resource", $resource, form: "accusative") }
line-gathered-share = { NAME("resource", $resource, form: "accusative") } ({ $percent }%)
line-and = { $first } и { $last }
line-role-nanny =
    { $count ->
        [one] { $count } нянька
        [few] { $count } няньки
       *[many] { $count } нянек
    }
line-action-move = идёт { NAME("line-direction", $towards) }
line-action-roam = кочует { NAME("line-direction", $towards) }, собирая по пути

line-direction-north = на север
line-direction-north-east = на северо-восток
line-direction-east = на восток
line-direction-south-east = на юго-восток
line-direction-south = на юг
line-direction-south-west = на юго-запад
line-direction-west = на запад
line-direction-north-west = на северо-запад

play-question = Что вы скажете на совете?
play-kind-go = Кочевать
play-kind-stay-and-gather = Остаться на стоянке и собирать
play-kind-winter-camp = Поставить здесь зимний лагерь
play-kind-abstain = Промолчать
play-where = Куда идти?
play-pick = Указать направление
play-cursor = Стрелки или hjkl - выбрать клетку, Enter - идти туда, Esc - назад.
play-place =
    { $cells ->
        [1] Идём { $land }, близко
       *[other] Идём { $land }, далеко
    }
place-unknown = в незнакомые земли
play-answer = Ваш ответ: номер; пусто - промолчать
play-point = Номер или точка - два шага от общины, на восток и на юг (+3 -2); пусто - назад
play-unclear = Непонятно: { $answer }.
play-fatigue = усталость { NUMBER($fatigue, maximumFractionDigits: 2) }
play-intent = намерение: { $proposal }
play-river = река
play-gone = Общины больше нет.
play-over = Игра окончена. q - выход.
play-over-banished = Община изгнала вас: ваш вес упал до 0. Игра окончена. q - выход.
play-over-died = Общины больше нет. Игра окончена. q - выход.
play-evening = День окончен. Прочитайте, что он принёс.
play-next = дальше
play-unknown = Община не знает этого места.
play-property-water = вода
play-property-food = еда
play-property-threat = угроза
play-property-passability = проходимость
play-title-band = Община
play-title-cell = Её место
play-title-target = Цель
play-title-log = Что было
play-title-council = Совет

place-grass =
    { $quality ->
        [danger] к опасным лугам
        [river] к лугам у реки
        [rich] к сочным лугам
        [safe] к безопасным лугам
       *[plain] к лугам
    }
place-forest =
    { $quality ->
        [danger] в опасный лес
        [river] в лес у реки
        [rich] в богатый лес
        [safe] в тихий лес
       *[plain] в лес
    }
place-hills =
    { $quality ->
        [danger] на опасные холмы
        [river] на холмы у реки
        [rich] на богатые холмы
        [safe] на тихие холмы
       *[plain] на холмы
    }
place-mountain =
    { $quality ->
        [danger] в опасные горы
        [river] в горы у реки
        [rich] в богатые горы
        [safe] в тихие горы
       *[plain] в горы
    }
place-outcrops =
    { $quality ->
        [danger] к опасным скалам
        [river] к скалам у реки
        [rich] к богатым скалам
        [safe] к тихим скалам
       *[plain] к скалам
    }
place-water =
    { $quality ->
        [danger] к опасной воде
        [river] к воде
        [rich] к богатой воде
        [safe] к тихой воде
       *[plain] к воде
    }
place-shallows =
    { $quality ->
        [danger] на опасное мелководье
        [river] на мелководье у реки
        [rich] на богатое мелководье
        [safe] на тихое мелководье
       *[plain] на мелководье
    }
place-swamp =
    { $quality ->
        [danger] в опасное болото
        [river] к болоту у реки
        [rich] в богатое болото
        [safe] в тихое болото
       *[plain] в болото
    }
place-marsh =
    { $quality ->
        [danger] в опасные топи
        [river] к топям у реки
        [rich] в богатые топи
        [safe] в тихие топи
       *[plain] в прибрежные топи
    }
place-floodplain =
    { $quality ->
        [danger] в опасную пойму
        [river] в пойму у реки
        [rich] в богатую пойму
        [safe] в тихую пойму
       *[plain] в пойму
    }
place-desert =
    { $quality ->
        [danger] в опасную пустыню
        [river] к реке в пустыне
        [rich] к оазису
        [safe] в тихую пустыню
       *[plain] в пустыню
    }
place-dunes =
    { $quality ->
        [danger] в опасные дюны
        [river] к дюнам у реки
        [rich] в богатые дюны
        [safe] в тихие дюны
       *[plain] в дюны
    }
place-tundra =
    { $quality ->
        [danger] в опасную тундру
        [river] в тундру у реки
        [rich] в богатую тундру
        [safe] в тихую тундру
       *[plain] в тундру
    }
place-snow =
    { $quality ->
        [danger] в опасные снега
        [river] в снега у реки
        [rich] в богатые снега
        [safe] в тихие снега
       *[plain] в снега
    }
place-ice =
    { $quality ->
        [danger] на опасные льды
        [river] на льды у реки
        [rich] на богатые льды
        [safe] на тихие льды
       *[plain] на льды
    }
place-through-grass = по лугам
place-through-forest = по лесу
place-through-hills = по холмам
place-through-mountain = по горам
place-through-outcrops = по скалам
place-through-water = по воде
place-through-shallows = по мелководью
place-through-swamp = по болоту
place-through-marsh = по топям
place-through-floodplain = по пойме
place-through-desert = по пустыне
place-through-dunes = по дюнам
place-through-tundra = по тундре
place-through-snow = по снегам
place-through-ice = по льдам
