"""
Class and functions for scene node
"""
from enum import Enum, unique
import numpy as np
from ..math.matrix import Matrix44
from ..math.transform import rotation_btw_vectors
from ..geometry.colour import Colour
from ..geometry.primitive import create_sphere, create_plane, create_cuboid
from ..geometry.mesh import BoundingBox
from ..util.misc import Attributes
from ...config import settings


class Node:
    """Creates Node object.

    :param mesh: mesh to add to node
    :type mesh: Union[Mesh, None]
    """
    @unique
    class RenderMode(Enum):
        Solid = 'Solid'
        Wireframe = 'Wireframe'
        Transparent = 'Transparent'
        Outline = 'Outline'

    @unique
    class RenderPrimitive(Enum):
        Lines = 'Lines'
        Triangles = 'Triangles'

    def __init__(self, mesh=None):
        if mesh is None:
            self._vertices = np.array([])
            self.indices = np.array([])
            self.normals = np.array([])
            self._bounding_box = None
            self._colour = Colour.black()
        else:
            self._vertices = mesh.vertices
            self.indices = mesh.indices
            self.normals = mesh.normals
            self._bounding_box = mesh.bounding_box
            self._colour = mesh.colour

        self._render_mode = Node.RenderMode.Solid
        self.render_primitive = Node.RenderPrimitive.Triangles
        self.transform = Matrix44.identity()
        self.parent = None
        self._visible = True
        self.selected = False
        self.children = []

    def copy(self, transform=None):
        """Creates shallow copy of node with unique transformation matrix

        :param transform: transformation matrix
        :type transform: Union[Matrix44, None]
        :return: shallow copy of node
        :rtype: Node
        """
        node = Node()
        node._vertices = self._vertices
        node.indices = self.indices
        node.normals = self.normals
        node.bounding_box = self.bounding_box
        node._colour = self._colour
        node._render_mode = self._render_mode
        node.render_primitive = self.render_primitive
        node.transform = self.transform if transform is None else transform
        node.parent = self.parent
        node._visible = self._visible
        node.selected = self.selected
        node.children = self.children

        return node

    @property
    def vertices(self):
        return self._vertices

    @vertices.setter
    def vertices(self, value):
        """Updates the bounding box of the node when vertices are changed

        :param value: N x 3 array of vertices
        :type value: numpy.ndarray
        """
        self._vertices = value
        max_pos, min_pos = BoundingBox.fromPoints(self._vertices).bounds
        for node in self.children:
            max_pos = np.maximum(node.bounding_box.max, max_pos)
            min_pos = np.minimum(node.bounding_box.min, min_pos)
        self.bounding_box = BoundingBox(max_pos, min_pos)

    @property
    def colour(self):
        if self._colour is None and self.parent:
            return self.parent.colour

        return self._colour

    @colour.setter
    def colour(self, value):
        self._colour = value

    @property
    def visible(self):
        if self._visible is None and self.parent:
            return self.parent.visible

        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value

    @property
    def render_mode(self):
        if self._render_mode is None and self.parent:
            return self.parent.render_mode

        return self._render_mode

    @render_mode.setter
    def render_mode(self, value):
        self._render_mode = value

    def isEmpty(self):
        """Checks if Node is empty

        :return: indicates node is empty
        :rtype: bool
        """
        if not self.children and len(self.vertices) == 0:
            return True
        return False

    def addChild(self, child_node):
        """Adds child to the node and recomputes the bounding box to include child

        :param child_node: child node to add
        :type child_node: Node
        """
        if child_node.isEmpty():
            return

        child_node.parent = self
        self.children.append(child_node)

        max_pos, min_pos = child_node.bounding_box.bounds
        if self.bounding_box is not None:
            max_pos = np.maximum(self.bounding_box.max, max_pos)
            min_pos = np.minimum(self.bounding_box.min, min_pos)
        self.bounding_box = BoundingBox(max_pos, min_pos)

    def translate(self, offset):
        """Translates node

        :param offset: 3 x 1 array of offsets for X, Y and Z axis
        :type offset: Union[numpy.ndarray, sscanss.core.scene.Vector3]
        """
        if self.isEmpty():
            return

        self.transform @= Matrix44.fromTranslation(offset)

    def flatten(self):
        """Recursively flattens the tree formed by nested nodes

        :return: flattened node
        :rtype: Node
        """
        new_node = Node()
        new_node.bounding_box = self.bounding_box
        for node in self.children:
            if node.children:
                new_node.children.extend(node.flatten().children)
            elif not node.isEmpty():
                node.parent = None
                new_node.children.append(node)

        if len(self.vertices) != 0:
            parent = self.copy()
            parent.vertices = self.vertices
            new_node.children.append(parent)

        return new_node

    @property
    def bounding_box(self):
        return None if self._bounding_box is None else self._bounding_box.transform(self.transform)

    @bounding_box.setter
    def bounding_box(self, value):
        self._bounding_box = value


def create_sample_node(samples, render_mode=Node.RenderMode.Solid):
    """Creates node for samples

    :param samples: sample mesh
    :type samples: Dict[str, Mesh]
    :param render_mode: render mode
    :type render_mode: Node.RenderMode
    :return: node containing sample
    :rtype: Node
    """
    sample_node = Node()
    sample_node.colour = Colour(*settings.value(settings.Key.Sample_Colour))
    sample_node.render_mode = render_mode

    for sample_mesh in samples.values():
        child = Node(sample_mesh)
        child.colour = None
        child.render_mode = None

        sample_node.addChild(child)

    return sample_node


def create_fiducial_node(fiducials, visible=True):
    """Creates node for fiducial points

    :param fiducials: fiducial points
    :type fiducials: numpy.recarray
    :param visible: indicates node is visible
    :type visible: bool
    :return: node containing fiducial points
    :rtype: Node
    """
    fiducial_node = Node()
    fiducial_node.visible = visible
    fiducial_node.render_mode = Node.RenderMode.Solid
    enabled_colour = Colour(*settings.value(settings.Key.Fiducial_Colour))
    disabled_colour = Colour(*settings.value(settings.Key.Fiducial_Disabled_Colour))
    size = settings.value(settings.Key.Fiducial_Size)
    for point, enabled in fiducials:
        fiducial_mesh = create_sphere(size)
        fiducial_mesh.translate(point)

        child = Node(fiducial_mesh)
        child.colour = enabled_colour if enabled else disabled_colour
        child.render_mode = None
        child.visible = None

        fiducial_node.addChild(child)

    return fiducial_node


def create_measurement_point_node(points, visible=True):
    """Creates node for measurement points

    :param points: measurement points
    :type points: numpy.recarray
    :param visible: indicates node is visible
    :type visible: bool
    :return: node containing measurement points
    :rtype: Node
    """
    measurement_point_node = Node()
    measurement_point_node.visible = visible
    measurement_point_node.render_mode = Node.RenderMode.Solid
    enabled_colour = Colour(*settings.value(settings.Key.Measurement_Colour))
    disabled_colour = Colour(*settings.value(settings.Key.Measurement_Disabled_Colour))
    size = settings.value(settings.Key.Measurement_Size)
    for point, enabled in points:
        x, y, z = point

        child = Node()
        child.vertices = np.array([[x - size, y, z],
                                   [x + size, y, z],
                                   [x, y - size, z],
                                   [x, y + size, z],
                                   [x, y, z - size],
                                   [x, y, z + size]])

        child.indices = np.array([0, 1, 2, 3, 4, 5])
        child.colour = enabled_colour if enabled else disabled_colour
        child.render_mode = None
        child.visible = None
        child.render_primitive = Node.RenderPrimitive.Lines

        measurement_point_node.addChild(child)

    return measurement_point_node


def create_measurement_vector_node(points, vectors, alignment, visible=True):
    """Creates node for measurement vectors

    :param points: measurement points
    :type points: numpy.recarray
    :param vectors: measurement vectors
    :type vectors: numpy.ndarray
    :param alignment: vector alignment
    :type alignment: int
    :param visible: indicates node is visible
    :type visible: bool
    :return: node containing measurement vectors
    :rtype: Node
    """
    measurement_vector_node = Node()
    measurement_vector_node.visible = visible
    measurement_vector_node.render_mode = Node.RenderMode.Solid
    if vectors.shape[0] == 0:
        return measurement_vector_node

    alignment = 0 if alignment >= vectors.shape[2] else alignment
    size = settings.value(settings.Key.Vector_Size)
    colours = [Colour(*settings.value(settings.Key.Vector_1_Colour)),
               Colour(*settings.value(settings.Key.Vector_2_Colour))]

    for k in range(vectors.shape[2]):
        start_point = points.points
        for j in range(0, vectors.shape[1]//3):
            end_point = start_point + size * vectors[:, j*3:j*3+3, k]

            vertices = np.column_stack((start_point, end_point)).reshape(-1, 3)

            child = Node()
            child.vertices = vertices
            child.indices = np.arange(vertices.shape[0])
            if j < 2:
                child.colour = colours[j]
            else:
                np.random.seed(j)
                child.colour = Colour(*np.random.random(3))
            child.render_mode = None
            child.visible = alignment == k
            child.render_primitive = Node.RenderPrimitive.Lines

            measurement_vector_node.addChild(child)

    return measurement_vector_node


def create_plane_node(plane, width, height):
    """Creates node for cross-sectional plane

    :param plane: plane normal and point
    :type plane: Plane
    :param width: plane width
    :type width: float
    :param height: plane height
    :type height: float
    :return: node containing plane
    :rtype: Node
    """
    plane_mesh = create_plane(plane, width, height)

    node = Node(plane_mesh)
    node.render_mode = Node.RenderMode.Transparent
    node.colour = Colour(*settings.value(settings.Key.Cross_Sectional_Plane_Colour))

    return node


def create_beam_node(instrument, bounds, visible=False):
    """Creates node for beam

    :param instrument: instrument object
    :type instrument: Instrument
    :param bounds: bounding box of the instrument scene
    :type bounds: BoundingBox
    :param visible: indicates node is visible
    :type visible: bool
    :return: node containing beam
    :rtype: Node
    """
    node = Node()
    node.render_mode = Node.RenderMode.Solid
    node.colour = Colour(0.80, 0.45, 0.45)
    node.visible = visible

    jaws = instrument.jaws
    detectors = instrument.detectors
    q_vectors = instrument.q_vectors
    gauge_volume = instrument.gauge_volume

    width, height = jaws.aperture
    beam_source = jaws.beam_source
    beam_direction = jaws.beam_direction
    cuboid_axis = np.array([0., 1., 0.])

    bound_max = np.dot(bounds.max - beam_source, beam_direction)
    bound_min = np.dot(bounds.min - beam_source, beam_direction)
    depth = max(bound_min, bound_max)

    mesh = create_cuboid(width, height, depth)
    m = Matrix44.fromTranslation(beam_source)
    m[0:3, 0:3] = rotation_btw_vectors(beam_direction, cuboid_axis)
    m = m @ Matrix44.fromTranslation([0., -depth/2, 0.])
    mesh.transform(m)

    if instrument.beam_in_gauge_volume:
        for index, detector in enumerate(detectors.values()):
            if detector.current_collimator is None:
                continue
            bound_max = np.dot(bounds.max - gauge_volume, detector.diffracted_beam)
            bound_min = np.dot(bounds.min - gauge_volume, detector.diffracted_beam)
            depth = max(bound_min, bound_max)
            sub_mesh = create_cuboid(width, height, depth)
            m = Matrix44.fromTranslation(gauge_volume)
            m[0:3, 0:3] = rotation_btw_vectors(cuboid_axis, detector.diffracted_beam)
            m = m @ Matrix44.fromTranslation([0., depth/2, 0.])
            mesh.append(sub_mesh.transformed(m))

            # draw q_vector
            end_point = gauge_volume + q_vectors[index] * depth/2
            vertices = np.array((gauge_volume, end_point))

            child = Node()
            child.vertices = vertices
            child.indices = np.arange(vertices.shape[0])
            child.colour = Colour(0.60, 0.25, 0.25)
            child.render_primitive = Node.RenderPrimitive.Lines
            node.addChild(child)

    node.vertices = mesh.vertices
    node.indices = mesh.indices
    node.normals = mesh.normals

    return node


def create_instrument_node(instrument, return_ids=False):
    """Creates node for a given instrument.

    :param instrument: instrument
    :type instrument: Instrument
    :param return_ids: flag indicating ids are required
    :type return_ids: bool
    :return: 3D model of instrument and dict to identify nodes
    :rtype: Tuple[Node, Dict[str, int]]
    """
    node = Node()

    count = 0
    model = instrument.positioning_stack.model()
    count += len(model.flatten().children)
    cache = {Attributes.Positioner.value: count}
    node.addChild(model)

    for detector in instrument.detectors.values():
        model = detector.model()
        count += len(model.flatten().children)
        cache[f'{Attributes.Detector.value}_{detector.name}'] = count
        node.addChild(model)

    model = instrument.jaws.model()
    count += len(model.flatten().children)
    cache[Attributes.Jaws.value] = count
    node.addChild(model)

    for name, model in instrument.fixed_hardware.items():
        count += 1
        cache[f'{Attributes.Fixture.value}_{name}'] = count
        node.addChild(Node(model))

    if return_ids:
        return node.flatten(), cache
    return node.flatten()
