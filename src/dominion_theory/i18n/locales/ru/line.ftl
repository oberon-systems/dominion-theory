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
line-store = { NAME("resource", $resource) } { NUMBER($amount, maximumFractionDigits: 1) }
line-status = Ваш вес { NUMBER($status, maximumFractionDigits: 0) }.
line-council = Голоса: { $table }.
line-votes = { $proposal } - { $votes }

line-action-camp = стоит лагерем
line-action-gather = собирает { NAME("resource", $resource, form: "accusative") }
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
play-leader = { $option } (за это большинство)
play-abstain = промолчать
play-answer = Ваш ответ: номер, направление или stay; пусто - промолчать
play-unclear = Непонятно: { $answer }.
play-fatigue = усталость { NUMBER($fatigue, maximumFractionDigits: 2) }
play-intent = намерение: { $proposal }
play-river = река
play-gone = Общины больше нет.
play-over = Игра окончена. q - выход.
play-evening = День окончен. Прочитайте, что он принёс.
play-next = дальше
play-unknown = Община не знает этого места.
play-property-water = вода
play-property-food = еда
play-property-threat = угроза
play-property-passability = проходимость
play-title-band = Община
play-title-cell = Её место
play-title-log = Что было
play-title-council = Совет
