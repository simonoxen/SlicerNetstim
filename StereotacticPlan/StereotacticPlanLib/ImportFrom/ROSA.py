import sys, os
import glob
import qt
import re
import slicer
from DICOMLib import DICOMUtils
import vtk
import numpy as np


def setParameterNodeFromDevice(parameterNode):
  filePath = qt.QFileDialog.getOpenFileName(qt.QWidget(), 'Select ROSA file', '', '*.ros')
  if filePath == '':
    return
  # get data
  manager = ROSAManager(filePath)
  trajectories = manager.getTrajectoriesList()
  trajectory = trajectories[0]
  # acpc
  referenceFidNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','ReferenceFid')
  referenceFidNode.AddFiducialFromArray(manager.getCoordinates('AC'), 'anatAC')
  referenceFidNode.AddFiducialFromArray(manager.getCoordinates('PC'), 'anatPC')
  referenceFidNode.AddFiducialFromArray(manager.getCoordinates('IH'), 'anatMS')
  # set values
  wasModified = parameterNode.StartModify()
  parameterNode.SetNodeReferenceID("ReferenceACPCMSMarkups", referenceFidNode.GetID())
  parameterNode.SetParameter("ReferenceTargetCoordinates", ','.join([str(x) for x in trajectory['target']]))
  parameterNode.SetParameter("ReferenceEntryCoordinates", ','.join([str(x) for x in trajectory['entry']]))
  parameterNode.EndModify(wasModified)


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

  def getCoordinates(self, queryPoint):
    pattern = r"(?<=\[ACPC\]).*" + queryPoint + r" \d -?\d+\.\d+ -?\d+\.\d+ -?\d+\.\d+"
    m = re.search(pattern, self.ros_txt, re.DOTALL)
    if not m:
      raise RuntimeError('Unable to find: %s' % queryPoint)
    coords_str = m.group().split(' ')[-3:]
    coords_lps = np.array(list(map(float, coords_str)))
    coords_ras = coords_lps * np.array([-1, -1, 1])
    return coords_ras


  # @staticmethod
  # def getFirstRosFilePath(root_path):
  #   possible_paths = glob.glob(os.path.join(root_path,'**','*.ros'), recursive=True)
  #   for possible_path in possible_paths:
  #     # TODO: do some check up
  #     return possible_path
  #   raise RuntimeError('Could not find .ros file inside ' + root_path)


# if __name__ == '__main__':
#     subject_path = sys.argv[1]    
#     ros_file_path = ROSAManager.getFirstRosFilePath(subject_path)
#     print("Found .ros file for '%s' in '%s'" % (subject_path, os.path.relpath(ros_file_path,subject_path)))

#     manager = ROSAManager(ros_file_path)
#     first_series_uid = manager.getFirstSeriesUID()
#     with DICOMUtils.TemporaryDICOMDatabase() as database:
#         DICOMUtils.importDicom(os.path.join(subject_path, 'DICOM'), database)
#         rosa_reference_node_ID = DICOMUtils.loadSeriesByUID([first_series_uid])[0]
#     slicer.modules.volumes.logic().CenterVolume(slicer.util.getNode(rosa_reference_node_ID))
#     slicer.util.resetSliceViews()
#     print('Loaded volume with UID: %s' % first_series_uid)

#     manager.loadTrajectoriesAsLineNodes()
#     manager.loadTrajectoriesAsTransformNodes()
#     # slicer.util.exit()