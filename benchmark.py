import time
from enum import Enum

limit = 30_000

class Ops(Enum):
    ADD = 'add'
    SUB = 'sub'
    MUL = 'mul'
    DIV = 'div'

all_ops = [op for op in Ops]

# generate random data in all types boolean, integer, string, enum, float, list, dict, set & tuple
t1 = time.time()
rows = []
for i in range(limit):
    rows.append({
        "boolean": bool(i % 2),
        "integer": i,
        "string": str(i),
        "enum": Ops(all_ops[i % 3]),  # enum with auto values
        "float": float(i),
        "list": list(range(i % 10, 0, -1)),
        "dict": {"key_" + str(j): j for j in range(i % 10)},
        "set": set(range(i % 10, 0, -1)),
        "tuple": tuple(range(i % 10, 0, -1)),
    })
t2 = time.time()
print(f"Generation of {limit:,d} records, took time: {t2-t1} seconds")

def test_camel_cy():
    global rows
    from camelx_cy import Camel, CamelRegistry
    reg = CamelRegistry()

    @reg.dumper(Ops, u'ops', version=None)
    def _dump_ops(data):
        return u"{}".format(data.value)
    @reg.loader(u'ops', version=None)
    def _load_ops(data, version):
        return Ops(data)

    camel = Camel([reg])

    t1 = time.time()
    camel_str = camel.dump(rows)
    t2 = time.time()
    original_rows = camel.load(camel_str)
    t3 = time.time()
    print(f"Serialization/Deserialization of {limit:,d} records, took time: {t2-t1} seconds for serialization, {t3-t2} seconds for deserialization")

def test_camel():
    global rows
    from camelx.camelx import Camel, CamelRegistry
    reg = CamelRegistry()

    @reg.dumper(Ops, u'ops', version=None)
    def _dump_ops(data):
        return u"{}".format(data.value)
    @reg.loader(u'ops', version=None)
    def _load_ops(data, version):
        return Ops(data)

    camel = Camel([reg])

    t1 = time.time()
    camel_str = camel.dump(rows)
    t2 = time.time()
    original_rows = camel.load(camel_str)
    t3 = time.time()
    print(f"Serialization/Deserialization of {limit:,d} records, took time: {t2-t1} seconds for serialization, {t3-t2} seconds for deserialization")

t1 = time.time()
print("Test for camel_cy")
test_camel_cy()
print("Test for camel")
test_camel()
t2 = time.time()
print(f"Total time: {t2-t1} seconds")