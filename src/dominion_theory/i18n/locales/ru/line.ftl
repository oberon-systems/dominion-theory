line-people =
    { $count ->
        [one] { $count } человек
        [few] { $count } человека
       *[many] { $count } человек
    }
line-store = { NAME("resource", $resource) } { NUMBER($amount, maximumFractionDigits: 1) }
line-status = Ваш вес { NUMBER($status, maximumFractionDigits: 0) }.

line-action-camp = стоит лагерем
line-action-gather = собирает { NAME("resource", $resource, form: "accusative") }
line-action-move = идёт { NAME("line-direction", $towards) }

line-direction-north = на север
line-direction-north-east = на северо-восток
line-direction-east = на восток
line-direction-south-east = на юго-восток
line-direction-south = на юг
line-direction-south-west = на юго-запад
line-direction-west = на запад
line-direction-north-west = на северо-запад
