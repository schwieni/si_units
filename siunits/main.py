from collections import defaultdict
from dataclasses import dataclass
# from enum import Enum
import operator
from typing import Callable, Dict, List, Tuple, Union

# import base_units


@dataclass
class BaseUnit:
    id: int  # Must be unique.
    _name: str  # lowercase.  eg "kilogram"
    abbrev: str  # caps sensitive. eg "kg"
    quantity: str  # lowercase. eg "mass"

    def name(self):  # For compatibility with DerivedUnit
        return self._name

    def _text_eq(self, other: Union['BaseUnit', 'DerivedUnit']) -> bool:
        """For testing"""
        return self.name == other.name and self.abbrev == other.abbrev and \
            self.quantity == other.quantity

    def __lt__(self, other):
        """Used for sorting units"""
        return self.abbrev < other.abbrev

    def __add__(self, other: Union['BaseUnit', int, float]) -> 'Composite':
        if isinstance(other, int) or isinstance(other, float):
            return Composite(1 + other, self)
        elif type(self) == type(other):
            if self == other:
                return Composite(2, self)
            else:
                raise TypeError(f'Addition: the BaseUnits must be identical! Error: {self} + {other}')
        else:
            raise NotImplemented(f"Addition not implemented between types {type(self)} + {type(other)}")

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        return self.__add__(other)

    def __sub__(self, other: Union['BaseUnit', int, float]) -> 'Composite':
        if isinstance(other, int) or isinstance(other, float):
            return Composite(1 - other, self)
        elif type(self) == type(other):
            if self == other:
                return Composite(0, self)
            else:
                raise TypeError(f'Subtraction: the BaseUnits must be identical! Error: {self} - {other}')
        else:
            raise NotImplemented(f"Subtraction not implemented between types {type(self)} - {type(other)}")

    def __rsub__(self, other):
        return self.__sub__(other)

    def __neg__(self):
        return Composite(-1, self)

    def __isub__(self, other):
        return self.__sub__(other)

    def __mul__(self, other: Union['BaseUnit', 'DerivedUnit', 'Composite', int, float]) -> Union['DerivedUnit', 'Composite']:
        return _mul_helper(self, other, {self: 1}, operator.add, "·")

    __rmul__ = __mul__

    def __imul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other: Union['BaseUnit', 'DerivedUnit', 'Composite', int, float]) \
            -> Union['DerivedUnit', 'Composite']:
        if isinstance(other, Composite):
            return Composite(1/other.coef, self * other.unit ** -1)
        else:
            return _mul_helper(self, other, {self: 1}, operator.sub, "/")

    def __rtruediv__(self, other: Union['BaseUnit', 'DerivedUnit', 'Composite', int, float]) \
            -> Union['DerivedUnit', 'Composite']:
        if isinstance(other, int) or isinstance(other, float):
            return Composite(other, self ** -1)
        else:
            raise NotImplemented(f'Division not implemented between types {type(other)} / {type(self)}')

    def __idiv__(self, other):
        return self.__truediv__(other)

    def __int__(self):
        return 1

    def __float__(self):
        return 1

    def __pow__(self, power: int) -> 'DerivedUnit':
        return _pow(self, power)

    def __eq__(self, other: Union['BaseUnit', 'DerivedUnit']) -> bool:
        if not other:
            return False
        elif isinstance(other, BaseUnit):
            return self.id == other.id
        elif isinstance(other, DerivedUnit):
            return other.base_units == [Assoc(self, 1)]
        else:
            raise NotImplemented("Can only compare BaseUnit to another "
                                 "BaseUnit, or DerivedUnit")

    def __hash__(self):
        return hash((self.id,))

    def __repr__(self):
        return f"{self._name} ({self.abbrev}), {self.quantity}"

    
@dataclass
class Assoc:
    """
    Associates a base unit, and its power
    """
    # todo: Currently, this wrapper doesn't do anything. Consider removing.
    unit: BaseUnit
    power: int

    def __repr__(self):
        return f"{self.unit.abbrev}: {self.power}"

    def __lt__(self, other):
        if self.unit == other.unit:
            return self.power < other.power
        else:
            return self.unit < other.unit


@dataclass
class DerivedUnit:
    # See comments on fields of same name in BaseUnit.
    _name_tokens: List[Tuple[str, int]]  # name, power
    abbrev: str
    base_units: List[Assoc]
    quantity: str  # todo infer this?

    def name(self) -> str:
        """This method keeps the units used in constructing it,
        rather than decompose into base units."""
        result_map = defaultdict(int)
        for name_, power in self._name_tokens:
            result_map[name_] += power
        return "·".join(k_ + _power_text(v_) for k_, v_ in result_map.items())

    def name_base(self) -> str:
        """This method decomposes into base units."""
        pass

    def rename(self, name: str, abbrev: str, quantity: str) -> 'DerivedUnit':
        """Useful for creating custom units composed of other units."""
        return DerivedUnit(name, abbrev, [(u.unit, u.power) for u in self.base_units], quantity)

    def _text_eq(self, other: Union['BaseUnit', 'DerivedUnit']) -> bool:
        """For testing"""
        return self.name() == other.name() and self.abbrev == other.abbrev and \
            self.quantity == other.quantity

    def __init__(
        self, 
        name: str,
        abbrev: str, 
        base_units: List[Tuple[BaseUnit, int]],
        quantity: str
    ) -> 'DerivedUnit':

        """This method exists to consolidate base units, if there are duplicates."""
        self._name_tokens = [(name, 1)]
        self.abbrev = abbrev

        base_units2 = [Assoc(b[0], b[1]) for b in base_units]
        self.base_units = [Assoc(k_, v_) for k_, v_ in _to_unit_map(base_units2).items()]

        self.quantity = quantity

    def __add__(self, other: Union['DerivedUnit', int, float]) -> 'Composite':
        if isinstance(other, int) or isinstance(other, float):
            return Composite(1 + other, self)
        elif isinstance(other, DerivedUnit):
            if self == other:  # check for identical units
                return Composite(2, self)
            else:
                raise TypeError(f'Addition: the BaseUnits must be identical! Error: {self} + {other}')
        else:
            raise NotImplemented(f"Addition not implemented between types {type(self)} + {type(other)}")

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other: Union['DerivedUnit', int, float]) -> 'Composite':
        if isinstance(other, int) or isinstance(other, float):
            return Composite(1 - other, self)
        elif isinstance(other, DerivedUnit):
            if self == other:  # check for identical units
                return Composite(0, self)
            else:
                raise TypeError(f'Subtraction: the BaseUnits must be identical! Error: {self} - {other}')
        else:
            raise NotImplemented(f"Subtraction not implemented between types {type(self)} - {type(other)}")

    def __rsub__(self, other):
        return self.__sub__(other)

    # def __add__(self, other) -> 'Composite':
    #
    #     if type(self) is not type(other):
    #         raise TypeError(f'Addition: types do not match! "{type(self)}" + "{type(other)}" is not implemented!')
    #     # check if base units match
    #     if _to_unit_map(self.base_units) == _to_unit_map(other.base_units):
    #         return Composite(2, self)
    #     else:
    #         raise TypeError(f'Addition: units do not match: {self.base_units} + {other.base_units}')

    def __mul__(self, other: Union[BaseUnit, 'DerivedUnit', 'Composite', int, float])\
            -> Union['DerivedUnit', 'Composite']:
        return _mul_helper(self, other, _to_unit_map(self.base_units), operator.add, "·")

    __rmul__ = __mul__

    def __truediv__(self, other: Union[BaseUnit, 'DerivedUnit', 'Composite', int, float])\
            -> Union['DerivedUnit', 'Composite']:
        # if isinstance(other, BaseUnit) or isinstance(other, DerivedUnit):
        #     return DerivedUnit(self / other)
        # elif isinstance(other, Composite):
        #     return Composite(1/other.coef, self / other.unit)
        # elif isinstance(other, int) or isinstance(other, float):
        #     return Composite(1/other, self)
        # else:
        #     raise TypeError(f'Division of {type(self)} / {type(other)} is not implemented!')
        if isinstance(other, Composite):
            return Composite(1/other.coef, self / other.unit)
        else:
            return _mul_helper(self, other, _to_unit_map(self.base_units), operator.sub, "/")

    def __rtruediv__(self, other: Union['BaseUnit', 'DerivedUnit', int, float])\
            -> Union['DerivedUnit', 'Composite']:
        if isinstance(other, int) or isinstance(other, float):
            return Composite(other, self ** -1)
        else:
            NotImplemented(f'Division not implemented between types {type(other)} / {type(self)}')

    # todo inplace mul and div.

    def __int__(self):
        return 1

    def __float__(self):
        return 1

    def __pow__(self, power: int) -> 'DerivedUnit':
        return _pow(self, power)

    def __eq__(self, other: Union['DerivedUnit', int, float]) -> bool:
        """Note that this only tests units."""
        # check special cases for int and float == 1
        if isinstance(other, int):
            if other == 1:
                return True
            else:
                return False
        elif isinstance(other, float):
            if other == 1.0:
                return True
            else:
                return False
        else:
            return _to_unit_map(self.base_units) == _to_unit_map(other.base_units)

    def __repr__(self):
        return f"{self.name()} ({self.abbrev}), {sorted(self.base_units, key=lambda a: a.unit.id)}"


def _to_unit_map(units: List[Assoc]) -> Dict[BaseUnit, int]:
    """Used to dedupe a list of Assoc"""
    result = {}
    for u in units:
        if u.unit in result.keys():
            result[u.unit] += 1
        else:
            result[u.unit] = u.power
    return {k_: v_ for k_, v_ in result.items() if v_ != 0}


def _base_description(units: List[Assoc]) -> str:
    """This reconstructs the description from base units."""
    unit_map = _to_unit_map(units)
    # todo: Sort by power, high to low?
    return "·".join(unit.abbrev + _power_text(power) for unit, power in unit_map.items())


def _handle_description(units: List[Union[BaseUnit, DerivedUnit]]) -> Tuple[str, str, str]:
    """This allows us to reconstruct using derived units, instead of just
    base ones."""
    # todo

    return


@dataclass
class Composite:
    # todo: Combine with DerivedUnit ?
    coef: Union[float, int]
    unit: Union[BaseUnit, DerivedUnit]

    def __mul__(self, other: Union[BaseUnit, DerivedUnit, int, float]) -> 'Composite':
        if isinstance(other, BaseUnit) or isinstance(other, DerivedUnit):
            return Composite(self.coef, self.unit * other)
        elif isinstance(other, Composite):
            return Composite(self.coef * other.coef, self.unit * other.unit)
        elif isinstance(other, int) or isinstance(other, float):
            return Composite(self.coef * other, self.unit)
        else:
            raise TypeError("Multiplication must be by a unit or number")

    __rmul__ = __mul__

    def __truediv__(self, other) -> 'Composite':
        if isinstance(other, BaseUnit) or isinstance(other, DerivedUnit):
            return Composite(self.coef, self.unit / other)
        elif isinstance(other, Composite):
            return Composite(self.coef / other.coef, self.unit / other.unit)
        elif isinstance(other, int) or isinstance(other, float):
            return Composite(self.coef / other, self.unit)
        else:
            raise NotImplemented(f'Division not implemented between types {type(self)} / {type(other)}!')

    def __rtruediv__(self, other):
        if isinstance(other, BaseUnit) or isinstance(other, DerivedUnit):
            return Composite(1 / self.coef, other / self.unit)
        elif isinstance(other, Composite):
            return Composite(other.coef / self.coef, other.unit / self.unit)
        elif isinstance(other, int) or isinstance(other, float):
            return Composite(other / self.coef, 1 / self.unit)
        else:
            raise NotImplemented(f'Division not implemented between types {type(other)} / {type(self)}!')

    def __pow__(self, power: int):
        return _pow(self, power)

    def __add__(self, other):
        if isinstance(other, Composite):
            if self.unit == other.unit:
                return Composite(self.coef + other.coef, self.unit)
            else:
                raise TypeError(f"Adding two different units: {self.unit} + {other.unit}")
        elif isinstance(other, int) or isinstance(other, float):
            # allow to add normal numbers and accept that the units are identical
            return Composite(self.coef + other, self.unit)
        else:
            raise NotImplemented(f'Addition not implemented between types: {type(self)} + {type(other)}!')
            # raise NotImplemented("Additions must have similar types. Maybe this is not implemented yet?")

    def __sub__(self, other: Union[int, float, 'Composite']) -> 'Composite':
        if isinstance(other, Composite):
            if self.unit == other.unit:
                return Composite(self.coef - other.coef, self.unit)
            else:
                raise TypeError(f"Subtracting two different units: {self.unit} - {other.unit}")
        elif isinstance(other, int) or isinstance(other, float):
            # allow to subtract normal numbers and accept that the units are identical
            return Composite(self.coef - other, self.unit)
        else:
            raise NotImplemented(f'Subtraction not implemented between types: {type(self)} - {type(other)}!')

    def __eq__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return self.coef == other
        elif isinstance(other, Composite):
            return self.coef == other.coef and self.unit == other.unit
        elif isinstance(other, DerivedUnit):
            return self.coef == 1 and self.unit == other
        else:
            raise NotImplemented(f'Equality not implemented between types: {type(self)} == {type(other)}!')

    def __int__(self):
        """
        Integer representation.
        :return: the coefficient as int value
        """
        return self.coef.__int__()

    def __float__(self):
        """
        Float representation. Allows for native math.sin() etc.
        :return: the coefficient as float value
        """
        return self.coef.__float__()

    # def __radd__(self, other: 'Composite'):
    #     pass

    def __repr__(self):
        return f"{self.coef}{self.unit.abbrev}"


def _mul_helper(
    self: Union['BaseUnit', 'DerivedUnit', int, float],
    other: Union['BaseUnit', 'DerivedUnit', int, float],
    init_map: Dict[Union['BaseUnit', 'DerivedUnit'], int],
    op: Callable,
    symbol: str
) -> [Composite, DerivedUnit]:
    """Avoids repetition between __mul__ and __truediv__"""
    unit_map = init_map

    if isinstance(other, BaseUnit):
        if other in unit_map.keys():
            unit_map[other] = op(unit_map[other], 1)
        else:
            unit_map[other] = -1 if symbol == "/" else 1

    elif isinstance(other, DerivedUnit):
        for u in other.base_units:
            if u.unit in unit_map.keys():
                unit_map[u.unit] = op(unit_map[u.unit], u.power)
            else:
                unit_map[u.unit] = -u.power if symbol == "/" else u.power

    elif isinstance(other, Composite):
        # Let composite's mult function handle this - other must be first here.
        # return self * other ** -1 if symbol == "/" else other * self
        if symbol == "/":
            raise NotImplemented(f'Division not implemented between types: {type(self)} / {type(other)}')
        return other * self

    elif isinstance(other, int) or isinstance(other, float):
        return Composite(1 / other, self) if symbol == "/" else Composite(other, self)

    else:
        raise TypeError("Must multiply by BaseUnit, DerivedUnit, or a number")

    if len([u for u in unit_map.values() if u != 0]) == 0:
        return DerivedUnit("𝟙", "", [], "𝟙")

    base_units = [(k_, v_) for k_, v_ in unit_map.items()]
    base_units2 = [Assoc(k_, v_) for k_, v_ in unit_map.items()]

    result = DerivedUnit(
        "",
        _base_description(base_units2),
        base_units,
        f"{self.quantity} {symbol} {other.quantity}"
    )

    # The constructor takes name as a string, so modify the field directly
    # to add the tokens

    if isinstance(self, BaseUnit):
        self_tokens = [(self._name, 1)]
    else:
        self_tokens = self._name_tokens

    if isinstance(other, BaseUnit):
        other_tokens = [(other._name, -1 if symbol == "/" else 1)]
    else:
        sign = -1 if symbol == "/" else 1
        other_tokens = [(name, sign * val) for name, val in other._name_tokens]

    # The unitary operator is used internally, but should not display in the result.
    result._name_tokens = [t for t in self_tokens + other_tokens if t[0] != '𝟙']

    return result


def _pow(unit: Union[BaseUnit, DerivedUnit, Composite], power: int) -> DerivedUnit:
    """Helper to avoid repeated code in BaseUnit and DerivedUnit."""
    result = DerivedUnit("𝟙", "", [], "𝟙")

    for _ in range(abs(power)):
        if power > 0:
            result = result * unit
        else:
            result = result / unit

    return result


def _power_text(power: int) -> str:
    chars = {
        "-": "⁻",
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
    }

    result = "".join(chars[char] for char in str(power))
    # Ommit first power
    new_result = ""  # Don't modify result in place
    for i, char in enumerate(result):
        if char == "¹":
            if i == 0 or result[i-1] != "⁻":
                continue
        new_result += char

    return new_result
