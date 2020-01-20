import unittest
import unittest.mock as mock
from PyQt5.QtWidgets import QUndoStack
import numpy as np
from sscanss.core.geometry import Mesh
from sscanss.core.util import Primitives, PointType, POINT_DTYPE, CommandID, LoadVector, StrainComponents
from sscanss.ui.window.view import MainWindow
from sscanss.ui.dialogs import ProgressDialog
from sscanss.ui.window.dock_manager import DockManager
from sscanss.ui.window.presenter import MainWindowPresenter
from sscanss.ui.commands import (RotateSample, TranslateSample, InsertPrimitive, DeleteSample, MergeSample,
                                 TransformSample, InsertPoints, DeletePoints, EditPoints, MovePoints, ChangeMainSample,
                                 InsertAlignmentMatrix, RemoveVectors, RemoveVectorAlignment, InsertSampleFromFile,
                                 InsertPointsFromFile, InsertVectorsFromFile, InsertVectors)
from tests.helpers import TestSignal


class TestTransformCommands(unittest.TestCase):
    @mock.patch('sscanss.ui.window.presenter.MainWindowModel', autospec=True)
    def setUp(self, model_mock):
        self.view_mock = mock.create_autospec(MainWindow)
        self.model_mock = model_mock
        self.model_mock.return_value.instruments = ['dummy']
        self.presenter = MainWindowPresenter(self.view_mock)

        vertices = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        normals = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]])
        indices = np.array([0, 1, 2])
        self.mesh_1 = Mesh(vertices, indices, normals)

        vertices = np.array([[7, 8, 9], [4, 5, 6], [1, 2, 3]])
        normals = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]])
        indices = np.array([1, 0, 2])
        self.mesh_2 = Mesh(vertices, indices, normals)
        self.sample = {'1': self.mesh_1, '2': self.mesh_2}

    def testRotateSampleCommand(self):
        self.model_mock.return_value.sample = self.sample.copy()

        # Command to rotate sample '1'
        angles = [0, 90, 0]
        cmd = RotateSample(angles, '1', self.presenter)
        cmd.redo()

        # Check that angles are converted to radians
        np.testing.assert_array_almost_equal(cmd.angles, np.radians(angles), decimal=5)

        expected_vertices = np.array([[3, 2, -1], [6, 5, -4], [9, 8, -7]])
        expected_normals = np.array([[1, 0, 0], [0, 1, 0], [0, 0, -1]])
        sample = self.model_mock.return_value.sample
        # Check that redo rotates vertices, normals but not the indices of sample '1'
        np.testing.assert_array_almost_equal(sample['1'].vertices, expected_vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, expected_normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)

        # Check that redo does not rotate sample '2'
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        cmd.undo()
        sample = self.model_mock.return_value.sample
        # Check that undo reverses the rotation on sample '1'
        np.testing.assert_array_almost_equal(sample['1'].vertices, self.mesh_1.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)

        # Check that undo does not touch sample '2'
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        # Command to rotate all the samples
        angles = [30, 60, 90]
        cmd = RotateSample(angles, 'All', self.presenter)
        cmd.redo()

        expected_vertices_1 = np.array([[1.59807621, -0.75, 3.29903811],
                                       [2.69615242, -0.20096189, 8.34807621],
                                       [3.79422863, 0.34807621, 13.39711432]])
        expected_normals_1 = np.array([[0.866025, -0.25, 0.433013], [-0.5, -0.433013, 0.75], [0, 0.866025, 0.5]])
        expected_vertices_2 = np.array([[3.79422863, 0.34807621, 13.39711432],
                                        [2.69615242, -0.20096189, 8.34807621],
                                        [1.59807621, -0.75, 3.29903811]])
        expected_normals_2 = np.array([[-0.5, -0.433013, 0.75], [0.866025, -0.25, 0.433013], [0, 0.866025, 0.5]])
        sample = self.model_mock.return_value.sample
        # Check that redo rotates vertices, normals but not the indices of all samples'
        np.testing.assert_array_almost_equal(sample['1'].vertices, expected_vertices_1, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, expected_normals_1, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)
        np.testing.assert_array_almost_equal(sample['2'].vertices, expected_vertices_2, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, expected_normals_2, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        cmd.undo()
        sample = self.model_mock.return_value.sample
        # Check that undo reverses the rotation on all samples
        np.testing.assert_array_almost_equal(sample['1'].vertices, self.mesh_1.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

    def testTranslateSampleCommand(self):
        self.model_mock.return_value.sample = self.sample.copy()

        # Command to translate sample '2'
        offset = [10, -5, 3]
        cmd = TranslateSample(offset, '2', self.presenter)
        cmd.redo()

        expected_vertices = np.array([[17, 3, 12], [14, 0, 9], [11, -3, 6]])
        sample = self.model_mock.return_value.sample
        # Check that redo translates vertices but not the normals and indices of sample '2'
        np.testing.assert_array_almost_equal(sample['2'].vertices, expected_vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        # Check that redo does not translate sample '2'
        np.testing.assert_array_almost_equal(sample['1'].vertices, self.mesh_1.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)

        cmd.undo()
        sample = self.model_mock.return_value.sample
        # Check that undo reverses the translation on sample '2'
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        # Check that undo does not touch sample '1'
        np.testing.assert_array_almost_equal(sample['1'].vertices, self.mesh_1.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)

        # Command to translate all the samples
        offset = [30, 60, 90]
        cmd = TranslateSample(offset, 'All', self.presenter)
        cmd.redo()

        expected_vertices_1 = np.array([[31, 62, 93], [34, 65, 96], [37, 68, 99]])
        expected_vertices_2 = np.array([[37, 68, 99], [34, 65, 96], [31, 62, 93]])
        sample = self.model_mock.return_value.sample
        # Check that redo translates vertices, normals but not the indices of all samples'
        np.testing.assert_array_almost_equal(sample['1'].vertices, expected_vertices_1, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)
        np.testing.assert_array_almost_equal(sample['2'].vertices, expected_vertices_2, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        cmd.undo()
        sample = self.model_mock.return_value.sample
        # Check that undo reverses the translation on all samples
        np.testing.assert_array_almost_equal(sample['1'].vertices, self.mesh_1.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

    def testTransformSampleCommand(self):
        self.model_mock.return_value.sample = self.sample.copy()

        # Command to transform sample '1'
        matrix = [[0., 0., 1., 10.], [0., 1., 0., -5.], [1., 0., 0., 0.4], [0., 0., 0., 1.]]
        cmd = TransformSample(matrix, '1', self.presenter)

        cmd.redo()
        expected_vertices = np.array([[13., -3., 1.4], [16., 0., 4.4], [19., 3., 7.4]])
        expected_normals = np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        sample = self.model_mock.return_value.sample

        # Check that redo transforms vertices, normals but not the indices of sample '1'
        np.testing.assert_array_almost_equal(sample['1'].vertices, expected_vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, expected_normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)

        # Check that redo does not rotate sample '2'
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        cmd.undo()
        sample = self.model_mock.return_value.sample
        # Check that undo reverses the translation on sample '2'
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        # Check that undo does not touch sample '1'
        np.testing.assert_array_almost_equal(sample['1'].vertices, self.mesh_1.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)

        # Command to translate all the samples
        cmd = TransformSample(matrix, 'All', self.presenter)
        cmd.redo()

        expected_vertices_2 = np.array([[19.,  3.,  7.4], [16.,  0.,  4.4], [13., -3.,  1.4]])
        expected_normals_2 = np.array([[0., 1., 0.],[1., 0., 0.],[0., 0., 1.]])
        sample = self.model_mock.return_value.sample
        # Check that redo translates vertices, normals but not the indices of all samples'
        np.testing.assert_array_almost_equal(sample['1'].vertices, expected_vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, expected_normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)
        np.testing.assert_array_almost_equal(sample['2'].vertices, expected_vertices_2, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, expected_normals_2, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)

        cmd.undo()
        sample = self.model_mock.return_value.sample
        # Check that undo reverses the translation on all samples
        np.testing.assert_array_almost_equal(sample['1'].vertices, self.mesh_1.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['1'].normals, self.mesh_1.normals, decimal=5)
        np.testing.assert_array_equal(sample['1'].indices, self.mesh_1.indices)
        np.testing.assert_array_almost_equal(sample['2'].vertices, self.mesh_2.vertices, decimal=5)
        np.testing.assert_array_almost_equal(sample['2'].normals, self.mesh_2.normals, decimal=5)
        np.testing.assert_array_equal(sample['2'].indices, self.mesh_2.indices)


class TestInsertCommands(unittest.TestCase):
    @mock.patch('sscanss.ui.window.presenter.MainWindowModel', autospec=True)
    def setUp(self, model_mock):
        self.view_mock = mock.create_autospec(MainWindow)
        self.model_mock = model_mock
        self.model_mock.return_value.instruments = ['dummy']
        self.presenter = MainWindowPresenter(self.view_mock)

    def testInsertPrimitiveCommand(self):
        self.model_mock.return_value.sample = {}

        # Command to add a cuboid to sample
        args = {'width': 50.000, 'height': 100.000, 'depth': 200.000, 'name': 'Test'}
        cmd = InsertPrimitive(Primitives.Cuboid, args, self.presenter, True)
        cmd.redo()
        self.model_mock.return_value.addMeshToProject.assert_called_once()
        cmd.undo()
        self.model_mock.return_value.removeMeshFromProject.assert_called_once()

        # Command to add a cylinder to sample
        self.model_mock.reset_mock()
        args = {'radius': 100.000, 'height': 200.000, 'name': 'Test'}
        cmd = InsertPrimitive(Primitives.Cylinder, args, self.presenter, True)
        cmd.redo()
        self.model_mock.return_value.addMeshToProject.assert_called_once()

        # Command to add a sphere to sample
        self.model_mock.reset_mock()
        args = {'radius': 100.000, 'name': 'Test'}
        cmd = InsertPrimitive(Primitives.Sphere, args, self.presenter, True)
        cmd.redo()
        self.model_mock.return_value.addMeshToProject.assert_called_once()

        # Command to add a tube to sample
        self.model_mock.reset_mock()
        args = {'outer_radius': 100.000, 'inner_radius': 50.000, 'height': 200.000, 'name': 'Test'}
        cmd = InsertPrimitive(Primitives.Tube, args, self.presenter, False)
        self.assertIsNone(cmd.old_sample)
        cmd.redo()
        self.assertEqual(cmd.old_sample, {})
        self.model_mock.return_value.addMeshToProject.assert_called_once()
        cmd.undo()
        self.model_mock.return_value.removeMeshFromProject.assert_not_called()

    @mock.patch('sscanss.ui.commands.insert.logging', autospec=True)
    @mock.patch('sscanss.ui.commands.insert.Worker', autospec=True)
    def testInsertSampleFromFileCommand(self, worker_mock, _):
        worker_mock.return_value.job_succeeded = TestSignal()
        worker_mock.return_value.job_failed = TestSignal()
        worker_mock.return_value.finished = TestSignal()
        sample_key = 'random'
        sample_name = f'{sample_key}.stl'
        sample = {sample_key: [0]}
        self.model_mock.return_value.uniqueKey.return_value = sample_key
        self.model_mock.return_value.sample = sample
        self.view_mock.progress_dialog = mock.create_autospec(ProgressDialog)
        self.view_mock.docks = mock.create_autospec(DockManager)
        self.view_mock.undo_stack = mock.create_autospec(QUndoStack)

        cmd = InsertSampleFromFile(sample_name, self.presenter, True)
        cmd.redo()
        self.view_mock.progress_dialog.show.assert_called_once()
        self.assertIsNone(cmd.old_sample)

        worker_mock.return_value.job_succeeded.emit()
        self.view_mock.docks.showSampleManager.assert_called_once()
        worker_mock.return_value.finished.emit()
        self.view_mock.progress_dialog.close.assert_called_once()
        worker_mock.return_value.job_failed.emit(Exception())
        self.assertTrue(cmd.isObsolete())
        self.model_mock.return_value.addMeshToProject.assert_not_called()
        cmd.undo()
        self.assertListEqual(cmd.new_mesh, sample[sample_key])
        self.model_mock.return_value.removeMeshFromProject.assert_called_once()
        cmd.redo()
        self.model_mock.return_value.addMeshToProject.assert_called()

        cmd = InsertSampleFromFile(sample_name, self.presenter, False)
        cmd.redo()
        self.assertIsNotNone(cmd.old_sample)
        cmd.old_sample = None
        cmd.undo()
        self.assertIsNone(self.model_mock.return_value.sample)

    def testDeleteSampleCommand(self):
        initial_sample = {'1': None, '2': None, '3': None}
        self.model_mock.return_value.sample = initial_sample

        # Command to delete multiple samples
        cmd = DeleteSample(['1', '3'], self.presenter)
        cmd.redo()
        self.assertEqual({'1': None, '3': None}, cmd.deleted_mesh)
        self.model_mock.return_value.removeMeshFromProject.assert_called_once()

        # Since removeMeshFromProject() is a mock object
        # we manually remove sample for the undo test
        self.model_mock.return_value.sample = {'2': None}
        cmd.undo()
        sample = self.model_mock.return_value.sample
        self.assertEqual(list(sample.keys()), list(initial_sample.keys()))
        self.assertEqual(sample, initial_sample)

        self.model_mock.reset_mock()
        cmd = DeleteSample(['2'], self.presenter)
        cmd.redo()
        self.assertEqual({'2': None}, cmd.deleted_mesh)
        self.model_mock.return_value.removeMeshFromProject.assert_called_once()

    def testMergeSampleCommand(self):
        vertices = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        normals = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]])
        indices = np.array([0, 1, 2])
        mesh_1 = Mesh(vertices, indices, normals)

        vertices = np.array([[7, 8, 9], [4, 5, 6], [1, 2, 3]])
        normals = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]])
        indices = np.array([1, 0, 2])
        mesh_2 = Mesh(vertices, indices, normals)

        initial_sample = {'1': mesh_1, '2': mesh_2, '3': None}
        self.model_mock.return_value.sample = initial_sample

        # Command to add a non-existent file to sample
        cmd = MergeSample(['1', '2'], self.presenter)
        cmd.redo()
        self.assertEqual([('1', 0), ('2', 3)], cmd.merged_mesh)
        self.assertEqual(initial_sample, {'3': None})
        self.model_mock.return_value.addMeshToProject.assert_called_once()

        vertices = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [7, 8, 9], [4, 5, 6], [1, 2, 3]])
        normals = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 0]])
        indices = np.array([0, 1, 2, 1, 0, 2])
        initial_sample = {'1': mesh_1, '2': mesh_2, '3': None}
        merged = Mesh(vertices, indices, normals)
        cmd.new_name = 'merged'
        self.model_mock.return_value.sample = {'3': None, 'merged': merged}

        cmd.undo()
        sample = self.model_mock.return_value.sample
        self.assertEqual(list(sample.keys()), list(initial_sample.keys()))

    def testChangeMainSampleCommand(self):
        initial_sample = {'1': 'a', '2': 'b', '3': 'c'}
        self.model_mock.return_value.sample = initial_sample

        # Command to delete multiple samples
        cmd = ChangeMainSample('3', self.presenter)
        cmd.redo()
        self.assertListEqual(list(self.model_mock.return_value.sample.keys()), ['3', '1', '2'])
        self.assertListEqual(list(self.model_mock.return_value.sample.values()), ['c', 'a', 'b'])
        cmd.undo()
        self.assertListEqual(list(self.model_mock.return_value.sample.keys()), list(initial_sample.keys()))
        self.assertListEqual(list(self.model_mock.return_value.sample.values()), list(initial_sample.values()))

        cmd.redo()
        self.assertTrue(cmd.mergeWith(ChangeMainSample('2', self.presenter)))
        self.assertFalse(cmd.isObsolete())
        cmd.undo()
        self.assertListEqual(list(self.model_mock.return_value.sample.keys()), list(initial_sample.keys()))
        self.assertListEqual(list(self.model_mock.return_value.sample.values()), list(initial_sample.values()))
        cmd.redo()
        self.assertListEqual(list(self.model_mock.return_value.sample.keys()), ['2', '3', '1'])
        self.assertListEqual(list(self.model_mock.return_value.sample.values()), ['b', 'c', 'a'])

        self.assertTrue(cmd.mergeWith(ChangeMainSample('1', self.presenter)))
        self.assertTrue(cmd.isObsolete())
        self.assertEqual(cmd.id(), CommandID.ChangeMainSample)

    @mock.patch('sscanss.ui.commands.insert.logging', autospec=True)
    @mock.patch('sscanss.ui.commands.insert.Worker', autospec=True)
    def testInsertPointsFromFileCommand(self, worker_mock, _):
        worker_mock.return_value.job_succeeded = TestSignal()
        worker_mock.return_value.job_failed = TestSignal()
        worker_mock.return_value.finished = TestSignal()
        filename = 'random'
        self.view_mock.progress_dialog = mock.create_autospec(ProgressDialog)
        self.view_mock.docks = mock.create_autospec(DockManager)
        self.view_mock.undo_stack = mock.create_autospec(QUndoStack)

        self.model_mock.return_value.fiducials = [1, 2]
        cmd = InsertPointsFromFile(filename, PointType.Fiducial, self.presenter)
        cmd.redo()
        self.view_mock.progress_dialog.show.assert_called_once()
        worker_mock.return_value.job_succeeded.emit()
        self.view_mock.docks.showPointManager.assert_called_once_with(PointType.Fiducial)
        worker_mock.return_value.finished.emit()
        self.view_mock.progress_dialog.close.assert_called_once()
        worker_mock.return_value.job_failed.emit(Exception())
        self.assertTrue(cmd.isObsolete())
        self.model_mock.return_value.addMeshToProject.assert_not_called()
        self.model_mock.return_value.fiducials = [1, 2, 3]
        cmd.undo()
        self.assertListEqual(list(cmd.new_points), [3])
        self.model_mock.return_value.removePointsFromProject.assert_called_once_with(slice(2, 3), PointType.Fiducial)
        cmd.redo()
        self.model_mock.return_value.addPointsToProject.assert_called_once_with(np.array([3]), PointType.Fiducial)

        self.model_mock.return_value.measurement_points = [1, 2]
        cmd = InsertPointsFromFile(filename, PointType.Measurement, self.presenter)
        cmd.undo()
        self.model_mock.return_value.removePointsFromProject.assert_called_with(slice(2, 2), PointType.Measurement)

    def testInsertPointsCommand(self):
        self.model_mock.return_value.fiducials = []
        self.model_mock.return_value.measurement_points = []

        # Command to add a fiducial point
        points = [([0.0, 0.0, 0.0], False)]
        args = (points, PointType.Fiducial)
        cmd = InsertPoints(*args, self.presenter)
        self.assertEqual(cmd.old_count, 0)
        cmd.redo()
        self.model_mock.return_value.addPointsToProject.assert_called_once_with(*args)
        self.model_mock.return_value.fiducials = args[0]
        cmd.undo()
        self.model_mock.return_value.removePointsFromProject.assert_called_once_with(slice(0, 1, None), args[1])

        self.model_mock.reset_mock()
        self.model_mock.return_value.fiducials = []
        self.model_mock.return_value.measurement_points = points

        # Command to add  measurement points
        points = [([1.0, 0.0, 0.0], False), ([1.0, 1.0, 0.0], True)]
        args = (points, PointType.Measurement)
        cmd = InsertPoints(*args, self.presenter)
        self.assertEqual(cmd.old_count, 1)
        cmd.redo()
        self.model_mock.return_value.addPointsToProject.assert_called_once_with(*args)
        self.model_mock.return_value.measurement_points.extend(args[0])
        cmd.undo()
        self.model_mock.return_value.removePointsFromProject.assert_called_once_with(slice(1, 3, None), args[1])

    def testDeletePointsCommand(self):
        points = np.rec.array([([0.0, 0.0, 0.0], False)], dtype=POINT_DTYPE)
        points_after_delete = np.recarray((0,), dtype=POINT_DTYPE)
        self.model_mock.return_value.fiducials = points
        self.model_mock.return_value.measurement_points = []
        self.model_mock.return_value.measurement_vectors = []

        # Command to delete a fiducial point
        args = ([0], PointType.Fiducial)
        cmd = DeletePoints(*args, self.presenter)
        self.assertIsNone(cmd.removed_points)
        self.assertIsNone(cmd.removed_vectors)
        cmd.redo()
        self.model_mock.return_value.fiducials = points_after_delete
        self.assertEqual(cmd.removed_points, points[args[0]])
        self.assertIsNone(cmd.removed_vectors)
        self.model_mock.return_value.removePointsFromProject.assert_called_once_with(*args)
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, points)
        self.assertEqual(len(self.model_mock.return_value.measurement_points), 0)
        self.assertEqual(len(self.model_mock.return_value.measurement_vectors), 0)

        self.model_mock.reset_mock()
        points = np.rec.array([([0.0, 0.0, 0.0], False), ([2.0, 0.0, 1.0], True), ([0.0, 1.0, 1.0], True)],
                              dtype=POINT_DTYPE)
        vectors = np.array([[[0.0], [0.0], [0.0]], [[0.0], [1.0], [0.0]], [[0.0], [0.0], [1.0]]])

        self.model_mock.return_value.fiducials = []
        self.model_mock.return_value.measurement_points = points
        self.model_mock.return_value.measurement_vectors = vectors

        # Command to delete some measurement points
        indices = [2, 0]
        sorted_indices = [0, 2]
        points_after_delete = np.delete(points, sorted_indices, 0)
        vectors_after_delete = np.delete(vectors, sorted_indices, 0)
        args = (indices, PointType.Measurement)
        cmd = DeletePoints(*args, self.presenter)
        self.assertIsNone(cmd.removed_points)
        self.assertIsNone(cmd.removed_vectors)
        cmd.redo()
        self.model_mock.return_value.measurement_points = points_after_delete
        self.model_mock.return_value.measurement_vectors = vectors_after_delete
        np.testing.assert_equal(cmd.removed_points, points[sorted_indices])
        np.testing.assert_equal(cmd.removed_vectors, vectors[sorted_indices])
        self.model_mock.return_value.removePointsFromProject.assert_called_once_with(sorted_indices, args[1])
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, points)
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, vectors)
        self.assertEqual(len(self.model_mock.return_value.fiducials), 0)

    def testEditPointsCommand(self):
        points = np.rec.array([([0.0, 0.0, 0.0], False)], dtype=POINT_DTYPE)
        new_points = np.rec.array([([1.0, 1.0, 1.0], True)], dtype=POINT_DTYPE)
        self.model_mock.return_value.fiducials = points
        self.model_mock.return_value.measurement_points = []

        # Command to edit fiducial points
        args = (new_points, PointType.Fiducial)
        cmd = EditPoints(*args, self.presenter)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, new_points)
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, points)

        self.model_mock.reset_mock()
        self.model_mock.return_value.fiducials = []
        self.model_mock.return_value.measurement_points = points

        # Command to edit measurement points
        args = (new_points, PointType.Measurement)
        cmd_1 = EditPoints(*args, self.presenter)
        cmd_1.redo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, new_points)
        cmd_1.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, points)
        cmd_1.redo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, new_points)
        self.assertFalse(cmd.mergeWith(cmd_1))

        newer_points = np.rec.array([([2.0, 2.0, 2.0], True)], dtype=POINT_DTYPE)
        args = (newer_points, PointType.Measurement)
        cmd_2 = EditPoints(*args, self.presenter)
        self.assertTrue(cmd_1.mergeWith(cmd_2))
        cmd_1.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, points)
        cmd_1.redo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, newer_points)
        self.assertTrue(cmd_1.mergeWith(EditPoints(points, PointType.Measurement, self.presenter)))
        self.assertTrue(cmd_1.isObsolete())
        self.assertTrue(cmd_1.id(), CommandID.EditPoints)

    def testMovePointsCommand(self):
        points = np.rec.array([([0.0, 0.0, 0.0], False), ([2.0, 0.0, 1.0], True), ([0.0, 1.0, 1.0], True)],
                              dtype=POINT_DTYPE)
        copied_points = points.copy()
        self.model_mock.return_value.fiducials = points
        self.model_mock.return_value.measurement_points = []
        self.model_mock.return_value.measurement_vectors = []

        # Command to move fiducial points
        cmd = MovePoints(2, 0, PointType.Fiducial, self.presenter)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, copied_points[[2, 1, 0]])
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, copied_points)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, copied_points[[2, 1, 0]])

        cmd_1 = MovePoints(0, 1, PointType.Fiducial, self.presenter)
        cmd_1.redo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, copied_points[[1, 2, 0]])
        self.assertTrue(cmd.mergeWith(cmd_1))
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, copied_points)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.fiducials, copied_points[[1, 2, 0]])

        self.assertTrue(cmd.mergeWith(MovePoints(0, 2, PointType.Fiducial, self.presenter)))
        self.assertTrue(cmd.mergeWith(MovePoints(1, 2, PointType.Fiducial, self.presenter)))
        self.assertTrue(cmd.isObsolete())
        self.assertTrue(cmd.id(), CommandID.EditPoints)

        self.model_mock.reset_mock()
        points = np.rec.array([([0.0, 0.0, 0.0], False), ([2.0, 0.0, 1.0], True), ([0.0, 1.0, 1.0], True)],
                              dtype=POINT_DTYPE)
        vectors = np.array([[[0.0], [0.0], [0.0]], [[0.0], [1.0], [0.0]], [[0.0], [0.0], [1.0]]])
        copied_vectors = vectors.copy()
        self.model_mock.return_value.fiducials = []
        self.model_mock.return_value.measurement_points = points
        self.model_mock.return_value.measurement_vectors = vectors

        # Command to move measurement points
        cmd_2 = MovePoints(0, 1, PointType.Measurement, self.presenter)
        cmd_2.redo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, copied_points[[1, 0, 2]])
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors[[1, 0, 2]])
        cmd_2.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_points, copied_points)
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors)
        self.assertFalse(cmd_1.mergeWith(cmd_2))

    def testInsertAlignmentMatrixCommand(self):
        self.model_mock.return_value.alignment = None

        matrix = np.identity(4)
        cmd = InsertAlignmentMatrix(matrix, self.presenter)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.alignment, matrix)
        cmd.undo()
        self.assertIsNone(self.model_mock.return_value.alignment)

        matrix = np.ones((4, 4))
        self.assertTrue(cmd.mergeWith(InsertAlignmentMatrix(matrix, self.presenter)))
        self.assertFalse(cmd.isObsolete())
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.alignment, matrix)
        cmd.undo()
        self.assertIsNone(self.model_mock.return_value.alignment)
        self.assertTrue(cmd.mergeWith(InsertAlignmentMatrix(None, self.presenter)))
        self.assertTrue(cmd.isObsolete())
        self.assertTrue(cmd.id(), CommandID.AlignSample)

    def testInsertAlignmentMatrixCommand(self):
        self.model_mock.return_value.alignment = None

        matrix = np.identity(4)
        cmd = InsertAlignmentMatrix(matrix, self.presenter)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.alignment, matrix)
        cmd.undo()
        self.assertIsNone(self.model_mock.return_value.alignment)

        matrix = np.ones((4, 4))
        self.assertTrue(cmd.mergeWith(InsertAlignmentMatrix(matrix, self.presenter)))
        self.assertFalse(cmd.isObsolete())
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.alignment, matrix)
        cmd.undo()
        self.assertIsNone(self.model_mock.return_value.alignment)
        self.assertTrue(cmd.mergeWith(InsertAlignmentMatrix(None, self.presenter)))
        self.assertTrue(cmd.isObsolete())
        self.assertTrue(cmd.id(), CommandID.AlignSample)

    def testRemoveVectorsCommand(self):
        vectors = np.array([[[1., 3.], [1., 3.], [1., 3.], [2., 4.], [2., 4.], [2., 4.]],
                            [[1., 3.], [1., 3.], [1., 3.], [2., 4.], [2., 4.], [2., 4.]]])
        copied_vectors = vectors.copy()
        self.model_mock.return_value.measurement_vectors = vectors

        cmd = RemoveVectors([0], 0, 0, self.presenter)
        cmd.redo()
        temp = vectors.copy()
        temp[0, 0:3, 0] = 0
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, temp)
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors)

        cmd = RemoveVectors([0, 1], 1, 1, self.presenter)
        cmd.redo()
        temp = vectors.copy()
        temp[:, 3:6, 1] = 0
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, temp)
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors)

    def testRemoveVectorAlignmentCommand(self):
        vectors = np.array([[[1., 3.], [1., 3.], [1., 3.], [1., 3.], [1., 3.], [1., 3.]],
                            [[1., 3.], [1., 3.], [1., 3.], [1., 3.], [1., 3.], [1., 3.]]])
        copied_vectors = vectors.copy()
        self.model_mock.return_value.measurement_vectors = vectors

        cmd = RemoveVectorAlignment(0, self.presenter)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors[:, :, 1:])
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors)

        cmd = RemoveVectorAlignment(1, self.presenter)
        cmd.redo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors[:, :, :1])
        cmd.undo()
        np.testing.assert_equal(self.model_mock.return_value.measurement_vectors, copied_vectors)

    @mock.patch('sscanss.ui.commands.insert.logging', autospec=True)
    @mock.patch('sscanss.ui.commands.insert.Worker', autospec=True)
    def testInsertVectorsFromFileCommand(self, worker_mock, _):
        worker_mock.return_value.job_succeeded = TestSignal()
        worker_mock.return_value.job_failed = TestSignal()
        worker_mock.return_value.finished = TestSignal()
        filename = 'random'
        self.view_mock.progress_dialog = mock.create_autospec(ProgressDialog)
        self.view_mock.docks = mock.create_autospec(DockManager)
        self.view_mock.undo_stack = mock.create_autospec(QUndoStack)

        vectors = np.array([[1, 2], [3, 4]])
        self.model_mock.return_value.measurement_vectors = vectors
        cmd = InsertVectorsFromFile(filename, self.presenter)
        cmd.redo()
        self.view_mock.progress_dialog.show.assert_called_once()
        worker_mock.return_value.job_succeeded.emit(LoadVector.Smaller_than_points)
        self.assertEqual(self.view_mock.showMessage.call_count, 1)
        self.assertEqual(self.view_mock.docks.showVectorManager.call_count, 1)
        worker_mock.return_value.job_succeeded.emit(LoadVector.Larger_than_points)
        self.assertEqual(self.view_mock.showMessage.call_count, 2)
        self.assertEqual(self.view_mock.docks.showVectorManager.call_count, 2)
        worker_mock.return_value.job_succeeded.emit(LoadVector.Exact)
        self.assertEqual(self.view_mock.showMessage.call_count, 2)
        self.assertEqual(self.view_mock.docks.showVectorManager.call_count, 3)
        worker_mock.return_value.finished.emit()
        self.view_mock.progress_dialog.close.assert_called_once()
        worker_mock.return_value.job_failed.emit(Exception())
        self.assertTrue(cmd.isObsolete())
        self.model_mock.return_value.measurement_vectors = np.identity(2)
        cmd.undo()
        np.testing.assert_array_equal(self.model_mock.return_value.measurement_vectors, vectors)
        cmd.redo()
        worker_mock.return_value.start.assert_called_once()
        np.testing.assert_array_equal(self.model_mock.return_value.measurement_vectors, np.identity(2))

    @mock.patch('sscanss.ui.commands.insert.logging', autospec=True)
    @mock.patch('sscanss.ui.commands.insert.Worker', autospec=True)
    def testInsertVectorsCommand(self, worker_mock, _):
        worker_mock.return_value.job_succeeded = TestSignal()
        worker_mock.return_value.job_failed = TestSignal()
        worker_mock.return_value.finished = TestSignal()
        self.view_mock.progress_dialog = mock.create_autospec(ProgressDialog)
        self.view_mock.docks = mock.create_autospec(DockManager)
        self.view_mock.undo_stack = mock.create_autospec(QUndoStack)

        self.model_mock.return_value.measurement_points = np.array([[1, 2, 3]])
        self.model_mock.return_value.measurement_vectors = np.identity(3)
        cmd = InsertVectors(self.presenter, -1, StrainComponents.parallel_to_x, 1, 1)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        self.view_mock.progress_dialog.show.assert_called_once()
        worker_mock.return_value.job_succeeded.emit()
        self.view_mock.docks.showVectorManager.assert_called_once()
        worker_mock.return_value.finished.emit()
        self.view_mock.progress_dialog.close.assert_called_once()
        worker_mock.return_value.job_failed.emit(Exception())
        self.assertTrue(cmd.isObsolete())

        expected = np.array([[1., 0., 0.], [1., 0., 0.], [1., 0, 0.]])
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        self.model_mock.return_value.measurement_vectors = actual
        np.testing.assert_array_equal(actual, expected)
        cmd.undo()
        np.testing.assert_array_equal(self.model_mock.return_value.measurement_vectors, np.identity(3))
        cmd.redo()
        np.testing.assert_array_equal(self.model_mock.return_value.measurement_vectors, expected)

        cmd = InsertVectors(self.presenter, 0, StrainComponents.parallel_to_y, 1, 1)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        np.testing.assert_array_equal(actual, [[0., 1., 0.]])

        cmd = InsertVectors(self.presenter, 2, StrainComponents.parallel_to_z, 1, 1)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        np.testing.assert_array_equal(actual, [[0., 0., 1.]])

        cmd = InsertVectors(self.presenter, 0, StrainComponents.custom, 1, 1, key_in=[1., 1., 0.], reverse=True)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        np.testing.assert_array_almost_equal(actual, [[-0.707107, -0.707107, 0.]], decimal=5)

        vertices = np.array([[-1., 1., 0.], [1., 1., 0.], [1., -1., 0.]])
        normals = np.array([[0., 0., 1.], [0., 0., 1.], [0., 0., 1.]])
        indices = np.array([2, 1, 0])

        points = np.rec.array([([0.0, 0.0, 0.0], False), ([0.1, 0.5, 0.0], True)], dtype=POINT_DTYPE)
        self.model_mock.return_value.measurement_points = points
        self.model_mock.return_value.sample = {'1': Mesh(vertices, indices, normals)}
        cmd = InsertVectors(self.presenter, 0, StrainComponents.normal_to_surface, 1, 1)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        np.testing.assert_array_almost_equal(actual, [[0., 0., 1.]], decimal=5)

        cmd = InsertVectors(self.presenter, -1, StrainComponents.orthogonal_to_normal_no_x, 1, 1)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        np.testing.assert_array_almost_equal(actual, [[0., 1., 0.], [0., 1., 0.]], decimal=5)

        cmd = InsertVectors(self.presenter, -1, StrainComponents.orthogonal_to_normal_no_y, 1, 1)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        np.testing.assert_array_almost_equal(actual, [[-1., 0., 0.], [-1., 0., 0.]], decimal=5)

        cmd = InsertVectors(self.presenter, 0, StrainComponents.orthogonal_to_normal_no_z, 1, 1)
        worker_mock.return_value.start = cmd.createVectors
        cmd.redo()
        actual = self.model_mock.return_value.addVectorsToProject.call_args[0][0]
        np.testing.assert_array_almost_equal(actual, [[0., 0., 0.]], decimal=5)


if __name__ == '__main__':
    unittest.main()
