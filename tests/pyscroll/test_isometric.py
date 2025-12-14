import pytest

from pyscroll.isometric import vector2_to_iso, vector3_to_iso


@pytest.fixture
def offset_fixture():
    return (5, -3)


@pytest.mark.parametrize(
    "vector, expected",
    [
        ((1, 1, 0), (0, 1)),
        ((2, 1, 0), (1, 1)),
        ((1, 2, 0), (-1, 1)),
        ((1, 1, 1), (0, 0)),
        ((-1, -1, 0), (0, -1)),
        ((-2, -1, 0), (-1, -2)),
        ((-1, -2, 0), (1, -2)),
        ((-1, -1, -1), (0, 0)),
        ((0, 0, 0), (0, 0)),
        ((100, 100, 0), (0, 100)),
        ((200, 100, 0), (100, 150)),
        ((100, 200, 0), (-100, 150)),
        ((100, 100, 100), (0, 0)),
    ],
)
def test_vector3_to_iso(vector, expected):
    assert vector3_to_iso(vector) == expected


@pytest.mark.parametrize(
    "vector, expected",
    [
        ((1, 1), (0, 1)),
        ((2, 1), (1, 1)),
        ((1, 2), (-1, 1)),
        ((0, 0), (0, 0)),
        ((-1, -1), (0, -1)),
        ((-2, -1), (-1, -2)),
        ((-1, -2), (1, -2)),
        ((100, 100), (0, 100)),
        ((200, 100), (100, 150)),
        ((100, 200), (-100, 150)),
    ],
)
def test_vector2_to_iso(vector, expected):
    assert vector2_to_iso(vector) == expected


@pytest.mark.parametrize(
    "vector, offset, expected",
    [
        ((1, 1, 0), (5, -3), (5, -2)),
        ((2, 1), (5, -3), (6, -2)),
    ],
)
def test_iso_with_offset(vector, offset, expected):
    if len(vector) == 3:
        assert vector3_to_iso(vector, offset) == expected
    else:
        assert vector2_to_iso(vector, offset) == expected


@pytest.mark.parametrize(
    "vector",
    [
        (10**6, 10**6, 0),
        (10**6, 0, 10**6),
        (-(10**6), -(10**6), 0),
    ],
)
def test_vector3_large_values(vector):
    result = vector3_to_iso(vector)
    assert isinstance(result, tuple)
    assert all(isinstance(x, int) for x in result)


@pytest.mark.parametrize(
    "vector",
    [
        (10**6, 10**6),
        (10**6, 0),
        (-(10**6), -(10**6)),
    ],
)
def test_vector2_large_values(vector):
    result = vector2_to_iso(vector)
    assert isinstance(result, tuple)
    assert all(isinstance(x, int) for x in result)


@pytest.mark.parametrize(
    "bad_input",
    [
        (1, 2),  # too short for vector3
        (1, 2, 3, 4),  # too long
        "not a tuple",  # wrong type
    ],
)
def test_vector3_invalid_inputs(bad_input):
    with pytest.raises(ValueError):
        vector3_to_iso(bad_input)


@pytest.mark.parametrize(
    "bad_input",
    [
        (1,),  # too short for vector2
        (1, 2, 3),  # too long
        None,  # wrong type
    ],
)
def test_vector2_invalid_inputs(bad_input):
    with pytest.raises(ValueError):
        vector2_to_iso(bad_input)
