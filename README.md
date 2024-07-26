**This fork from "[eevee/camel](https://github.com/eevee/camel)" aims to maintain and potentially enhance the library, the original project has been inactive for years.**

CamelX
=====

CamelX is a library that lets you describe how to serialize your objects to
YAML — and refuses to serialize them if you don't.

If you are interested in contributing, please submit pull requests.

Quick example:

```python

    from camelx import Camel, CamelRegistry

    class DieRoll(tuple):
        def __new__(cls, a, b):
            return tuple.__new__(cls, [a, b])

        def __repr__(self):
            return "DieRoll(%s,%s)" % self

    reg = CamelRegistry()

    @reg.dumper(DieRoll, u'roll', version=None)
    def _dump_dice(data):
        return u"{}d{}".format(*data)

    @reg.loader(u'roll', version=None)
    def _load_dice(data, version):
        a, _, b = data.partition(u'd')
        return DieRoll(int(a), int(b))

    value = DieRoll(3, 6)
    camel = Camel([reg])
    print(camel.dump(value))

    # !roll 3d6
    # ...
```

Docs: http://camel.readthedocs.org/en/latest/

GitHub: https://github.com/eevee/camel

