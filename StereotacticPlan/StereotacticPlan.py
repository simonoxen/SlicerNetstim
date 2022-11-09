import os
import unittest
import logging
import vtk, qt, ctk, slicer
import glob
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import numpy as np
import StereotacticPlanLib.util

#
# StereotacticPlan
#

class StereotacticPlan(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Stereotactic Plan"
    self.parent.categories = ["Netstim"]
    self.parent.dependencies = []
    self.parent.contributors = ["Simon Oxenford (Charite Berlin.)"] 
    self.parent.helpText = """
This module creates a transform node representing the planned trajectory from stereotactic frame settings.
"""
    self.parent.acknowledgementText = ""


#
# Register sample data sets in Sample Data module
#

def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # StereotacticPlan1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='StereotacticPlan',
    sampleName='StereotacticPlan1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'StereotacticPlan1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='StereotacticPlan1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='StereotacticPlan1'
  )

  # StereotacticPlan2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='StereotacticPlan',
    sampleName='StereotacticPlan2',
    thumbnailFileName=os.path.join(iconsPath, 'StereotacticPlan2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='StereotacticPlan2.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='StereotacticPlan2'
  )

#
# StereotacticPlanWidget
#

class StereotacticPlanWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/StereotacticPlan.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    importFromOptions = glob.glob(os.path.join(os.path.dirname(__file__), 'StereotacticPlanLib', 'ImportFrom', '*.py'))
    importFromOptions = [os.path.basename(opt).replace('.py','') for opt in importFromOptions]
    importFromOptions.remove('__init__')

    self.ui.importFromComboBox.clear()
    self.ui.importFromComboBox.addItems(['Import From...'] + importFromOptions)


    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = StereotacticPlanLogic()

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # Preview line CHeckbox
    self.ui.previewLineCheckBox.connect('toggled(bool)', self.onPreviewLineToggled)
    self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updatePreviewLineTransform)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.referenceACPCMSComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.frameACPCMSComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.referenceToFrameTransformComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.arcAngleSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.ringAngleSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.rollAngleSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.mountingComboBox.currentIndexChanged.connect(self.updateParameterNodeFromGUI)
    self.ui.autoUpdateCheckBox.connect('toggled(bool)', self.updateParameterNodeFromGUI)
    self.ui.targetMountingRingArcRadioButton.clicked.connect(self.updateParameterNodeFromGUI)
    self.ui.targetEntryRollRadioButton.clicked.connect(self.updateParameterNodeFromGUI)
    self.ui.applyXYZToRASCheckBox.clicked.connect(self.updateParameterNodeFromGUI)

    # Coordinate modification
    self.ui.frameTargetCoordinates.coordinatesChanged.connect(self.onFrameCoordinatesModified)
    self.ui.frameEntryCoordinates.coordinatesChanged.connect(self.onFrameCoordinatesModified)
    self.ui.referenceTargetCoordinates.coordinatesChanged.connect(self.onReferenceCoordinatesModified)
    self.ui.referenceEntryCoordinates.coordinatesChanged.connect(self.onReferenceCoordinatesModified)
    self.ui.frameTargetCoordinatesSystemComboBox.connect('currentTextChanged(QString)', self.frameTargetCoordinatesSytemChanged)
    self.ui.frameEntryCoordinatesSystemComboBox.connect('currentTextChanged(QString)', self.frameEntryCoordinatesSytemChanged)

    # Buttons
    self.ui.applyXYZToRASCheckBox.connect('toggled(bool)', self.applyXYZToRASToggled)
    self.ui.calculateReferenceToFrameTransformPushButton.connect('clicked(bool)', self.onCalculateReferenceToFrameTransform)
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.importFromComboBox.connect('currentTextChanged(QString)', self.importFromChanged)
    self.ui.setDefaultResliceDriverPushButton.connect('clicked(bool)', self.onSetDefaultResliceDriver)

    self.ui.targetEntryRollRadioButton.toggle()
    self.ui.targetMountingRingArcRadioButton.toggle()

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Remove Preview node
    self.ui.previewLineCheckBox.setChecked(False)
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Update node selectors and sliders
    self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputTransform"))
    self.ui.referenceACPCMSComboBox.setCurrentNode(self._parameterNode.GetNodeReference("ReferenceACPCMSMarkups"))
    self.ui.frameACPCMSComboBox.setCurrentNode(self._parameterNode.GetNodeReference("FrameACPCMSMarkups"))
    self.ui.referenceToFrameTransformComboBox.setCurrentNode(self._parameterNode.GetNodeReference("ReferenceToFrameTransform"))
    self.ui.applyXYZToRASCheckBox.checked = int(self._parameterNode.GetParameter("ApplyXYZToRAS"))
    self.ui.arcAngleSliderWidget.value = float(self._parameterNode.GetParameter("ArcAngle"))
    self.ui.ringAngleSliderWidget.value = float(self._parameterNode.GetParameter("RingAngle"))
    self.ui.rollAngleSliderWidget.value = float(self._parameterNode.GetParameter("RollAngle"))
    self.ui.mountingComboBox.setCurrentText(self._parameterNode.GetParameter("Mounting"))
    self.ui.autoUpdateCheckBox.setChecked(int(self._parameterNode.GetParameter("AutoUpdate")))

    self.ui.frameTargetCoordinates.coordinates = self._parameterNode.GetParameter("FrameTargetCoordinates")
    self.ui.frameEntryCoordinates.coordinates = self._parameterNode.GetParameter("FrameEntryCoordinates")
    self.ui.referenceTargetCoordinates.coordinates = self._parameterNode.GetParameter("ReferenceTargetCoordinates")
    self.ui.referenceEntryCoordinates.coordinates = self._parameterNode.GetParameter("ReferenceEntryCoordinates")

    self.ui.frameTargetCoordinatesSystemComboBox.currentText = self._parameterNode.GetParameter("FrameTargetCoordinatesSystem")
    self.ui.frameEntryCoordinatesSystemComboBox.currentText = self._parameterNode.GetParameter("FrameEntryCoordinatesSystem")

    # Update buttons states and tooltips
    self.ui.applyButton.enabled = bool(self._parameterNode.GetNodeReference("OutputTransform")) and not int(self._parameterNode.GetParameter("AutoUpdate"))
    self.ui.calculateReferenceToFrameTransformPushButton.enabled = bool(self._parameterNode.GetNodeReference("ReferenceACPCMSMarkups")) and bool(self._parameterNode.GetNodeReference("ReferenceToFrameTransform"))
    self.ui.setDefaultResliceDriverPushButton.enabled = bool(self._parameterNode.GetNodeReference("OutputTransform"))

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("OutputTransform", self.ui.outputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("ReferenceACPCMSMarkups", self.ui.referenceACPCMSComboBox.currentNodeID)
    self._parameterNode.SetNodeReferenceID("FrameACPCMSMarkups", self.ui.frameACPCMSComboBox.currentNodeID)
    self._parameterNode.SetNodeReferenceID("ReferenceToFrameTransform", self.ui.referenceToFrameTransformComboBox.currentNodeID)
    self._parameterNode.SetParameter("ApplyXYZToRAS", str(int(self.ui.applyXYZToRASCheckBox.checked)))
    self._parameterNode.SetParameter("ArcAngle", str(self.ui.arcAngleSliderWidget.value))
    self._parameterNode.SetParameter("RingAngle", str(self.ui.ringAngleSliderWidget.value))
    self._parameterNode.SetParameter("RollAngle", str(self.ui.rollAngleSliderWidget.value))
    self._parameterNode.SetParameter("Mounting", self.ui.mountingComboBox.currentText)
    self._parameterNode.SetParameter("AutoUpdate", str(int(self.ui.autoUpdateCheckBox.checked)))

    self._parameterNode.EndModify(wasModified)

    # Run in case of auto update
    if int(self._parameterNode.GetParameter("AutoUpdate")):
      self.onApplyButton()

  def onFrameCoordinatesModified(self):
    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    frameTargetCoordinates = np.array(self.ui.frameTargetCoordinates.coordinates.split(','), dtype=float)
    frameEntryCoordinates = np.array(self.ui.frameEntryCoordinates.coordinates.split(','), dtype=float)

    self._parameterNode.SetParameter("FrameTargetCoordinates", self.ui.frameTargetCoordinates.coordinates)
    self._parameterNode.SetParameter("FrameEntryCoordinates", self.ui.frameEntryCoordinates.coordinates)
  
    referenceToFrameTransform = self._parameterNode.GetNodeReference("ReferenceToFrameTransform")
    if referenceToFrameTransform:

      if self.ui.frameTargetCoordinatesSystemComboBox.currentText == 'XYZ':
        frameTargetCoordinates = self.logic.transformCoordinateFromXYZToRAS(frameTargetCoordinates)
      if self.ui.frameEntryCoordinatesSystemComboBox.currentText == 'XYZ':
        frameEntryCoordinates = self.logic.transformCoordinateFromXYZToRAS(frameEntryCoordinates)
 
      referenceTargetCoordinates = referenceToFrameTransform.GetMatrixTransformFromParent().MultiplyFloatPoint(np.append(frameTargetCoordinates, 1))[:3]
      referenceEntryCoordinates = referenceToFrameTransform.GetMatrixTransformFromParent().MultiplyFloatPoint(np.append(frameEntryCoordinates, 1))[:3]

      self._parameterNode.SetParameter("ReferenceTargetCoordinates", ','.join([str(x) for x in referenceTargetCoordinates]))
      self._parameterNode.SetParameter("ReferenceEntryCoordinates", ','.join([str(x) for x in referenceEntryCoordinates]))

    self._parameterNode.EndModify(wasModified)

    if int(self._parameterNode.GetParameter("AutoUpdate")):
      self.onApplyButton()

  def onReferenceCoordinatesModified(self):
    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    referenceTargetCoordinates = np.array(self.ui.referenceTargetCoordinates.coordinates.split(','), dtype=float)
    referenceEntryCoordinates = np.array(self.ui.referenceEntryCoordinates.coordinates.split(','), dtype=float)

    self._parameterNode.SetParameter("ReferenceTargetCoordinates", self.ui.referenceTargetCoordinates.coordinates)
    self._parameterNode.SetParameter("ReferenceEntryCoordinates", self.ui.referenceEntryCoordinates.coordinates)
 
    referenceToFrameTransform = self._parameterNode.GetNodeReference("ReferenceToFrameTransform")
    if referenceToFrameTransform:

      frameTargetCoordinates = referenceToFrameTransform.GetMatrixTransformToParent().MultiplyFloatPoint(np.append(referenceTargetCoordinates, 1))[:3]
      frameEntryCoordinates = referenceToFrameTransform.GetMatrixTransformToParent().MultiplyFloatPoint(np.append(referenceEntryCoordinates, 1))[:3]

      if self.ui.frameTargetCoordinatesSystemComboBox.currentText == 'XYZ':
        frameTargetCoordinates = self.logic.transformCoordinateFromRASToXYZ(frameTargetCoordinates)
      if self.ui.frameTargetCoordinatesSystemComboBox.currentText == 'XYZ':
        frameEntryCoordinates = self.logic.transformCoordinateFromRASToXYZ(frameEntryCoordinates)

      self._parameterNode.SetParameter("FrameTargetCoordinates", ','.join([str(x) for x in frameTargetCoordinates]))
      self._parameterNode.SetParameter("FrameEntryCoordinates", ','.join([str(x) for x in frameEntryCoordinates]))

    self._parameterNode.EndModify(wasModified)

    if int(self._parameterNode.GetParameter("AutoUpdate")):
      self.onApplyButton()

  def frameTargetCoordinatesSytemChanged(self, system):
    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return
    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch
    frameTargetCoordinates = np.array(self.ui.frameTargetCoordinates.coordinates.split(','), dtype=float)
    if system == 'XYZ':
      frameTargetCoordinates = self.logic.transformCoordinateFromRASToXYZ(frameTargetCoordinates)
    elif system == 'RAS':
      frameTargetCoordinates = self.logic.transformCoordinateFromXYZToRAS(frameTargetCoordinates)
    self._parameterNode.SetParameter("FrameTargetCoordinatesSystem", system)
    self._parameterNode.SetParameter("FrameTargetCoordinates", ','.join([str(x) for x in frameTargetCoordinates]))
    self._parameterNode.EndModify(wasModified)
    self.onFrameCoordinatesModified()

  def frameEntryCoordinatesSytemChanged(self, system):
    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return
    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch
    frameEntryCoordinates = np.array(self.ui.frameEntryCoordinates.coordinates.split(','), dtype=float)
    if system == 'XYZ':
      frameEntryCoordinates = self.logic.transformCoordinateFromRASToXYZ(frameEntryCoordinates)
    elif system == 'RAS':
      frameEntryCoordinates = self.logic.transformCoordinateFromXYZToRAS(frameEntryCoordinates)
    self._parameterNode.SetParameter("FrameEntryCoordinatesSystem", system)
    self._parameterNode.SetParameter("FrameEntryCoordinates", ','.join([str(x) for x in frameEntryCoordinates]))
    self._parameterNode.EndModify(wasModified)
    self.onFrameCoordinatesModified()


  def importFromChanged(self, deviceName):
    if deviceName=='Import From...':
      return
    
    import StereotacticPlanLib.ImportFrom
    importFromModule = StereotacticPlanLib.ImportFrom

    import importlib
    importlib.import_module('.'.join(['StereotacticPlanLib', 'ImportFrom', deviceName]))

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    deviceModule = getattr(importFromModule, deviceName)
    deviceModule.setParameterNodeFromDevice(self._parameterNode)

    self._parameterNode.EndModify(wasModified)

    self.ui.importFromComboBox.currentText = 'Import From...'

  def onSetDefaultResliceDriver(self):
    StereotacticPlanLib.util.setDefaultResliceDriver(self._parameterNode.GetNodeReferenceID("OutputTransform"))
      
  def onPreviewLineToggled(self, state):
    if state:
      # add node and default points
      markupsLineNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode')
      self._parameterNode.SetNodeReferenceID("PreviewLine", markupsLineNode.GetID())
      markupsLineNode.AddControlPointWorld(vtk.vtkVector3d(0,0,0), 'Target')
      markupsLineNode.AddControlPointWorld(vtk.vtkVector3d(0,0,80), '2')
      self.updatePreviewLineTransform(self._parameterNode.GetNodeReference("OutputTransform"))
    elif self._parameterNode.GetNodeReferenceID("PreviewLine"):
      # remove node
      slicer.mrmlScene.RemoveNode(self._parameterNode.GetNodeReference("PreviewLine"))

  def updatePreviewLineTransform(self, node):
    if self._parameterNode.GetNodeReferenceID("PreviewLine"):
      self._parameterNode.GetNodeReference("PreviewLine").SetAndObserveTransformNodeID(node.GetID() if node else None)

  def applyXYZToRASToggled(self, active):
    fiducialNode = self.ui.frameACPCMSComboBox.currentNode()
    if fiducialNode:
      if active:
        npMatrix = self.logic.getFrameXYZToRASTransform()
        vtkMatrix = vtk.vtkMatrix4x4()
        for i in range(4):
          for j in range(4):
            vtkMatrix.SetElement(i,j,npMatrix[i,j])
        frameToRASNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        frameToRASNode.SetMatrixTransformToParent(vtkMatrix)
        fiducialNode.SetAndObserveTransformNodeID(frameToRASNode.GetID())
      else:
        currentTransform = fiducialNode.GetTransformNodeID()
        fiducialNode.SetAndObserveTransformNodeID(None)
        if currentTransform:
          slicer.mrmlScene.RemoveNode(slicer.util.getNode(currentTransform))

  def onCalculateReferenceToFrameTransform(self):
    referenceACPCMSNode = self.ui.referenceACPCMSComboBox.currentNode()
    frameACPCMSNode = self.ui.frameACPCMSComboBox.currentNode()
    if frameACPCMSNode is not None:
      self.logic.runFiducialRegistration(self.ui.referenceToFrameTransformComboBox.currentNode(),
                          referenceACPCMSNode,
                          frameACPCMSNode)
    else:
      self.logic.runACPCAlignment(self.ui.referenceToFrameTransformComboBox.currentNode(),
                          referenceACPCMSNode)

  def onApplyButton(self):
    """
    Run processing when user clicks "Apply" button.
    """
    frameTargetCoordinates = np.array(self.ui.frameTargetCoordinates.coordinates.split(','), dtype=float)
    if self.ui.frameTargetCoordinatesSystemComboBox.currentText == 'XYZ':
      frameTargetCoordinates = self.logic.transformCoordinateFromXYZToRAS(frameTargetCoordinates)
  
    frameEntryCoordinates = np.array(self.ui.frameEntryCoordinates.coordinates.split(','), dtype=float)
    if self.ui.frameEntryCoordinatesSystemComboBox.currentText == 'XYZ':
      frameEntryCoordinates = self.logic.transformCoordinateFromXYZToRAS(frameEntryCoordinates)

    try:

      if self.ui.targetMountingRingArcRadioButton.checked:
        self.logic.computeFromTargetMountingRingArc(self.ui.outputSelector.currentNode(),
                          frameTargetCoordinates,
                          self.ui.mountingComboBox.currentText,
                          self.ui.ringAngleSliderWidget.value,
                          self.ui.arcAngleSliderWidget.value)
      else:
        self.logic.computeFromTargetEntryRoll(self.ui.outputSelector.currentNode(),
                          frameTargetCoordinates,
                          frameEntryCoordinates,
                          self.ui.rollAngleSliderWidget.value)


    except Exception as e:
      slicer.util.errorDisplay("Failed to compute transform: "+str(e))
      import traceback
      traceback.print_exc()


#
# StereotacticPlanLogic
#

class StereotacticPlanLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

    if slicer.util.settingsValue('Developer/DeveloperMode', False, converter=slicer.util.toBool):
      import glob
      import importlib
      import StereotacticPlanLib
      StereotacticPlanLibPath = os.path.join(os.path.dirname(__file__), 'StereotacticPlanLib')
      G = glob.glob(os.path.join(StereotacticPlanLibPath, '**','*.py'))
      for g in G:
        relativePath = os.path.relpath(g, StereotacticPlanLibPath) # relative path
        relativePath = os.path.splitext(relativePath)[0] # get rid of .py
        moduleParts = relativePath.split(os.path.sep) # separate
        importlib.import_module('.'.join(['StereotacticPlanLib']+moduleParts)) # import module
        module = StereotacticPlanLib
        for modulePart in moduleParts: # iterate over parts in order to load subpkgs
          module = getattr(module, modulePart)
        importlib.reload(module) # reload

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("ArcAngle"):
      parameterNode.SetParameter("ArcAngle", "90.0")
    if not parameterNode.GetParameter("RingAngle"):
      parameterNode.SetParameter("RingAngle", "90.0")
    if not parameterNode.GetParameter("RollAngle"):
      parameterNode.SetParameter("RollAngle", "0.0")
    if not parameterNode.GetParameter("FrameTargetCoordinates"):
      parameterNode.SetParameter("FrameTargetCoordinates", "100.0,100.0,100.0")
    if not parameterNode.GetParameter("FrameEntryCoordinates"):
      parameterNode.SetParameter("FrameEntryCoordinates", "100.0,100.0,50.0")
    if not parameterNode.GetParameter("ApplyXYZToRAS"):
      parameterNode.SetParameter("ApplyXYZToRAS", "0")
    if not parameterNode.GetParameter("FrameEntryCoordinatesSystem"):
      parameterNode.SetParameter("FrameEntryCoordinatesSystem", "XYZ")
    if not parameterNode.GetParameter("FrameTargetCoordinatesSystem"):
      parameterNode.SetParameter("FrameTargetCoordinatesSystem", "XYZ")
    if not parameterNode.GetParameter("Mounting"):
      parameterNode.SetParameter("Mounting", "lateral-left")
    if not parameterNode.GetParameter("AutoUpdate"):
      parameterNode.SetParameter("AutoUpdate", "0")

  def runFiducialRegistration(self, outputTransform, sourceFiducials, targetFiducials):
    # use aux node with World coordinates
    auxFidNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
    auxFidNode.GetDisplayNode().SetVisibility(False)
    auxFidNode.AddControlPointWorld(targetFiducials.GetNthControlPointPositionWorld(0))
    auxFidNode.AddControlPointWorld(targetFiducials.GetNthControlPointPositionWorld(1))
    auxFidNode.AddControlPointWorld(targetFiducials.GetNthControlPointPositionWorld(2))

    parameters = {}
    parameters['fixedLandmarks']  = auxFidNode.GetID()
    parameters['movingLandmarks'] = sourceFiducials.GetID()
    parameters['saveTransform']   = outputTransform.GetID()
    parameters['transformType']   = 'Rigid'
    slicer.cli.run(slicer.modules.fiducialregistration, None, parameters, wait_for_completion=True, update_display=False)

    slicer.mrmlScene.RemoveNode(auxFidNode)


  def runACPCAlignment(self, outputTransform, ACPCMSNode):
    auxLineNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode')
    auxLineNode.GetDisplayNode().SetVisibility(False)
    auxLineNode.AddControlPointWorld(ACPCMSNode.GetNthControlPointPositionWorld(0), 'AC')
    auxLineNode.AddControlPointWorld(ACPCMSNode.GetNthControlPointPositionWorld(1), 'PC')

    parameters = {}
    parameters['ACPC']  = auxLineNode.GetID()
    parameters['Midline'] = ACPCMSNode.GetID()
    parameters['centerVolume'] = True 
    parameters['OutputTransform'] = outputTransform.GetID()
    slicer.cli.run(slicer.modules.acpctransform, None, parameters, wait_for_completion=True, update_display=False)

    slicer.mrmlScene.RemoveNode(auxLineNode)


  def computeFromTargetMountingRingArc(self, outputTransform, frameTargetCoordinates, mounting, ringAngle, arcAngle):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    """

    if not outputTransform:
      raise ValueError("output transform is invalid")

    # Get ring and arc directions
    if mounting == 'lateral-right':
      initDirection = [0, 1, 0]
      ringDirection = [1, 0, 0]
      arcDirection =  [0, -np.sin(np.deg2rad(ringAngle)), np.cos(np.deg2rad(ringAngle))]
    elif mounting == 'lateral-left':
      initDirection = [0, -1, 0]
      ringDirection = [-1, 0, 0]
      arcDirection  = [0, np.sin(np.deg2rad(ringAngle)), np.cos(np.deg2rad(ringAngle))]
    elif mounting == 'sagittal-anterior':
      initDirection = [-1, 0, 0]
      ringDirection = [0, 1, 0]
      arcDirection  = [np.sin(np.deg2rad(ringAngle)), 0, np.cos(np.deg2rad(ringAngle))]
    elif mounting == 'sagittal-posterior':
      initDirection = [1, 0, 0]
      ringDirection = [0, -1, 0]
      arcDirection  = [-np.sin(np.deg2rad(ringAngle)), 0, np.cos(np.deg2rad(ringAngle))]

    # Create vtk Transform
    vtkTransform = vtk.vtkTransform()
    vtkTransform.Translate(frameTargetCoordinates)
    vtkTransform.RotateWXYZ(arcAngle, arcDirection[0], arcDirection[1], arcDirection[2])
    vtkTransform.RotateWXYZ(ringAngle, ringDirection[0], ringDirection[1], ringDirection[2])
    vtkTransform.RotateWXYZ(90, initDirection[0], initDirection[1], initDirection[2])

    # Set to node
    outputTransform.SetAndObserveTransformToParent(vtkTransform)

  def computeFromTargetEntryRoll(self, outputTransform, frameTargetCoordinates, frameEntryCoordinates, rollAngle):

    entryTargetDirection = frameEntryCoordinates - frameTargetCoordinates
    vtk.vtkMath().Normalize(entryTargetDirection)
    superiorInferiorDirection = np.array([0,0,1])

    ang_rad = np.arccos(vtk.vtkMath().Dot(entryTargetDirection, superiorInferiorDirection))
    ang_deg = np.rad2deg(ang_rad)

    cross = np.zeros(3)
    vtk.vtkMath().Cross(entryTargetDirection, superiorInferiorDirection, cross)

    if vtk.vtkMath().Dot(cross,superiorInferiorDirection) >= 0:
      ang_deg = -1 * ang_deg
    
    vtkTransform = vtk.vtkTransform()
    vtkTransform.Translate(frameTargetCoordinates)
    vtkTransform.RotateWXYZ(rollAngle, entryTargetDirection[0], entryTargetDirection[1], entryTargetDirection[2])
    vtkTransform.RotateWXYZ(ang_deg, cross[0], cross[1], cross[2])

    outputTransform.SetAndObserveTransformToParent(vtkTransform)

  def transformCoordinateFromXYZToRAS(self, coord):
    return np.dot(self.getFrameXYZToRASTransform(), np.append(coord, 1))[:3]

  def transformCoordinateFromRASToXYZ(self, coord):
    return np.dot(np.linalg.inv(self.getFrameXYZToRASTransform()), np.append(coord, 1))[:3]

  def getFrameXYZToRASTransform(self):
    # Headring coordinates to Slicer world (matching center)
    frameToRAS = np.array([[ -1,  0,  0,  100],
                           [  0,  1,  0, -100],
                           [  0,  0, -1,  100],
                           [  0,  0,  0,    1]])
    return frameToRAS                       

#
# StereotacticPlanTest
#

class StereotacticPlanTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_StereotacticPlan1()

  def test_StereotacticPlan1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # frame fiducials
    frameFidNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','FrameFid')
    frameFidNode.AddFiducialFromArray([100.2, 127.55, 123.66], 'frameAC')
    frameFidNode.AddFiducialFromArray([99.93, 102.57, 123.74], 'framePC')
    frameFidNode.AddFiducialFromArray([96.94, 102.37, 53.81], 'frameMS')
    # reference fiducials
    referenceFidNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','ReferenceFid')
    referenceFidNode.AddFiducialFromArray([-0.47, 5.1, -39.01], 'referenceAC')
    referenceFidNode.AddFiducialFromArray([1.03, -17.39, -49.78], 'referencePC')
    referenceFidNode.AddFiducialFromArray([7.36, -47.16, 13.25], 'referenceMS')

    self.delayDisplay('Test passed')
