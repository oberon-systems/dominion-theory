people-lost =
    { $count ->
        [one] { $count } person has died.
       *[other] { $count } people have died.
    }
