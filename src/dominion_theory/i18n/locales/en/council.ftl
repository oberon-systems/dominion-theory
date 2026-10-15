proposal-move-north = we go towards the star that does not move
proposal-move-north-east = we go between the unmoving star and the sunrise
proposal-move-east = we go where the sun rises
proposal-move-south-east = we go between the sunrise and the midday sun
proposal-move-south = we go where the sun stands at midday
proposal-move-south-west = we go between the midday sun and the sunset
proposal-move-west = we go where the sun sets
proposal-move-north-west = we go between the sunset and the unmoving star
proposal-stay-and-gather = we stay and gather
proposal-none = nothing in particular

council-opened = The council of the day sits. Most lean to: { $leader }.
council-agreed = The council needs no vote, all are of one mind: { $leader }.
council-followed = You spoke with the others: { $proposal }.
council-turned = You turned the band: { $proposal }. { NUMBER($yes, maximumFractionDigits: 1) } voices of { NUMBER($all, maximumFractionDigits: 1) } were for it.
council-outvoted = The council would not have it: { $proposal }; it chose { $winner }. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
council-abstained = You said nothing at the council. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
proposal-worked = It went well: { $proposal }. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
proposal-failed =
    { $lost ->
        [0] It went badly: { $proposal }. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
        [one] It went badly: { $proposal }; { $lost } person was lost. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
       *[other] It went badly: { $proposal }; { $lost } people were lost. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
    }
proposal-disaster =
    { $lost ->
        [one] It ended in disaster: { $proposal }; { $lost } person was lost. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
       *[other] It ended in disaster: { $proposal }; { $lost } people were lost. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
    }
intent-ended = The way is closed, the band gives up: { $proposal }.
seat-blamed =
    { $lost ->
        [one] { $lost } person died on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
       *[other] { $lost } people died on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
    }
seat-praised =
    { $born ->
        [one] { $born } child was born on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
       *[other] { $born } children were born on a day you voted for. Your standing is now { NUMBER($status, maximumFractionDigits: 0) }.
    }
seat-banished = The band has turned you out. Your voice is heard no more.
