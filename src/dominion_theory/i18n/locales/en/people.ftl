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
people-injured =
    { $count ->
        [one] { $count } person is injured.
       *[other] { $count } people are injured.
    }
