line-people =
    { $count ->
        [one] { $count } person
       *[other] { $count } people
    }
line-stage-child =
    { $count ->
        [one] { $count } child
       *[other] { $count } children
    }
line-stage-adult =
    { $count ->
        [one] { $count } adult
       *[other] { $count } adults
    }
line-stage-elder =
    { $count ->
        [one] { $count } elder
       *[other] { $count } elders
    }
line-pregnant = { $count } with child
line-injured = { $count } injured
line-store = { NAME("resource", $resource) } { NUMBER($amount, maximumFractionDigits: 1) }
line-status = Your standing is { NUMBER($status, maximumFractionDigits: 0) }.
line-council = The votes: { $table }.
line-votes = { $proposal } - { $votes }

line-action-camp = camps
line-action-gather = gathers { NAME("resource", $resource) }
line-action-move = walks { NAME("line-direction", $towards) }
line-action-roam = roams { NAME("line-direction", $towards) }, foraging on the way

line-direction-north = north
line-direction-north-east = north-east
line-direction-east = east
line-direction-south-east = south-east
line-direction-south = south
line-direction-south-west = south-west
line-direction-west = west
line-direction-north-west = north-west

play-question = What do you say at the council?
play-leader = { $option } (most lean to it)
play-abstain = say nothing
play-answer = Your answer: a number, a direction or stay; an empty line to say nothing
play-unclear = Not understood: { $answer }.
play-fatigue = fatigue { NUMBER($fatigue, maximumFractionDigits: 2) }
play-intent = intent: { $proposal }
play-river = a river
play-gone = The band is no more.
play-over = The game is over. Press q to leave.
play-evening = The day is over. Read what it brought.
play-next = go on
play-unknown = The band does not know this place.
play-property-water = water
play-property-food = food
play-property-threat = threat
play-property-passability = passability
play-title-band = The band
play-title-cell = Its place
play-title-log = What happened
play-title-council = The council
