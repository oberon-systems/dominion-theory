people-lost =
    { $count ->
        [one] { $count } person has died.
       *[other] { $count } people have died.
    }
people-born =
    { $count ->
        [one] { $count } child was born.
       *[other] { $count } children were born.
    }
