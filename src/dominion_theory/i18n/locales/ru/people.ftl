people-lost =
    { $count ->
        [one] Погиб { $count } человек.
        [few] Погибли { $count } человека.
       *[many] Погибло { $count } человек.
    }
