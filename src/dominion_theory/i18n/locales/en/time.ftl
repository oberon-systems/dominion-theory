time-part-morning = morning
time-part-midday = midday
time-part-afternoon = afternoon
time-part-evening = evening
time-part-night = night

time-season-spring = spring
time-season-summer = summer
time-season-autumn = autumn
time-season-winter = winter

time-date = day { $day }, month { $month }, year { $year }, { NAME("time-season", $season) }

day-started = Day { $day } of month { $month }, year { $year }, begins.
month-started = Month { $month } of year { $year } begins; the season is { NAME("time-season", $season) }.
season-started = Year { $year }: { NAME("time-season", $season) } has come.
year-started = Year { $year } begins.
