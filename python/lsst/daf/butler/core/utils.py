# This file is part of daf_butler.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import namedtuple


def iterable(a):
    """Make input iterable.

    There are three cases, when the input is:

    - iterable, but not a `str` -> iterate over elements
      (e.g. ``[i for i in a]``)
    - a `str` -> return single element iterable (e.g. ``[a]``)
    - not iterable -> return single elment iterable (e.g. ``[a]``).

    Parameters
    ----------
    a : iterable or `str` or not iterable
        Argument to be converted to an iterable.

    Returns
    -------
    i : `generator`
        Iterable version of the input value.
    """
    if isinstance(a, str):
        yield a
        return
    try:
        yield from a
    except Exception:
        yield a


def allSlots(self):
    """
    Return combined ``__slots__`` for all classes in objects mro.

    Parameters
    ----------
    self : `object`
        Instance to be inspected.

    Returns
    -------
    slots : `itertools.chain`
        All the slots as an iterable.
    """
    from itertools import chain
    return chain.from_iterable(getattr(cls, '__slots__', []) for cls in self.__class__.__mro__)


def slotValuesAreEqual(self, other):
    """
    Test for equality by the contents of all slots, including those of its
    parents.

    Parameters
    ----------
    self : `object`
        Reference instance.
    other : `object`
        Comparison instance.

    Returns
    -------
    equal : `bool`
        Returns True if all the slots are equal in both arguments.
    """
    return all((getattr(self, slot) == getattr(other, slot) for slot in allSlots(self)))


def slotValuesToHash(self):
    """
    Generate a hash from slot values.

    Parameters
    ----------
    self : `object`
        Instance to be hashed.

    Returns
    -------
    h : `int`
        Hashed value generated from the slot values.
    """
    return hash(tuple(getattr(self, slot) for slot in allSlots(self)))


def getFullTypeName(cls):
    """Return full type name of the supplied entity.

    Parameters
    ----------
    cls : `type` or `object`
        Entity from which to obtain the full name. Can be an instance
        or a `type`.

    Returns
    -------
    name : `str`
        Full name of type.
    """
    # If we have an instance we need to convert to a type
    if not hasattr(cls, "__qualname__"):
        cls = type(cls)
    return cls.__module__ + "." + cls.__qualname__


def doImport(pythonType):
    """Import a python object given an importable string and return the
    type object

    Parameters
    ----------
    pythonType : `str`
        String containing dot-separated path of a Python class, module,
        or member function.

    Returns
    -------
    type : `type`
        Type object. Either a module or class or a function.

    Raises
    ------
    TypeError
        pythonType is not a `str`.
    ValueError
        pythonType can not be imported.
    AttributeError
        pythonType can be partially imported.
    """
    if not isinstance(pythonType, str):
        raise TypeError("Unhandled type of pythonType, val:%s" % pythonType)
    try:
        # import this pythonType dynamically
        pythonTypeTokenList = pythonType.split('.')
        importClassString = pythonTypeTokenList.pop()
        importClassString = importClassString.strip()
        importPackage = ".".join(pythonTypeTokenList)
        importType = __import__(importPackage, globals(), locals(), [importClassString], 0)
        pythonType = getattr(importType, importClassString)
        return pythonType
    except ImportError:
        pass
    # maybe python type is a member function, in the form: path.to.object.Class.funcname
    pythonTypeTokenList = pythonType.split('.')
    importClassString = '.'.join(pythonTypeTokenList[0:-1])
    importedClass = doImport(importClassString)
    pythonType = getattr(importedClass, pythonTypeTokenList[-1])
    return pythonType


def getInstanceOf(typeOrName):
    """Given the type name or a type, instantiate an object of that type.

    If a type name is given, an attempt will be made to import the type.

    Parameters
    ----------
    typeOrName : `str` or Python class
        A string describing the Python class to load or a Python type.
    """
    if isinstance(typeOrName, str):
        cls = doImport(typeOrName)
    else:
        cls = typeOrName
    return cls()


class Singleton(type):
    """Metaclass to convert a class to a Singleton.

    If this metaclass is used the constructor for the singleton class must
    take no arguments. This is because a singleton class will only accept
    the arguments the first time an instance is instantiated.
    Therefore since you do not know if the constructor has been called yet it
    is safer to always call it with no arguments and then call a method to
    adjust state of the singleton.
    """

    _instances = {}

    def __call__(cls):  # noqa N805
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__()
        return cls._instances[cls]


# Helper Node in a TopologicalSet
# Unfortunately can't be a class member because that breaks pickling
TopologicalSetNode = namedtuple('TopologicalSetNode', ['element', 'sourceElements'])


class TopologicalSet:
    """A collection that behaves like a builtin `set`, but where
    elements can be interconnected (like a graph).

    Iteration over this collection visits its elements in topologically
    sorted order.

    Parameters
    ----------
    elements : `iterable`
        Any iterable with elements to insert.
    """
    def __init__(self, elements):
        self._nodes = {e: TopologicalSetNode(e, set()) for e in elements}
        self._ordering = None

    def __contains__(self, element):
        return element in self._nodes

    def __len__(self):
        return len(self._nodes)

    def __eq__(self, other):
        return self._nodes == other._nodes

    def connect(self, sourceElement, targetElement):
        """Connect two elements in the set.

        The connection is directed from `sourceElement` to `targetElement` and
        is distinct from its inverse.
        Both elements must already be present in the set.

        sourceElement : `object`
            The source element.
        targetElement : `object`
            The target element.

        Raises
        ------
        KeyError
            When either element is not already in the set.
        ValueError
            If a self connections between elements would be created.
        """
        if sourceElement == targetElement:
            raise ValueError('Cannot connect {} to itself'.format(sourceElement))
        for element in (sourceElement, targetElement):
            if element not in self._nodes:
                raise KeyError('{} not in set'.format(element))
        targetNode = self._nodes[targetElement]
        targetNode.sourceElements.add(sourceElement)
        # Adding a connection invalidates previous ordering
        self._ordering = None

    def __iter__(self):
        """Iterate over elements in topologically sorted order.

        Raises
        ------
        ValueError
            If a cycle is found and hence no topological order exists.
        """
        if self._ordering is None:
            self.ordering = self._topologicalOrdering()
        yield from self.ordering

    def _topologicalOrdering(self):
        """Generate a topological ordering by doing a basic
        depth-first-search.
        """
        seen = set()
        finished = set()
        order = []

        def visit(node):
            if node.element in finished:
                return
            if node.element in seen:
                raise ValueError("Cycle detected")
            seen.add(node.element)
            for sourceElement in node.sourceElements:
                visit(self._nodes[sourceElement])
            finished.add(node.element)
            seen.remove(node.element)
            order.append(node.element)

        for node in self._nodes.values():
            visit(node)
        return order
