from enum import Enum, unique
import numpy as np
from scipy import optimize
from PyQt5 import QtCore
from ..math.matrix import Matrix44
from ..math.transform import rotation_btw_vectors
from ..math.quaternion import Quaternion, QuaternionVectorPair
from ..math.vector import Vector3
from ..scene.node import Node


class SerialManipulator:
    def __init__(self, links, base=None, tool=None, base_mesh=None, name=''):
        """ This class defines a open loop kinematic chain.

        :param links: list of link objects
        :type links: List[sscanss.core.instrument.robotics.Link]
        :param base: base matrix. None sets base to an identity matrix
        :type base: Union[None, sscanss.core.math.matrix.Matrix44]
        :param tool: tool matrix. None sets tool to an identity matrix
        :type tool: Union[None, sscanss.core.math.matrix.Matrix44]
        :param base_mesh: mesh object for the base of the manipulator
        :type base_mesh: Union[None, sscanss.core.mesh.utility.Mesh]
        :param name: name of the manipulator
        :type name: str
        """
        self.name = name
        self.links = links
        self.base = Matrix44.identity() if base is None else base
        self.default_base = self.base
        self.tool = Matrix44.identity() if tool is None else tool
        self.base_mesh = base_mesh

    def fkine(self, q, start_index=0, end_index=None, include_base=True, ignore_locks=False, setpoint=True):
        """ Moves the manipulator to specified configuration and returns the forward kinematics
        transformation matrix of the manipulator. The transformation matrix can be computed for a subset
        of links i.e a start index to end index

        :param q: list of joint offsets to move to. The length must be equal to number of links
        :type q: List[float]
        :param start_index: index to start
        :type start_index: int
        :param end_index: index to end. None sets end_index to index of last link
        :type end_index: Union[None, int]
        :param include_base: indicates that base matrix should be included
        :type include_base: bool
        :param ignore_locks: indicates that joint locks should be ignored
        :type ignore_locks: bool
        :param setpoint: indicates that given configuration, q is a setpoint
        :type setpoint: bool
        :return: Forward kinematic transformation matrix
        :rtype: sscanss.core.math.matrix.Matrix44
        """
        link_count = self.numberOfLinks

        start = 0 if start_index < 0 else start_index
        end = link_count if end_index is None or end_index > link_count else end_index

        base = self.base if include_base and start == 0 else Matrix44.identity()
        tool = self.tool if end == link_count else Matrix44.identity()

        qs = QuaternionVectorPair.identity()
        for i in range(start, end):
            self.links[i].move(q[i], ignore_locks, setpoint)
            qs *= self.links[i].quaterionVectorPair

        return base @ qs.toMatrix() @ tool

    def resetOffsets(self):
        """
        resets link offsets to the defaults
        """
        for link in self.links:
            link.reset()

    def reset(self):
        """
         resets  base matrix, link offsets, locks, and limits to the defaults
        """
        self.base = self.default_base
        for link in self.links:
            link.reset()
            link.locked = False
            link.ignore_limits = False

    @property
    def numberOfLinks(self):
        """ number of links in manipulator

        :return: number of links
        :rtype: int
        """
        return len(self.links)

    @property
    def set_points(self):
        """ expected configuration (set-point for all links) of the manipulator.
        This is useful when the animating the manipulator in that case the actual configuration
        differs from the set-point or final configuration.

        :return: expected configuration
        :rtype: list[float]
        """
        return [link.set_point for link in self.links]

    @set_points.setter
    def set_points(self, q):
        """ setter for set_points

        :param q: expected configuration
        :type q: list[float]
        """
        for offset, link in zip(q, self.links):
            link.set_point = offset

    @property
    def configuration(self):
        """ current configuration (joint offsets for all links) of the manipulators

        :return: current configuration
        :rtype: list[float]
        """
        return [link.offset for link in self.links]

    @property
    def pose(self):
        """ the pose of the end effector of the manipulator

        :return: transformation matrix
        :rtype: sscanss.core.math.matrix.Matrix44
        """
        qs = QuaternionVectorPair.identity()
        for link in self.links:
            qs *= link.quaterionVectorPair

        return self.base @ qs.toMatrix() @ self.tool

    def model(self, matrix=None):
        """ Generates 3d model of the manipulator and transforms it with specified matrix.

        :param matrix: transformation matrix
        :type matrix: Union[None, sscanss.core.math.matrix.Matrix44]
        :return: 3D model of manipulator
        :rtype: sscanss.core.scene.node.Node
        """
        node = Node()
        node.render_mode = Node.RenderMode.Outline

        if matrix is None:
            base = self.base
        else:
            base = matrix @ self.base

        if self.base_mesh is not None:
            transformed_mesh = self.base_mesh.transformed(base)
            child = Node(transformed_mesh)
            child.render_mode = None

            node.addChild(child)

        qs = QuaternionVectorPair.identity()
        joint_pos = Vector3()
        up = Vector3([0., 0., 1.])
        for link in self.links:
            qs *= link.quaterionVectorPair
            rot = rotation_btw_vectors(up, link.joint_axis)
            m = Matrix44.identity()
            m[0:3, 0:3] = qs.quaternion.toMatrix() @ rot
            m[0:3, 3] = joint_pos if link.type == Link.Type.Revolute else qs.vector

            m = base @ m
            if link.mesh is not None:
                transformed_mesh = link.mesh.transformed(m)
                child = Node(transformed_mesh)
                child.render_mode = None

                node.addChild(child)
            joint_pos = qs.vector

        return node


class Link:
    @unique
    class Type(Enum):
        Revolute = 0
        Prismatic = 1

    def __init__(self, axis, point, joint_type, default_offset=0.0, upper_limit=None, lower_limit=None,
                 mesh=None, name=''):
        """ This class represents a link/joint that belongs to a serial manipulator.
        The joint could be revolute or prismatic. The link is represented using the Quaternion-vector
        kinematic notation.

        :param axis: axis of rotation or translation
        :type axis: List[float]
        :param point: centre of joint
        :type point: List[float]
        :param joint_type: joint type
        :type joint_type: Link.Type
        :param default_offset: default joint offset
        :type default_offset: float
        :param upper_limit: upper limit of joint
        :type upper_limit: float
        :param lower_limit: lower limit of joint
        :type lower_limit: float
        :param mesh: mesh object for the base
        :type mesh: sscanss.core.mesh.utility.Mesh
        :param name: name of the link
        :type name: str
        """
        self.joint_axis = Vector3(axis)

        if self.joint_axis.length < 0.00001:
            raise ValueError('The joint axis cannot be a zero vector.')

        self.quaternion = Quaternion.fromAxisAngle(self.joint_axis, 0.0)
        self.vector = Vector3(point)
        self.home = Vector3(point)
        self.type = joint_type
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.default_offset = default_offset
        self.set_point = default_offset
        self.mesh = mesh
        self.name = name
        self.locked = False
        self.ignore_limits = False
        self.reset()

    def move(self, offset, ignore_locks=False, setpoint=True):
        """ moves link by the specified offset

        :param offset: joint offset
        :type offset: float
        :param ignore_locks: indicates that joint locks should be ignored
        :type ignore_locks: bool
        :param setpoint: indicates that given offset is a setpoint
        :type setpoint: bool
        """
        if self.locked and not ignore_locks:
            return

        self.offset = offset
        self.set_point = offset if setpoint else self.set_point
        if self.type == Link.Type.Revolute:
            self.quaternion = Quaternion.fromAxisAngle(self.joint_axis, offset)
            self.vector = self.quaternion.rotate(self.home)
        else:
            self.vector = self.home + self.joint_axis * offset

    def reset(self):
        """
        moves link to it default offset
        """
        self.move(self.default_offset, True)

    @property
    def transformationMatrix(self):
        """ pose of the link

        :return: pose of the link
        :rtype: sscanss.core.math.matrix.Matrix44
        """
        return self.quaterionVectorPair.toMatrix()

    @property
    def quaterionVectorPair(self):
        """ pose of the link

        :return: pose of the link
        :rtype: sscanss.core.math.quaternion.QuaternionVectorPair
        """
        return QuaternionVectorPair(self.quaternion, self.vector)


def joint_space_trajectory(start_pose, stop_pose, step):
    """  Generates a trajectory from a start to end configuration.

    :param start_pose: inclusive start joint configuration/offsets
    :type start_pose: List[float]
    :param stop_pose: inclusive stop joint configuration/offsets
    :type stop_pose: List[float]
    :param step: number of steps
    :type step: int
    :return: array of configurations defining the trajectory
    :rtype: numpy.ndarray
    """
    dof = len(start_pose)
    trajectory = np.zeros((step, dof))

    for i in range(dof):
        t = cubic_polynomial_trajectory(start_pose[i], stop_pose[i], step=step)
        trajectory[:, i] = t

    return trajectory


def cubic_polynomial_trajectory(p0, p1, step=100):
    """  Generates a trajectory from p0 to p1 using a cubic polynomial.

    :param p0: inclusive start value
    :type p0: float
    :param p1: inclusive stop value
    :type p1: float
    :param step: number of steps
    :type step: int
    :return: offsets in the trajectory
    :rtype: numpy.ndarray
    """

    t0 = 0.0
    tf = step
    t = np.linspace(t0, tf, step)

    t0_2 = t0 * t0
    t0_3 = t0_2 * t0

    tf_2 = tf * tf
    tf_3 = tf_2 * tf

    m = [[1.0, t0, t0_2, t0_3],
         [0.0, 1.0, 2 * t0, 3 * t0_2],
         [1.0, tf, tf_2, tf_3],
         [0.0, 1.0, 2 * tf, 3 * tf_2]]

    v0 = v1 = 0.0
    b = [p0, v0, p1, v1]
    a = np.dot(np.linalg.inv(m), b)

    pd = np.polyval(a[::-1], t)

    return pd


class Sequence(QtCore.QObject):
    frame_changed = QtCore.pyqtSignal()

    def __init__(self, frames, start, stop, duration, step):
        """ This class creates an animation from start to end configuration

        :param frames: function to generate frame at each way point
        :type frames: method
        :param start: inclusive start joint configuration/offsets
        :type start: List[float]
        :param stop: inclusive start joint configuration/offsets
        :type stop: List[float]
        :param duration: time duration in milliseconds
        :type duration: int
        :param step: number of steps
        :type step: int
        """
        super().__init__()

        self.timeline = QtCore.QTimeLine(duration, self)
        self.timeline.setFrameRange(0, step - 1)

        self.trajectory = joint_space_trajectory(start, stop, step)

        self.timeline.setCurrentTime(self.timeline.duration())
        self.timeline.frameChanged.connect(self.animate)
        self.frames = frames
        self.step = step

    def start(self):
        """
        starts the animation
        """
        self.timeline.start()

    def stop(self):
        """
        stops the animation
        """
        if self.timeline.currentTime() < self.timeline.duration():
            self.timeline.setCurrentTime(self.timeline.duration())

        self.timeline.stop()

    def isRunning(self):
        """ indicates if the animation is running

        :return: indicates if the animation is running
        :rtype: bool
        """
        if self.timeline.state() == QtCore.QTimeLine.Running:
            return True

        return False

    def animate(self, index):
        """ Calls the frame function and emits signal to notify frame change

        :param index: current step/frame in the animation
        :type index: int
        """
        self.frames(self.trajectory[index, :])
        self.frame_changed.emit()


class StopOptimizingException(Exception):
    pass


def numeric_inverse_kinematics(ri, target_pose, current_pose, bounds, tol):
    best_result = np.inf
    tolerance = tol * tol

    conf = np.array(ri.configuration)
    state = [not l.locked for l in ri.links]
    q0 = conf[state]
    _bounds = np.array(bounds)[state]

    def opt(q):
        nonlocal best_result
        nonlocal conf

        conf[state] = q
        H = ri.fkine(conf) @ ri.tool_link
        err1 = np.zeros(6)
        err1[0:3] = target_pose[0:3] - (H[0:3, 0:3] @ current_pose[0:3] + H[0:3, 3])
        err1[3:6] = target_pose[3:6] - H[0:3, 0:3] @ current_pose[3:6]
        err = np.dot(err1, err1)
        if err < best_result:
            best_result = err

        if err < tolerance:
            raise StopOptimizingException

        return err

    def callback(_x, f, _context):
        if f < tolerance:
            return True

        return False

    best_result = opt(q0)
    if best_result < tolerance:
        return q0

    try:
        r = optimize.dual_annealing(opt, _bounds, x0=q0, local_search_options={'method': 'Nelder-Mead'},
                                    callback=callback, seed=10, maxiter=100, initial_temp=500, no_local_search=False)
        x = r.x
    except StopOptimizingException:
        x = conf

    return x