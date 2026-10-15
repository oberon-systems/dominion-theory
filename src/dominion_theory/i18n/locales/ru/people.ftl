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
