import qt
import re
import slicer
from DICOMLib import DICOMUtils
import numpy as np
import json

from .importerBase import ImporterDialogBase


class ImporterDialog(ImporterDialogBase):
    def __init__(self):
        ImporterDialogBase.__init__(self)
        self.importerName = 'ROSA'
        self.fileSelectTitle = 'Select ROSA file'
        self.fileSelectExt = 'ros'

class Importer():
    def __init__(self):
        self.fileExtension = '.ros'
    
    
def setParameterNodeFromDevice(parameterNode, filePath=None, importInFrameSpace=False, DICOMdir=None):

    if filePath is None:
        filePath, computeReferenceToFrame, importACPC, importDICOM, DICOMdir = getOptionsFromDialog(importInFrameSpace)
    else:
        computeReferenceToFrame = True
        importACPC = True
        importDICOM = True if DICOMdir is not None else False

    if filePath is None:
        return

    manager = ROSAManager(filePath)
    rosa_trajectories = manager.getTrajectoriesList()

    import StereotacticPlan2
    logic = StereotacticPlan2.StereotacticPlan2Logic()

    wasModified = parameterNode.StartModify()

    if importACPC:
        parameterNode.SetParameter("Reference AC", manager.getCoordinates('AC') + ';RAS')
        parameterNode.SetParameter("Reference PC", manager.getCoordinates('PC') + ';RAS')
        parameterNode.SetParameter("Reference MS", manager.getCoordinates('IH') + ';RAS')
        parameterNode.SetParameter("ReferenceToFrameMode", "ACPC Align")

    if computeReferenceToFrame:
        referenceToFrameNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "Reference To Frame")
        logic.runACPCAlignment(referenceToFrameNode, 
                                np.fromstring(manager.getCoordinates('AC'), dtype=float, sep=','),
                                np.fromstring(manager.getCoordinates('PC'), dtype=float, sep=','),
                                np.fromstring(manager.getCoordinates('IH'), dtype=float, sep=','))
        parameterNode.SetNodeReferenceID("ReferenceToFrameTransform", referenceToFrameNode.GetID())

    trajectories = json.loads(parameterNode.GetParameter("Trajectories"))
    for rosa_trajectory in rosa_trajectories:
        new_trajectory = {}
        trajectoryTransform = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "Trajectory " + rosa_trajectory['name'])
        new_trajectory['OutputTransformID'] = trajectoryTransform.GetID()
        new_trajectory['Mode'] = 'Target Entry Roll'
        new_trajectory['Entry'] = rosa_trajectory['entry'] + ';RAS;0'
        new_trajectory['Target'] = rosa_trajectory['target'] + ';RAS;0'
        new_trajectory['Mounting'] = 'lateral-left'
        new_trajectory['Arc'] = 90
        new_trajectory['Ring'] = 90
        new_trajectory['Roll'] = 0
        trajectories.append(new_trajectory)

    parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
    parameterNode.SetParameter("TrajectoryIndex", str(len(trajectories)-1))

    if importDICOM:
        first_series_uid = manager.getFirstSeriesUID()
        with DICOMUtils.TemporaryDICOMDatabase() as database:
            DICOMUtils.importDicom(DICOMdir, database)
            rosa_reference_node_ID = DICOMUtils.loadSeriesByUID([first_series_uid])[0]
        slicer.modules.volumes.logic().CenterVolume(slicer.util.getNode(rosa_reference_node_ID))
        slicer.util.resetSliceViews()
        parameterNode.SetNodeReferenceID("ReferenceVolume", rosa_reference_node_ID)

    parameterNode.EndModify(wasModified)


def getOptionsFromDialog(importInFrameSpace):
    dialog = qt.QDialog()
    dialog.setWindowTitle('ROSA Import Options')

    planningPDFButton = qt.QPushButton('Click to select')
    planningPDFButton.clicked.connect(lambda: planningPDFButton.setText(qt.QFileDialog.getOpenFileName(qt.QWidget(), 'Select ROSA file', '', '*.ros')))

    computeReferenceToFrameCheckBox = qt.QCheckBox()
    computeReferenceToFrameCheckBox.setEnabled(False)

    importACPCCheckBox = qt.QCheckBox()
    importACPCCheckBox.connect("toggled(bool)", lambda b: computeReferenceToFrameCheckBox.setEnabled(b))

    DICOMDirButton = qt.QPushButton('Click to select')
    DICOMDirButton.clicked.connect(lambda: DICOMDirButton.setText(qt.QFileDialog.getExistingDirectory(qt.QWidget(), 'Select DICOM directory', '')))
    DICOMDirButton.setEnabled(False)

    importDICOMCheckBox = qt.QCheckBox()
    importDICOMCheckBox.connect("toggled(bool)", lambda b: DICOMDirButton.setEnabled(b))

    buttonBox = qt.QDialogButtonBox(qt.QDialogButtonBox.Ok | qt.QDialogButtonBox.Cancel, qt.Qt.Horizontal, dialog)
    buttonBox.accepted.connect(lambda: dialog.accept())
    buttonBox.rejected.connect(lambda: dialog.reject())

    form = qt.QFormLayout(dialog)
    form.addRow('ROSA file: ', planningPDFButton)
    if not importInFrameSpace:
        form.addRow('Import ACPC coords: ', importACPCCheckBox)
        form.addRow('Compute reference to frame transform: ', computeReferenceToFrameCheckBox)
        form.addRow('Import reference image: ', importDICOMCheckBox)
        form.addRow('DICOM directory: ', DICOMDirButton)
    form.addRow(buttonBox)

    if dialog.exec() == qt.QDialog.Accepted:
        return  planningPDFButton.text,\
              computeReferenceToFrameCheckBox.checked,\
              importACPCCheckBox.checked,\
              importDICOMCheckBox.checked,\
              DICOMDirButton.text
    else:
        return None, None, None, None, None
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
            trajectory[pos] = ','.join([str(x) for x in trajectory[pos]])
        return trajectories

    def getCoordinates(self, queryPoint):
        pattern = r"(?<=\[ACPC\]).*" + queryPoint + r" \d -?\d+\.\d+ -?\d+\.\d+ -?\d+\.\d+"
        m = re.search(pattern, self.ros_txt, re.DOTALL)
        if not m:
          raise RuntimeError('Unable to find: %s' % queryPoint)
        coords_str = m.group().split(' ')[-3:]
        coords_lps = np.array(list(map(float, coords_str)))
        coords_ras = coords_lps * np.array([-1, -1, 1])
        return ','.join([str(x) for x in coords_ras])
