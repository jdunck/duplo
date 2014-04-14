import importlib, operator, sys
from collections import defaultdict
from contextlib import contextmanager

class EmptyContext(ValueError):
    pass

class Context(object):
    """
    A stack of dictionaries, which provides an abstraction of shadowing
    for applying and unapplying.
    """
    def __init__(self, default):
        self._default = default
        self.stack = [defaultdict(default)]

    def __getitem__(self, name):
        for frame in reversed(self.stack):
            if name in frame:
                return frame[name]
        else:
            return self._default()

    def __setitem__(self, name, value):
        self.stack[-1][name] = value

    @property
    def depth(self):
        return len(self.stack)

    def push(self):
        self.stack.append({})

    def pop(self):
        if len(self.stack) == 1:
            raise EmptyContext("Context stack empty")

        return self.stack.pop()

    def keys(self):
        all_keys = set()
        for frame in self.stack:
            all_keys.update(frame.keys())
        return list(all_keys)

    def items(self):
        pairs = []
        for key in self.keys():
            pairs.append((key, self[key]))
        return pairs

    def update(self, values):
        self.stack[-1].update(values)

class DoublerBase(object):
    """
    An "interface" for managing doubles.
    """
    def __init__(self, name):
        self.name = name

    def __unicode__(self):
        return u"<Double: {0}>".format(self.name)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def apply(self):
        raise NotImplementedError

    def unapply(self):
        raise NotImplementedError

class MissingPatchTarget(ValueError):
    pass

class UnexpectedUnapply(TypeError):
    pass

class PatchingDoubler(DoublerBase):
    """
    A doubler which is applied through monkey patches.

    Targets is a list of importable names to be patched, e.g.
    ['some.module:name']
    """
    def __init__(self, name, variant, targets):
        super(PatchingDoubler, self).__init__(name)
        if isinstance(targets, basestring):
            targets = [targets]

        if len(targets) < 1:
            raise MissingPatchTarget("There must be at least 1 target to patch.")

        self.targets = targets

        self.normals = [] # set when first applied, same order as targets
        self.variant = variant

    def patching_attribute(self, name_maybe):
        return name_maybe is not None

    def _parse_target(self, target):
        try:
            module, name_maybe = target.split(':')
        except ValueError:
            module, name_maybe = target, None
        return (module, name_maybe)

    def _format_target(self, module_name, name_maybe):
        if name_maybe is None:
            return module_name
        else:
            return "{0}:{1}".format(module_name, name_maybe)

    def _resolve_module(self, module_name, name_maybe):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            # If patching an attribute of a module, fail if we can't find
            #  the needed module.
            # But if patching a module, it's OK if it didn't
            #  originally exist.
            if name_maybe is None:
                module = None
            else:
                raise MissingPatchTarget("Unable to find {0}".format(module_name))
        else:
            return module

    def _resolve_variant(self, variant):
        if isinstance(variant, basestring):
            try:
                return self._resolve_target(variant)[0]()
            except MissingPatchTarget: # assume it's a literal value
                return variant
        return variant


    def _resolve_target(self, target):
        """
        Returns a getter and setter for the given target.
        """
        module_name, name_maybe = self._parse_target(target)
        module = self._resolve_module(module_name, name_maybe)

        if self.patching_attribute(name_maybe):
            def make_attr_getter():
                def getter():
                    try:
                        return getattr(module, name_maybe)
                    except AttributeError:
                        formatted_name = self._format_target(module_name, name_maybe)
                        raise MissingPatchTarget("Unable to find {0}".format(formatted_name))
                return getter

            return make_attr_getter(), lambda value: setattr(module, name_maybe, value)
        else:
            def make_module_setter():
                def setter(value):
                    if value is None:
                        del sys.modules[module_name]
                    else:
                        sys.modules[module_name] = value
                return setter

            return lambda: module, make_module_setter()

    def apply(self):
        for target in self.targets:
            getter, setter = self._resolve_target(target)

            self.normals.append(getter())

            variant = self._resolve_variant(self.variant)
            setter(variant)

    def unapply(self):
        if not len(self.normals):
            raise UnexpectedUnapply

        for target in self.targets:
            getter, setter = self._resolve_target(target)
            original = self.normals.pop()
            setter(original)

class MissingDouble(ValueError):
    """
    No double with the given name is registered.
    """
    pass

class UnappliedDouble(ValueError):
    """
    The requested double has not been applied.
    """

    pass

class DuplicateRegistration(ValueError):
    """
    A double with the given name was already registered.
    """
    pass

class DoubleManager(object):
    """
    Applies each double once (and only once).

    Register doubles, then apply them or unapply them as needed.

    Calling apply on a previously-applied double does nothing, and
    similarly with unapply on previously-unapplied.

    .revert returns the doubles to the state they were in before
    the previous call to apply or unapply.
    """
    def __init__(self):
        self._applieds = Context(bool)
        self.registry = {}

    def register_double(self, double):
        if not isinstance(double, DoublerBase):
            raise MissingDouble("Unable to register {0}.".format(double))
        if double.name in self.registry:
            raise DuplicateRegistration("{0} was registered twice. Duplicate import?".format(double.name))
        self.registry[double.name] = double

    def _resolve_included(self, include, exclude):
        """
        Expands include and exclude into a concrete list of doubles
        to work upon.
        """
        include, exclude = self._conform_double_names(include), self._conform_double_names(exclude)

        if include is None and exclude is None:
            included = set(self.registry.keys())
        elif include is None:
            included = set(self.registry.keys()) - set(exclude)
        elif exclude is None:
            included = set(include)
        else:
            raise ValueError("Unable to both include and exclude.")

        # check that there weren't any bad names
        missing = set()
        if include is not None:
            missing = set(include) - included
        elif exclude is not None:
            missing = included & set(exclude)

        return included

    def _resolve_doubles(self, included):
        """
        Maps the given double names to double instances.
        """
        try:
            return [self.registry[name] for name in included]
        except KeyError:
            raise MissingDouble

    def _conform_double_names(self, doubles):
        if doubles is None:
            return

        if isinstance(doubles, basestring):
            doubles = [doubles]

        if not all(d in self.registry for d in doubles):
            raise MissingDouble
        return doubles

    @property
    def applied(self):
        """
        Returns the names of all currently-applied doubles.
        """
        return [name for name, applied in self._applieds.items() if applied]

    def is_applied(self, name):
        return name in self.applied

    def apply_doubles(self, include=None, exclude=None):
        return self._manage_doubles(operator.not_, 'apply', include, exclude)

    def unapply_doubles(self, include=None, exclude=None):
        return self._manage_doubles(operator.truth, 'unapply', include, exclude)

    def _manage_doubles(self, operator, action_attr, include=None, exclude=None):
        included = self._resolve_included(include, exclude)

        doubles = self._resolve_doubles(included)

        self._applieds.push()

        applied = []
        for double in doubles:
            status = self._applieds[double.name]
            # only do if not already done:
            if operator(status):
                # actually apply or unapply
                getattr(double, action_attr)()
                self._applieds[double.name] = not status
                applied.append(double.name)
        return applied

    def revert(self):
        """
        Return the double application to the state it was in prior to
        the most recent call to apply_ or unapply_doubles.
        """
        try:
            previous_doubles = self._applieds.pop()
        except EmptyContext:
            raise UnappliedDouble

        for double_name, applied in previous_doubles.items():
            if applied:
                self.registry[double_name].unapply()
            else:
                self.registry[double_name].apply()

def _take_action(manager, attr, doubles):
    doubles = manager._conform_double_names(doubles)
    getattr(manager, attr)(doubles)
    yield
    manager.revert()

@contextmanager
def unapplied(manager, doubles):
    """
    Unapply a double (if needed) within the block.
    """
    return _take_action(manager, 'unapply_doubles', doubles)

@contextmanager
def applied(manager, doubles):
    """
    Apply a double (if needed) within the block.
    """
    return _take_action(manager, 'apply_doubles', doubles)