proposal-go-grass = we go to the meadows
proposal-go-forest = we go into the forest
proposal-go-hills = we go onto the hills
proposal-go-mountain = we go into the mountains
proposal-go-outcrops = we go to the rocks
proposal-go-water = we go to the water
proposal-go-shallows = we go into the shallows
proposal-go-swamp = we go into the swamp
proposal-go-marsh = we go into the coastal marshes
proposal-go-floodplain = we go onto the floodplain
proposal-go-desert = we go into the desert
proposal-go-dunes = we go into the dunes
proposal-go-tundra = we go into the tundra
proposal-go-snow = we go into the snow
proposal-go-ice = we go onto the ice
proposal-go-through-grass = we go on through the meadows
proposal-go-through-forest = we go on through the forest
proposal-go-through-hills = we go on over the hills
proposal-go-through-mountain = we go on through the mountains
proposal-go-through-outcrops = we go on over the rocks
proposal-go-through-water = we go on over the water
proposal-go-through-shallows = we go on through the shallows
proposal-go-through-swamp = we go on through the swamp
proposal-go-through-marsh = we go on through the marshes
proposal-go-through-floodplain = we go on along the floodplain
proposal-go-through-desert = we go on through the desert
proposal-go-through-dunes = we go on over the dunes
proposal-go-through-tundra = we go on across the tundra
proposal-go-through-snow = we go on through the snow
proposal-go-through-ice = we go on across the ice
proposal-go-unknown = we go into land we do not know
proposal-go = we go on to the land we set out for
proposal-stay-and-gather = we stay and gather
proposal-none = nothing in particular

council-opened = The council sits: { $occasion }. Most lean to: { $leader }.
council-agreed = The council meets: { $occasion }; all are of one mind: { $leader }.
occasion-first = it is the first evening
occasion-death = people have died
occasion-arrived = the band has reached the land it went to
occasion-hunger = hunger presses
occasion-closed = the way is closed
occasion-restless = the band wants another way
occasion-season = the season has turned
occasion-river = a river has been seen
council-followed = You spoke with the others: { $proposal }.
council-turned = You turned the band: { $proposal }. { NUMBER($yes, maximumFractionDigits: 1) } voices of { NUMBER($all, maximumFractionDigits: 1) } were for it.
council-outvoted = The council would not have it: { $proposal }; it chose { $winner }. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
council-abstained = You said nothing at the council. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
proposal-worked = It went well: { $proposal }. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
proposal-even = It came out even: { $proposal }. Your standing stays { NUMBER($status, maximumFractionDigits: 1) }.
proposal-failed =
    { $lost ->
        [0] It went badly: { $proposal }. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
        [one] It went badly: { $proposal }; { $lost } person was lost. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
       *[other] It went badly: { $proposal }; { $lost } people were lost. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
    }
proposal-disaster =
    { $lost ->
        [one] It ended in disaster: { $proposal }; { $lost } person was lost. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
       *[other] It ended in disaster: { $proposal }; { $lost } people were lost. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
    }
intent-ended = The way is closed, the band gives up: { $proposal }.
intent-arrived = The band has reached the land it set out for.
seat-blamed =
    { $lost ->
        [one] { $lost } person died on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
       *[other] { $lost } people died on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
    }
seat-praised =
    { $born ->
        [one] { $born } child was born on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
       *[other] { $born } children were born on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
    }
seat-banished = The band has turned you out. Your voice is heard no more.
