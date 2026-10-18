from dominion_theory.content import load_params
from dominion_theory.engine.stock import Stock


def test_an_amount_joins_the_lot_of_its_day() -> None:
    stock = Stock()
    stock.add('forage', 3, 2.0)
    stock.add('forage', 3, 1.5)
    stock.add('forage', 4, 1.0)

    assert stock == {'forage': [[3.0, 3.5], [4.0, 1.0]]}
    assert stock.held('forage') == 4.5
    assert stock.held('water') == 0.0


def test_taking_empties_the_oldest_lots_first_and_gives_what_is_missing() -> None:
    stock = Stock({'forage': [[0.0, 2.0], [1.0, 3.0]]})

    assert stock.take('forage', 4.0) == 0.0
    assert stock == {'forage': [[1.0, 1.0]]}
    assert stock.take('forage', 2.5) == 1.5
    assert stock.take('water', 1.0) == 1.0
    assert stock == {'forage': [], 'water': []}


def test_lots_older_than_their_resource_keeps_spoil_and_age_slower_at_a_lower_pace() -> None:
    stock = Stock({'forage': [[0.0, 1.0], [2.0, 1.0]], 'water': [[0.0, 1.0]]})
    slow = Stock.read(stock.plain())

    stock.spoil(4, {'forage': 3, 'water': 5})
    slow.spoil(4, {'forage': 3, 'water': 5}, 0.5)

    assert stock.plain() == {'forage': [[2.0, 1.0]], 'water': [[0.0, 1.0]]}
    assert slow.plain() == {'forage': [[0.0, 1.0], [2.0, 1.0]], 'water': [[0.0, 1.0]]}


def test_weight_and_amounts_go_by_the_resource() -> None:
    params = load_params()
    stock = Stock({'water': [[0.0, 2.0]], 'forage': [[0.0, 1.0], [1.0, 1.0]]})
    weights = {name: params.resources[name].weight_kg for name in ('forage', 'water')}

    assert stock.amounts() == {'forage': 2.0, 'water': 2.0}
    assert stock.weight(params.resources) == 2.0 * weights['forage'] + 2.0 * weights['water']


def test_a_lot_of_goods_keeps_its_quality_and_joins_only_its_like() -> None:
    stock = Stock()
    stock.add('stones', 3, 1.0, 0.6)
    stock.add('stones', 3, 2.0, 0.7)
    stock.add('stones', 3, 0.5, 0.6)
    stock.add('stones', 4, 1.0, 0.6)

    assert stock == {'stones': [[3.0, 1.5, 0.6], [3.0, 2.0, 0.7], [4.0, 1.0, 0.6]]}
    assert stock.held('stones') == 4.5


def test_goods_wear_out_by_their_quality_and_the_stock_says_what_went() -> None:
    stock = Stock({'stones': [[0.0, 1.0, 0.5], [0.0, 2.0, 1.0]], 'forage': [[0.0, 3.0]]})

    assert stock.spoil(30, {'stones': 60, 'forage': 3}) == {'stones': 1.0, 'forage': 3.0}
    assert stock.plain() == {'forage': [], 'stones': [[0.0, 2.0, 1.0]]}
    assert stock.spoil(31, {'stones': 60, 'forage': 3}) == {}


def test_a_part_leaves_with_its_days_and_qualities_and_joins_another_stock_in_order() -> None:
    stock = Stock({'stones': [[0.0, 1.0, 0.5], [2.0, 2.0, 0.9]]})
    kit = Stock({'stones': [[1.0, 1.0], [2.0, 0.5, 0.9]]})

    parted = stock.part('stones', 1.5)
    kit.join(parted)

    assert parted == {'stones': [[0.0, 1.0, 0.5], [2.0, 0.5, 0.9]]}
    assert stock == {'stones': [[2.0, 1.5, 0.9]]}
    assert kit == {'stones': [[0.0, 1.0, 0.5], [1.0, 1.0], [2.0, 1.0, 0.9]]}
