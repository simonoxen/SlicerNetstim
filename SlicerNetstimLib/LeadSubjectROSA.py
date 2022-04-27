import sys, os
import glob
import re
import slicer
from DICOMLib import DICOMUtils
import vtk
import numpy as np

class ROSAManager:
    def __init__(self, ros_file_path):
        with open(ros_file_path, 'r') as f:
            self.ros_txt = f.read()
    
    def getFirstSeriesUID(self):
        return re.search(r"(?<=\[SERIE_UID\]\n).*", self.ros_txt).group()

    def getTrajectoriesList(self):
        pattern = r"(?P<name>\w+) (?P<type>\d) (?P<color>\d+) (?P<entry_point_defined>\d) (?P<entry>-?\d+\.\d+ -?\d+\.\d+ -?\d+\.\d+) (?P<target_point_defined>\d) (?P<target>-?\d+\.\d+ -?\d+\.\d+ -?\d+\.\d+) (?P<instrument_length>\d+\.\d+) (?P<instrument_diameter>\d+\.\d+)\n"
        trajectories = [m.groupdict() for m in re.finditer(pattern, self.ros_txt)]
        for trajectory in trajectories:
            for pos in ['entry', 'target']:
                trajectory[pos] = np.array(list(map(float, trajectory[pos].split(' ')))) # str to array
                trajectory[pos] = trajectory[pos] * np.array([-1, -1, 1]) # LPS to RAS
        return trajectories

    def loadTrajectoriesAsLineNodes(self):
        for trajectory in self.getTrajectoriesList():
            n = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode', trajectory['name'])
            n.AddControlPoint(vtk.vtkVector3d(trajectory['entry']))
            n.AddControlPoint(vtk.vtkVector3d(trajectory['target']))
    
    def loadTrajectoriesAsTransformNodes(self):
        for trajectory in self.getTrajectoriesList():
            superior_of_target = trajectory['target'] + np.array([0, 0, 10])
            target_entry_diff = trajectory['target'] - trajectory['entry']
            a = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsAngleNode')
            p = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode')
            p.SetPlaneType(0)
            for point in [trajectory['entry'], trajectory['target'], superior_of_target]:
                p.AddControlPoint(vtk.vtkVector3d(point))
                a.AddControlPoint(vtk.vtkVector3d(point))
            vtkTransform = vtk.vtkTransform()
            vtkTransform.Translate(trajectory['target'])
            vtkTransform.RotateWXYZ(-90, target_entry_diff[0], target_entry_diff[1], target_entry_diff[2])  
            vtkTransform.RotateWXYZ(a.GetAngleDegrees(), p.GetNormal()[0], p.GetNormal()[1], p.GetNormal()[2])  
            n = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', trajectory['name'])
            n.SetAndObserveTransformToParent(vtkTransform)
            slicer.mrmlScene.RemoveNode(p)
            slicer.mrmlScene.RemoveNode(a)

    @staticmethod
    def getFirstRosFilePath(root_path):
        possible_paths = glob.glob(os.path.join(root_path,'**','*.ros'), recursive=True)
        for possible_path in possible_paths:
            # TODO: do some check up
            return possible_path
        raise RuntimeError('Could not find .ros file inside ' + root_path)


if __name__ == '__main__':
    subject_path = sys.argv[1]    
    ros_file_path = ROSAManager.getFirstRosFilePath(subject_path)
    print("Found .ros file for '%s' in '%s'" % (subject_path, os.path.relpath(ros_file_path,subject_path)))

    manager = ROSAManager(ros_file_path)
    first_series_uid = manager.getFirstSeriesUID()
    with DICOMUtils.TemporaryDICOMDatabase() as database:
        DICOMUtils.importDicom(os.path.join(subject_path, 'DICOM'), database)
        rosa_reference_node_ID = DICOMUtils.loadSeriesByUID([first_series_uid])[0]
    slicer.modules.volumes.logic().CenterVolume(slicer.util.getNode(rosa_reference_node_ID))
    slicer.util.resetSliceViews()
    print('Loaded volume with UID: %s' % first_series_uid)

    manager.loadTrajectoriesAsLineNodes()
    manager.loadTrajectoriesAsTransformNodes()
    # slicer.util.exit()