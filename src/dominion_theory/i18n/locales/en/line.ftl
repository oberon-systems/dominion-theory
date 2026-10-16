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
line-injured-badly = { $count } injured ({ $badly } badly)
line-store = { NAME("resource", $resource) } { NUMBER($amount, maximumFractionDigits: 1) }
line-status = Your standing is { NUMBER($status, maximumFractionDigits: 1) }.
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
play-kind-go = Roam
play-kind-stay-and-gather = Stay at the camp and gather
play-kind-abstain = Say nothing
play-where = Where to go?
play-pick = Point the way
play-cursor = Arrows or hjkl pick a cell, Enter goes there, Esc goes back.
play-place =
    { $cells ->
        [1] We go { $land }, near
       *[other] We go { $land }, far
    }
place-unknown = into land we do not know
play-answer = Your answer: a number; an empty line to say nothing
play-point = A number, or a point as two steps from the band, east then south (+3 -2); an empty line goes back
play-unclear = Not understood: { $answer }.
play-fatigue = fatigue { NUMBER($fatigue, maximumFractionDigits: 2) }
play-intent = intent: { $proposal }
play-river = a river
play-gone = The band is no more.
play-over = The game is over. Press q to leave.
play-over-banished = The band has turned you out: your standing fell to 0. The game is over. Press q to leave.
play-over-died = The band is no more. The game is over. Press q to leave.
play-evening = The day is over. Read what it brought.
play-next = go on
play-unknown = The band does not know this place.
play-property-water = water
play-property-food = food
play-property-threat = threat
play-property-passability = passability
play-title-band = The band
play-title-cell = Its place
play-title-target = The target
play-title-log = What happened
play-title-council = The council

place-grass =
    { $quality ->
        [danger] to the dangerous meadows
        [river] to the meadows by the river
        [rich] to the lush meadows
        [safe] to the safe meadows
       *[plain] to the meadows
    }
place-forest =
    { $quality ->
        [danger] into the dangerous forest
        [river] to the forest by the river
        [rich] into the rich forest
        [safe] into the quiet forest
       *[plain] into the forest
    }
place-hills =
    { $quality ->
        [danger] onto the dangerous hills
        [river] to the hills by the river
        [rich] onto the rich hills
        [safe] onto the quiet hills
       *[plain] onto the hills
    }
place-mountain =
    { $quality ->
        [danger] into the dangerous mountains
        [river] to the mountains by the river
        [rich] into the rich mountains
        [safe] into the quiet mountains
       *[plain] into the mountains
    }
place-outcrops =
    { $quality ->
        [danger] to the dangerous rocks
        [river] to the rocks by the river
        [rich] to the rich rocks
        [safe] to the quiet rocks
       *[plain] to the rocks
    }
place-water =
    { $quality ->
        [danger] to the dangerous water
        [river] to the water
        [rich] to the rich water
        [safe] to the quiet water
       *[plain] to the water
    }
place-shallows =
    { $quality ->
        [danger] into the dangerous shallows
        [river] to the shallows by the river
        [rich] into the rich shallows
        [safe] into the quiet shallows
       *[plain] into the shallows
    }
place-swamp =
    { $quality ->
        [danger] into the dangerous swamp
        [river] to the swamp by the river
        [rich] into the rich swamp
        [safe] into the quiet swamp
       *[plain] into the swamp
    }
place-marsh =
    { $quality ->
        [danger] into the dangerous marshes
        [river] to the marshes by the river
        [rich] into the rich marshes
        [safe] into the quiet marshes
       *[plain] into the coastal marshes
    }
place-floodplain =
    { $quality ->
        [danger] onto the dangerous floodplain
        [river] to the floodplain by the river
        [rich] onto the rich floodplain
        [safe] onto the quiet floodplain
       *[plain] onto the floodplain
    }
place-desert =
    { $quality ->
        [danger] into the dangerous desert
        [river] to the river in the desert
        [rich] to an oasis
        [safe] into the quiet desert
       *[plain] into the desert
    }
place-dunes =
    { $quality ->
        [danger] into the dangerous dunes
        [river] to the dunes by the river
        [rich] into the rich dunes
        [safe] into the quiet dunes
       *[plain] into the dunes
    }
place-tundra =
    { $quality ->
        [danger] into the dangerous tundra
        [river] to the tundra by the river
        [rich] into the rich tundra
        [safe] into the quiet tundra
       *[plain] into the tundra
    }
place-snow =
    { $quality ->
        [danger] into the dangerous snow
        [river] to the snow by the river
        [rich] into the rich snow
        [safe] into the quiet snow
       *[plain] into the snow
    }
place-ice =
    { $quality ->
        [danger] onto the dangerous ice
        [river] to the ice by the river
        [rich] onto the rich ice
        [safe] onto the quiet ice
       *[plain] onto the ice
    }
place-through-grass = on through the meadows
place-through-forest = on through the forest
place-through-hills = on over the hills
place-through-mountain = on through the mountains
place-through-outcrops = on over the rocks
place-through-water = on over the water
place-through-shallows = on through the shallows
place-through-swamp = on through the swamp
place-through-marsh = on through the marshes
place-through-floodplain = on along the floodplain
place-through-desert = on through the desert
place-through-dunes = on over the dunes
place-through-tundra = on across the tundra
place-through-snow = on through the snow
place-through-ice = on across the ice
