from a import b
from a.b import c
from d import (d_1, d_2, d_3)
from e import (
    e_1,
    e_2,
    e_3,
)

import f as f_alias


class A:
    pass

@dataclass
class B:
    pass

def a():
    pass
