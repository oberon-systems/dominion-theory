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
people-sickened =
    { $count ->
        [one] { $count } person is sick
       *[other] { $count } people are sick
    } { $cause ->
        [meat] from raw meat
       *[other] from bad water
    }.
people-cured =
    { $count ->
        [one] Herbs helped { $count } person.
       *[other] Herbs helped { $count } people.
    }
