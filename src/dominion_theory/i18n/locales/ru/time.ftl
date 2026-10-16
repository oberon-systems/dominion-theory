time-part-morning = утро
time-part-midday = полдень
time-part-afternoon = вторая половина дня
time-part-evening = вечер
time-part-night = ночь

time-season-spring = весна
    .gender = feminine
time-season-summer = лето
    .gender = neuter
time-season-autumn = осень
    .gender = feminine
time-season-winter = зима
    .gender = feminine

time-date = день { $day }, месяц { $month }, год { $year }, { NAME("time-season", $season) }

day-started = Начался день { $day } месяца { $month }, год { $year }.
month-started = Начался месяц { $month } года { $year }; время года — { NAME("time-season", $season) }.
season-started =
    Год { $year }: { NAME("time-season", $season, form: "gender") ->
        [neuter] наступило
       *[feminine] наступила
    } { NAME("time-season", $season) }.
year-started = Начался год { $year }.
