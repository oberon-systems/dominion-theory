# Band

#unit #band #epoch0

**Band**  is a first in-game unit with a simple functions: gather water or food and grow population. It could not create any tools neither collect huge amount of resources.

For each **Band** we determinate some sets of states, actions, properties and so, for example:

- **[state](#state)**: represents a current **Band** state (e.g. normal, starved etc);
- **[action](#action):** represents what **Band** doing at the moment;
- **[population](#population):** how bigger the Band, one of the most important factors;
- **[properties](#properties):** list of **Band**'s properties (speed, carrying values);
- **[resources](#resources):** list of resources that **Band** owns;

___

## State

- `normal`: no any features or threats applied to a **Band**;
- `starvation`: there is not enough of food;
- `thirst`: there is no enough of water;
- `tiredness`: rest required for a **Band**;

___

## Action

- `move`: move to another location;
- `camp`: set a camp in a current location;
- `gather`: gather resources in a current location;

___

## Population

min: 10
max: 150

___

## Properties

- `speed`: 1 cell per 5 hours, reduced by 9% for each 10 people;
- `carrying`: 5 kilo per 1 population;
- `gathering`:
  - `water`: 1 units per population per `tick`
  - `food`: 1 units per population per `tick`
- `consumption`:
  - water: 1 unit per 1 population per 24h;
  - food: 2 units per 1 population per 24h;

___

## Resources

- `water`: just a water it-self;
- `food`:  `forage`, a simple and not very good food;
