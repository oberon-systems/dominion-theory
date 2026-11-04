proposal-camp = we camp here
proposal-winter-camp = we make a winter camp here
proposal-roam = we roam
proposal-explore = we go to see land we do not know
proposal-roam-n = we roam to the north
proposal-roam-ne = we roam to the north-east
proposal-roam-e = we roam to the east
proposal-roam-se = we roam to the south-east
proposal-roam-s = we roam to the south
proposal-roam-sw = we roam to the south-west
proposal-roam-w = we roam to the west
proposal-roam-nw = we roam to the north-west
proposal-explore-n = we explore to the north
proposal-explore-ne = we explore to the north-east
proposal-explore-e = we explore to the east
proposal-explore-se = we explore to the south-east
proposal-explore-s = we explore to the south
proposal-explore-sw = we explore to the south-west
proposal-explore-w = we explore to the west
proposal-explore-nw = we explore to the north-west
proposal-none = nothing in particular

council-opened = The council sits: { $occasion }. Most lean to: { $leader }.
council-agreed = The council meets: { $occasion }; all are of one mind: { $leader }.
occasion-first = it is the first evening
occasion-death = people have died
occasion-hunger = hunger presses
occasion-thirst = thirst presses
occasion-encounter = the band was struck
occasion-found = new land has been seen
occasion-spent = the plan has run its course
occasion-term = the month of the plan is over
occasion-season = the season has turned
council-followed = You spoke with the others: { $proposal }.
council-turned = You turned the band: { $proposal }. { NUMBER($yes, maximumFractionDigits: 1) } voices of { NUMBER($all, maximumFractionDigits: 1) } were for it.
council-outvoted = The council would not have it: { $proposal }; it chose { $winner }. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
council-abstained = You said nothing at the council. Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
proposal-worked = It went well: { $proposal }. { verdict-reason } Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
proposal-even = It came out even: { $proposal }. { verdict-reason } Your standing stays { NUMBER($status, maximumFractionDigits: 1) }.
proposal-failed = It went badly: { $proposal }. { verdict-reason } Your standing is now { NUMBER($status, maximumFractionDigits: 1) }.
verdict-reason =
    { $short ->
        [0] { "" }
        [1] Hungry { $short } day,{ " " }
       *[other] Hungry { $short } days,{ " " }
    }{ $found ->
        [0] { "" }
        [1] { $found } new cell,{ " " }
       *[other] { $found } new cells,{ " " }
    }{ $short ->
        [0] { $found ->
            [0] Stores
           *[other] stores
        }
       *[other] stores
    } { NUMBER($before, maximumFractionDigits: 1) } -> { NUMBER($after, maximumFractionDigits: 1) } { $after ->
        [1] day.
       *[other] days.
    }
plan-ended =
    { $why ->
        [reached] The band has reached the land it set out for: { $proposal }.
        [nothing] Nothing better lies that way: { $proposal }.
       *[closed] The way is closed, the band gives up: { $proposal }.
    }
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
