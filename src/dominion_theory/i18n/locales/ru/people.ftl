people-lost =
    { $count ->
        [one] Погиб { $count } человек.
        [few] Погибли { $count } человека.
       *[many] Погибло { $count } человек.
    }
people-born =
    { $count ->
        [one] Родился { $count } ребёнок.
        [few] Родились { $count } ребёнка.
       *[many] Родилось { $count } детей.
    }
people-injured =
    { $count ->
        [one] Ранен { $count } человек.
        [few] Ранены { $count } человека.
       *[many] Ранено { $count } человек.
    }
people-sickened =
    { $count ->
        [one] Заболел { $count } человек
        [few] Заболели { $count } человека
       *[many] Заболело { $count } человек
    } { $cause ->
        [meat] от сырого мяса
       *[other] от плохой воды
    }.
people-cured =
    { $count ->
        [one] Травы помогли { $count } человеку.
       *[other] Травы помогли { $count } людям.
    }
