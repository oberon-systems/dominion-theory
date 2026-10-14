line-people =
    { $count ->
        [one] { $count } person
       *[other] { $count } people
    }
line-store = { NAME("resource", $resource) } { NUMBER($amount, maximumFractionDigits: 1) }
line-status = Your standing is { NUMBER($status, maximumFractionDigits: 0) }.
line-council = The votes: { $table }.
line-votes = { $proposal } - { $votes }

line-action-camp = camps
line-action-gather = gathers { NAME("resource", $resource) }
line-action-move = walks { NAME("line-direction", $towards) }

line-direction-north = north
line-direction-north-east = north-east
line-direction-east = east
line-direction-south-east = south-east
line-direction-south = south
line-direction-south-west = south-west
line-direction-west = west
line-direction-north-west = north-west
