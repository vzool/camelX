# encoding: utf8
# TODO, this specifically:
# - allow prefixing (in the Camel obj?) otherwise assume local, don't require the leading !
# - figure out namespacing and urls and whatever the christ
# - document exactly which ones we support (i.e., yaml supports)
# - support the attrs module, if installed, somehow
# - consider using (optionally?) ruamel.yaml, which roundtrips comments, merges, anchors, ...
# TODO, general:
# - DWIM -- block style except for very short sequences (if at all?), quotey style for long text...

# TODO BEFORE PUBLISHING:
# - /must/ strip the leading ! from tag names and allow giving a prefix (difficulty: have to do %TAG directive manually)
# - better versioning story, interop with no version somehow, what is the use case for versionless?  assuming it will never change?  imo should require version
# - should write some docs, both on camel and on yaml

# TODO from alex gaynor's talk, starting around 24m in:
# - class is deleted (if it's useless, just return a dummy value)
# - attribute changes

# TODO little niceties
# - complain if there are overlapping definitions within the same registry?
# - opt-in thing for subclasses, i think pyyaml has some facilities for this even (multi)
# - dumper and loader could be easily made to work on methods...  i think...  in py3


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import base64
import collections
import functools
from io import StringIO
import types

import yaml

try:
    from yaml import CSafeDumper as SafeDumper
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeDumper
    from yaml import SafeLoader


YAML_TAG_PREFIX = 'tag:yaml.org,2002:'

_str = type('')
_bytes = type(b'')
_long = type(18446744073709551617)  # 2**64 + 1


class CamelDumper(SafeDumper):
    """Subclass of yaml's `SafeDumper` that scopes representers to the
    instance, rather than to the particular class, because damn.
    """
    def __init__(self, *args, **kwargs):
        # TODO this isn't quite good enough; pyyaml still escapes anything
        # outside the BMP
        kwargs.setdefault('allow_unicode', True)
        super(CamelDumper, self).__init__(*args, **kwargs)
        self.yaml_representers = SafeDumper.yaml_representers.copy()
        self.yaml_multi_representers = SafeDumper.yaml_multi_representers.copy()

        # Always dump bytes as binary, even on Python 2
        self.add_representer(bytes, CamelDumper.represent_binary)

    def represent_binary(self, data):
        # This is copy-pasted, because it only exists in pyyaml in python 3 (?!)
        if hasattr(base64, 'encodebytes'):
            data = base64.encodebytes(data).decode('ascii')
        else:
            data = base64.encodestring(data).decode('ascii')
        return self.represent_scalar(
            YAML_TAG_PREFIX + 'binary', data, style='|')

    def add_representer(self, data_type, representer):
        self.yaml_representers[data_type] = representer

    def add_multi_representer(self, data_type, representer):
        self.yaml_multi_representers[data_type] = representer


class CamelLoader(SafeLoader):
    """Subclass of yaml's `SafeLoader` that scopes constructors to the
    instance, rather than to the particular class, because damn.
    """
    def __init__(self, *args, **kwargs):
        super(CamelLoader, self).__init__(*args, **kwargs)
        self.yaml_constructors = SafeLoader.yaml_constructors.copy()
        self.yaml_multi_constructors = SafeLoader.yaml_multi_constructors.copy()
        self.yaml_implicit_resolvers = SafeLoader.yaml_implicit_resolvers.copy()

    def add_constructor(self, data_type, constructor):
        self.yaml_constructors[data_type] = constructor

    def add_multi_constructor(self, data_type, constructor):
        self.yaml_multi_constructors[data_type] = constructor

    def add_implicit_resolver(self, tag, regexp, first):
        if first is None:
            first = [None]
        for ch in first:
            self.yaml_implicit_resolvers.setdefault(ch, []).append((tag, regexp))

    def add_path_resolver(self, *args, **kwargs):
        # This API is non-trivial and claims to be experimental and unstable
        raise NotImplementedError


class Camel(object):
    def __init__(self, registries=()):
        self.registries = (STANDARD_TYPES,) + tuple(registries)
        self.version_locks = {}  # class => version

    def lock_version(self, cls, version):
        self.version_locks[cls] = version

    def make_dumper(self, stream):
        dumper = CamelDumper(stream, default_flow_style=False)
        for registry in self.registries:
            registry.inject_dumpers(dumper, version_locks=self.version_locks)
        return dumper

    def dump(self, data):
        stream = StringIO()
        dumper = self.make_dumper(stream)
        dumper.open()
        dumper.represent(data)
        dumper.close()
        return stream.getvalue()

    def make_loader(self, stream):
        loader = CamelLoader(stream)
        for registry in self.registries:
            registry.inject_loaders(loader)
        return loader

    def load(self, data):
        stream = StringIO(data)
        loader = self.make_loader(stream)
        obj = loader.get_data()
        if loader.check_node():
            raise RuntimeError("Multiple documents found in stream; use load_all")
        return obj

    def load_first(self, data):
        stream = StringIO(data)
        loader = self.make_loader(stream)
        return loader.get_data()

    def load_all(self, data):
        stream = StringIO(data)
        loader = self.make_loader(stream)
        while loader.check_node():
            yield loader.get_data()


class DuplicateVersion(ValueError):
    pass


class NoSuchVersion(KeyError):
    pass


class CamelRegistry(object):
    frozen = False

    def __init__(self):
        # type => {version => function)
        self.dumpers = collections.defaultdict(dict)
        # base tag => {version => function}
        self.loaders = collections.defaultdict(dict)

    def freeze(self):
        self.frozen = True

    # Dumping

    def _check_tag(self, tag):
        # Good a place as any, I suppose
        if self.frozen:
            raise RuntimeError("Can't add to a frozen registry")

        if ';' in tag:
            raise ValueError(
                "Tags may not contain semicolons: {0!r}".format(tag))

    def dumper(self, cls, tag, version=None):
        self._check_tag(tag)

        if version in self.dumpers[cls]:
            raise DuplicateVersion

        if version is None:
            full_tag = tag
        elif isinstance(version, (int, _long)) and version > 0:
            full_tag = "{0};{1}".format(tag, version)
        else:
            raise TypeError(
                "Expected None or a positive integer version; "
                "got {0!r} instead".format(version))

        def decorator(f):
            self.dumpers[cls][version] = functools.partial(
                self.run_representer, f, full_tag)
            return f

        return decorator

    def run_representer(self, representer, tag, dumper, data):
        canon_value = representer(data)
        # Note that we /do not/ support subclasses of the built-in types here,
        # to avoid complications from returning types that have their own
        # custom representers
        canon_type = type(canon_value)
        # TODO this gives no control over flow_style, style, and implicit.  do
        # we intend to figure it out ourselves?
        if canon_type in (dict, collections.OrderedDict):
            return dumper.represent_mapping(tag, canon_value, flow_style=False)
        elif canon_type in (tuple, list):
            return dumper.represent_sequence(tag, canon_value, flow_style=False)
        elif canon_type in (int, _long, float, bool, _str, type(None)):
            return dumper.represent_scalar(tag, canon_value)
        else:
            raise TypeError(
                "Representers must return native YAML types, but the representer "
                "for {!r} returned {!r}, which is of type {!r}"
                .format(data, canon_value, canon_type))

    def inject_dumpers(self, dumper, version_locks=None):
        if not version_locks:
            version_locks = {}

        for cls, versions in self.dumpers.items():
            version = version_locks.get(cls, max)
            if versions and version is max:
                if None in versions:
                    representer = versions[None]
                else:
                    representer = versions[max(versions)]
            elif version in versions:
                representer = versions[version]
            else:
                raise KeyError(
                    "Don't know how to dump version {0!r} of type {1!r}"
                    .format(version, cls))
            dumper.add_representer(cls, representer)

    # Loading
    # TODO implement "upgrader", which upgrades from one version to another

    def loader(self, tag, version=None):
        self._check_tag(tag)

        if version in self.loaders[tag]:
            raise DuplicateVersion

        def decorator(f):
            self.loaders[tag][version] = functools.partial(self.run_constructor, f)
            return f

        return decorator

    def run_constructor(self, constructor, loader, node):
        if isinstance(node, yaml.ScalarNode):
            data = loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            data = loader.construct_sequence(node, deep=True)
        elif isinstance(node, yaml.MappingNode):
            data = loader.construct_mapping(node, deep=True)
        else:
            raise TypeError("Not a primitive node: {!r}".format(node))
        return constructor(data)

    def inject_loaders(self, loader):
        for tag, versions in self.loaders.items():
            # "all" loader overrides everything
            if all in versions:
                loader.add_constructor(tag, versions[all])
                # Including unrecognized versions
                # TODO need a way to pass the version in, oops
                #loader.add_multi_constructor(tag + ";", lambda loader
                continue

            # Otherwise, add each constructor individually
            for version, constructor in versions.items():
                if version is None:
                    loader.add_constructor(tag, constructor)
                elif version is any:
                    # TODO this should act as a fallback using multi
                    pass
                else:
                    full_tag = "{0};{1}".format(tag, version)
                    loader.add_constructor(full_tag, constructor)


# TODO "raw" loaders and dumpers that get access to loader/dumper and deal with
# raw nodes?
# TODO multi_constructor, multi_representer, implicit_resolver


# YAML's "language-independent types" — not builtins, but supported with
# standard !! tags.  Most of them are built into pyyaml, but OrderedDict is
# curiously overlooked.  Loaded first by default into every Camel object.
# Ref: http://yaml.org/type/
# TODO pyyaml supports tags like !!python/list; do we care?
STANDARD_TYPES = CamelRegistry()


@STANDARD_TYPES.dumper(frozenset, YAML_TAG_PREFIX + 'set')
def _dump_frozenset(data):
    return dict.fromkeys(data)


@STANDARD_TYPES.dumper(collections.OrderedDict, YAML_TAG_PREFIX + 'omap')
def _dump_ordered_dict(data):
    pairs = []
    for key, value in data.items():
        pairs.append({key: value})
    return pairs


@STANDARD_TYPES.loader(YAML_TAG_PREFIX + 'omap')
def _load_ordered_dict(data):
    # TODO assert only single kv per thing
    return collections.OrderedDict(
        next(iter(datum.items())) for datum in data
    )


# Extra Python types that don't have native YAML equivalents, but that PyYAML
# supports with !!python/foo tags.  Dumping them isn't supported by default,
# but loading them is, since there's no good reason for it not to be.
# A couple of these dumpers override builtin type support.  For example, tuples
# are dumped as lists by default, but this registry will dump them as
# !!python/tuple.
PYTHON_TYPES = CamelRegistry()


@PYTHON_TYPES.dumper(tuple, YAML_TAG_PREFIX + 'python/tuple')
def _dump_tuple(data):
    return list(data)


@STANDARD_TYPES.loader(YAML_TAG_PREFIX + 'python/tuple')
def _load_tuple(data):
    return tuple(data)


@PYTHON_TYPES.dumper(complex, YAML_TAG_PREFIX + 'python/complex')
def _dump_complex(data):
    ret = repr(data)
    if str is bytes:
        ret = ret.decode('ascii')
    # Complex numbers become (1+2j), but the parens are superfluous
    if ret[0] == '(' and ret[-1] == ')':
        return ret[1:-1]
    else:
        return ret


@STANDARD_TYPES.loader(YAML_TAG_PREFIX + 'python/complex')
def _load_complex(data):
    return complex(data)


@PYTHON_TYPES.dumper(frozenset, YAML_TAG_PREFIX + 'python/frozenset')
def _dump_frozenset(data):
    try:
        return list(sorted(data))
    except TypeError:
        return list(data)


@STANDARD_TYPES.loader(YAML_TAG_PREFIX + 'python/frozenset')
def _load_frozenset(data):
    return frozenset(data)


if hasattr(types, 'SimpleNamespace'):
    @PYTHON_TYPES.dumper(types.SimpleNamespace, YAML_TAG_PREFIX + 'python/namespace')
    def _dump_simple_namespace(data):
        return data.__dict__


    @STANDARD_TYPES.loader(YAML_TAG_PREFIX + 'python/namespace')
    def _load_simple_namespace(data):
        return types.SimpleNamespace(**data)


STANDARD_TYPES.freeze()
PYTHON_TYPES.freeze()
