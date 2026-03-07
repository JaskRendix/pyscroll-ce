import pytest

from pyscroll.common import vector2_to_iso, vector3_to_iso


@pytest.fixture
def offset_fixture():
    return (5, -3)


@pytest.mark.parametrize(
    "vector, expected",
    [
        pytest.param((1, 1, 0), (0, 1), id="basic_1_1_0"),
        pytest.param((2, 1, 0), (1, 1), id="basic_2_1_0"),
        pytest.param((1, 2, 0), (-1, 1), id="basic_1_2_0"),
        pytest.param((1, 1, 1), (0, 0), id="with_z_1"),
        pytest.param((-1, -1, 0), (0, -1), id="negative_basic"),
        pytest.param((-2, -1, 0), (-1, -2), id="negative_2_1"),
        pytest.param((-1, -2, 0), (1, -2), id="negative_1_2"),
        pytest.param((-1, -1, -1), (0, 0), id="negative_with_z"),
        pytest.param((0, 0, 0), (0, 0), id="zero"),
        pytest.param((100, 100, 0), (0, 100), id="large_100"),
        pytest.param((200, 100, 0), (100, 150), id="large_200_100"),
        pytest.param((100, 200, 0), (-100, 150), id="large_100_200"),
        pytest.param((100, 100, 100), (0, 0), id="large_with_z"),
    ],
)
def test_vector3_to_iso(vector, expected):
    assert vector3_to_iso(vector) == expected


@pytest.mark.parametrize(
    "vector, expected",
    [
        pytest.param((1, 1), (0, 1), id="basic_1_1"),
        pytest.param((2, 1), (1, 1), id="basic_2_1"),
        pytest.param((1, 2), (-1, 1), id="basic_1_2"),
        pytest.param((0, 0), (0, 0), id="zero"),
        pytest.param((-1, -1), (0, -1), id="negative_basic"),
        pytest.param((-2, -1), (-1, -2), id="negative_2_1"),
        pytest.param((-1, -2), (1, -2), id="negative_1_2"),
        pytest.param((100, 100), (0, 100), id="large_100"),
        pytest.param((200, 100), (100, 150), id="large_200_100"),
        pytest.param((100, 200), (-100, 150), id="large_100_200"),
    ],
)
def test_vector2_to_iso(vector, expected):
    assert vector2_to_iso(vector) == expected


@pytest.mark.parametrize(
    "vector, offset, expected",
    [
        pytest.param((1, 1, 0), (5, -3), (5, -2), id="vector3_with_offset"),
        pytest.param((2, 1), (5, -3), (6, -2), id="vector2_with_offset"),
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
        pytest.param((10**6, 10**6, 0), id="large_xy"),
        pytest.param((10**6, 0, 10**6), id="large_xz"),
        pytest.param((-(10**6), -(10**6), 0), id="negative_large"),
    ],
)
def test_vector3_large_values(vector):
    result = vector3_to_iso(vector)
    assert isinstance(result, tuple)
    assert all(isinstance(x, int) for x in result)


@pytest.mark.parametrize(
    "vector",
    [
        pytest.param((10**6, 10**6), id="large_xy"),
        pytest.param((10**6, 0), id="large_x"),
        pytest.param((-(10**6), -(10**6)), id="negative_large"),
    ],
)
def test_vector2_large_values(vector):
    result = vector2_to_iso(vector)
    assert isinstance(result, tuple)
    assert all(isinstance(x, int) for x in result)


@pytest.mark.parametrize(
    "bad_input",
    [
        pytest.param((1, 2), id="too_short"),
        pytest.param((1, 2, 3, 4), id="too_long"),
        pytest.param("not a tuple", id="wrong_type"),
    ],
)
def test_vector3_invalid_inputs(bad_input):
    with pytest.raises(ValueError):
        vector3_to_iso(bad_input)


@pytest.mark.parametrize(
    "bad_input",
    [
        pytest.param((1,), id="too_short"),
        pytest.param((1, 2, 3), id="too_long"),
        pytest.param(None, id="wrong_type"),
    ],
)
def test_vector2_invalid_inputs(bad_input):
    with pytest.raises(ValueError):
        vector2_to_iso(bad_input)
