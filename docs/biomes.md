# Biomes

#map #biomes

This document provides description about all in-game Biomes.

Please note, that Biomes properties/settings could not be changed in run-time!

**Biomes list**:

- `forest`
- `mountain`
- `grass`
- `woter`

___
## Properties

Each Biome has his own properties. This props depends environment settings, resources movement speed and other basics.

They all represents a general multipliers but not a real numbers!

### water

Define how many water could be collected from a Biome.

### food

Define how many food could be collected from a Biome.

### threat

Threat level for a Biome (e.g. how often wild animals will be attack a tribe).

### passability

How faster could tribe move crossing a Biome.

### resources

List of collectible resources in a cell.

___
## Environments

There is a few environment settings for each Biome. Please note that some of the settings could be not present.

- `moisture`: moisture level for a Biome, used for stick a biome with moisture layer on map generation stage.
- `elevation`: elevation level for a Biome, used for stick a biome with elevation layer on map generation stage.

___
## Visualization

Some visualization settings presented there as well.

- `color`: a default color scheme used for visualize a Biome

___
## Configuration files location

You cant find biomes configuration in [settings](src/dominion_theory/maps/settings/biomes/) directory.
