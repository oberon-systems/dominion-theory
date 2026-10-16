proposal-go-north = we go to the land towards the star that does not move
proposal-go-north-east = we go to the land between the unmoving star and the sunrise
proposal-go-east = we go to the land where the sun rises
proposal-go-south-east = we go to the land between the sunrise and the midday sun
proposal-go-south = we go to the land where the sun stands at midday
proposal-go-south-west = we go to the land between the midday sun and the sunset
proposal-go-west = we go to the land where the sun sets
proposal-go-north-west = we go to the land between the sunset and the unmoving star
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
