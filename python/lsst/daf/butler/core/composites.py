#
# LSST Data Management System
#
# Copyright 2018  AURA/LSST.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
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
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <https://www.lsstcorp.org/LegalNotices/>.

"""Support for reading and writing composite objects."""

import collections


class DatasetComponent:

    """Component of a dataset and associated information.

    Parameters
    ----------
    name : `str`
        Name of the component.
    storageClass : `StorageClass`
        StorageClass to be used when reading or writing this component.
    component : `object`
        Component extracted from the composite object.

    """
    def __init__(self, name, storageClass, component):
        self.name = name
        self.storageClass = storageClass
        self.component = component


def _attrNames(componentName, getter=True):
    """Return list of suitable attribute names to attempt to use.

    Parameters
    ----------
    componentName : `str`
        Name of component/attribute to look for.
    getter : `bool`
        If true, return getters, else return setters.

    Returns
    -------
    attrs : `tuple(str)`
        Tuple of strings to attempt.
    """
    root = "get" if getter else "set"
    return (componentName, "{}_{}".format(root, componentName), "{}{}".format(root, componentName.capitalize))


def genericAssembler(storageClass, components, pytype=None):
    """Construct an object from components based on storageClass.

    This generic implementation assumes that instances of objects
    can be created either by passing all the components to a constructor
    or by calling setter methods with the name.

    Parameters
    ----------
    storageClass : `StorageClass`
        `StorageClass` describing the entity to be created from the
        components.
    components : `dict`
        Collection of components from which to assemble a new composite
        object. Keys correspond to composite names in the `StorageClass`.
    pytype : `class`, optional
        Override the type from the `storageClass` to use when assembling
        the final object.

    Returns
    -------
    composite : `object`
        New composite object assembled from components.

    Raises
    ------
    ValueError
        Some components could not be used to create the object.
    """
    if pytype is not None:
        cls = pytype
    else:
        cls = storageClass.pytype

    # Should we check that the storage class components match or are a superset
    # of the items described in the supplied components?

    # First try to create an instance directly using keyword args
    try:
        obj = cls(**components)
    except TypeError:
        obj = None

    # Now try to use setters if direct instantiation didn't work
    if not obj:
        obj = cls()

        failed = []
        for name, component in components.items():
            for attr in _attrNames(name, getter=False):
                if hasattr(obj, attr):
                    setattr(obj, attr, component)
                    break
            else:
                failed.append(name)

        if failed:
            raise ValueError("There are unhandled components ({})".format(failed))

    return obj


def validComponents(composite, storageClass):
    """Extract requested components from a composite.

    Parameters
    ----------
    composite : `object`
        Composite from which to extract components.
    storageClass : `StorageClass`
        `StorageClass` associated with this composite object.
        If None, it is assumed this is not to be treated as a composite.

    Returns
    -------
    comps : `dict`
        Non-None components extracted from the composite, indexed by the component
        name as derived from the `StorageClass`.
    """
    components = {}
    if storageClass is not None and storageClass.components:
        for c in storageClass.components:
            if isinstance(composite, collections.Mapping):
                comp = composite[c]
            else:
                comp = genericGetter(composite, c)
            if comp is not None:
                components[c] = comp
    return components


def hasComponent(composite, componentName):
    """Determine if it seems likely that the composite has the component.

    Parameters
    ----------
    composite : `object`
        Item to query for the component.
    componentName : `str`
        Name of component to retrieve.

    Returns
    -------
    getter : `str`
        Name of attribute to use with `getattr`. None if nothing suitable
        was found.

    """
    for attr in _attrNames(componentName, getter=True):
        if hasattr(composite, attr):
            return attr
    return None


def genericGetter(composite, componentName):
    """Attempt to retrieve component from composite object by heuristic.

    Will attempt a direct attribute retrieval, or else getter methods of the
    form "get_componentName" and "getComponentName".

    Parameters
    ----------
    composite : `object`
        Item to query for the component.
    componentName : `str`
        Name of component to retrieve.

    Returns
    -------
    component : `object`
        Component extracted from composite. None if nothing worked.
    """
    component = None
    for attr in _attrNames(componentName, getter=True):
        if hasattr(composite, attr):
            component = getattr(composite, attr)
            break
    return component


def genericDisassembler(composite, storageClass):
    """Generic implementation of a disassembler.

    This implementation attempts to extract components from the parent
    by looking for attributes of the same name or getter methods derived
    from the component name.

    Parameters
    ----------
    composite : `object`
        Parent composite object consisting of components to be extracted.
    storageClass : `StorageClass`
        `StorageClass` associated with the parent, with defined components.

    Returns
    -------
    components : `dict`
        `dict` with keys matching the components defined in `storageClass`
        and values being `DatasetComponent` instances describing the component.

    Raises
    ------
    ValueError
        A requested component can not be found in the parent using generic
        lookups.
    TypeError
        The parent object does not match the supplied `StorageClass`.
    """
    if not storageClass.validateInstance(composite):
        raise TypeError("Unexpected type mismatch between parent and StorageClass"
                        " ({} != {})".format(type(composite), storageClass.pytype))

    requested = set(storageClass.components.keys())
    components = {}
    for c in list(requested):
        # Try three different ways to get a value associated with the
        # component name.
        component = genericGetter(composite, c)

        # If we found a match store it in the results dict and remove
        # it from the list of components we are still looking for.
        if component is not None:
            components[c] = DatasetComponent(c, storageClass.components[c], component)
            requested.remove(c)

    if requested:
        raise ValueError("There are unhandled components ({})".format(requested))

    return components