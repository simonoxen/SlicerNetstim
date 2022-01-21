import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import numpy as np

#
# AdvancedVolumeDisplay
#

class AdvancedVolumeDisplay(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "AdvancedVolumeDisplay"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Netstim"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Simon Oxenford (Charite Berlin)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#AdvancedVolumeDisplay">module documentation</a>.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

    # Additional initialization step after application startup is complete
    # slicer.app.connect("startupCompleted()", registerSampleData)s

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

  # AdvancedVolumeDisplay1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='AdvancedVolumeDisplay',
    sampleName='AdvancedVolumeDisplay1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'AdvancedVolumeDisplay1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='AdvancedVolumeDisplay1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='AdvancedVolumeDisplay1'
  )

  # AdvancedVolumeDisplay2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='AdvancedVolumeDisplay',
    sampleName='AdvancedVolumeDisplay2',
    thumbnailFileName=os.path.join(iconsPath, 'AdvancedVolumeDisplay2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='AdvancedVolumeDisplay2.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='AdvancedVolumeDisplay2'
  )

#
# AdvancedVolumeDisplayWidget
#

class AdvancedVolumeDisplayWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
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
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/AdvancedVolumeDisplay.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = AdvancedVolumeDisplayLogic()

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    # self.ui.range1Slider.minimumValueChanged.connect(self.updateParameterNodeFromGUI)
    # self.ui.range1Slider.maximumValueChanged.connect(self.updateParameterNodeFromGUI)
    # self.ui.range2Slider.minimumValueChanged.connect(self.updateParameterNodeFromGUI)
    # self.ui.range2Slider.maximumValueChanged.connect(self.updateParameterNodeFromGUI)    

    self.ui.inputSelector.currentNodeChanged.connect(self.runSetUpLogic)
    self.ui.outputSelector.currentNodeChanged.connect(self.runSetUpLogic)

    # self.ui.range1Slider.rangeChanged.connect(self.runLogic)
    # self.ui.range2Slider.rangeChanged.connect(self.runLogic)

    self.ui.range1Slider.minimumValueChanged.connect(self.runLogic)
    self.ui.range1Slider.maximumValueChanged.connect(self.runLogic)
    self.ui.range2Slider.minimumValueChanged.connect(self.runLogic)
    self.ui.range2Slider.maximumValueChanged.connect(self.runLogic)   


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
    self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))

    self.ui.settingsCollapsibleButton.enabled = self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume")

    if self._parameterNode.GetNodeReference("InputVolume"):
      inputVolumeArray = slicer.util.array(self._parameterNode.GetNodeReferenceID("InputVolume"))
      self.ui.range1Slider.singleStep = (inputVolumeArray.max()-inputVolumeArray.min())/100
      self.ui.range2Slider.singleStep = (inputVolumeArray.max()-inputVolumeArray.min())/100

      self.ui.range1Slider.minimum = inputVolumeArray.min()
      self.ui.range1Slider.maximum = inputVolumeArray.max()
      self.ui.range2Slider.minimum = inputVolumeArray.min()
      self.ui.range2Slider.maximum = inputVolumeArray.max()

      self.ui.range1Slider.minimumValue = inputVolumeArray.min()
      self.ui.range1Slider.maximumValue = inputVolumeArray.max()/2
      self.ui.range2Slider.minimumValue = inputVolumeArray.max()/2
      self.ui.range2Slider.maximumValue = inputVolumeArray.max()

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

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  def runSetUpLogic(self):
    if self.ui.inputSelector.currentNodeID and self.ui.outputSelector.currentNodeID:
      self.logic.setUp(self._parameterNode.GetNodeReference("InputVolume"), self._parameterNode.GetNodeReference("OutputVolume"))

  def runLogic(self):
    if self.ui.inputSelector.currentNodeID and self.ui.outputSelector.currentNodeID:
      range1 = np.array((self.ui.range1Slider.minimumValue, self.ui.range1Slider.maximumValue))
      range2 = np.array((self.ui.range2Slider.minimumValue, self.ui.range2Slider.maximumValue))
      self.logic.run(self._parameterNode.GetNodeReference("InputVolume"), self._parameterNode.GetNodeReference("OutputVolume"), range1, range2)


#
# AdvancedVolumeDisplayLogic
#

class AdvancedVolumeDisplayLogic(ScriptedLoadableModuleLogic):
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

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    pass
    # if not parameterNode.GetParameter("Threshold"):
    #   parameterNode.SetParameter("Threshold", "100.0")
    # if not parameterNode.GetParameter("Invert"):
    #   parameterNode.SetParameter("Invert", "false")

  def setUp(self, inputVolume, outputVolume):

    fillVoxelValue = 0

    imageData = vtk.vtkImageData()
    imageData.SetDimensions(inputVolume.GetImageData().GetDimensions())
    imageData.AllocateScalars(inputVolume.GetImageData().GetScalarType(), 3)
    imageData.AllocateScalars(vtk.VTK_FLOAT, 3)
    # imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

    m = vtk.vtkMatrix4x4()
    inputVolume.GetIJKToRASDirectionMatrix(m)

    outputVolume.SetOrigin(inputVolume.GetOrigin())
    outputVolume.SetSpacing(inputVolume.GetSpacing())
    outputVolume.SetAndObserveImageData(imageData)
    outputVolume.SetIJKToRASDirectionMatrix(m)
    outputVolume.CreateDefaultDisplayNodes()



  def run(self, inputVolume, outputVolume, range1, range2):

    backupArray = slicer.util.array(inputVolume.GetID())

    outputArray = slicer.util.array(outputVolume.GetID())
    outputArray[:,:,:,0] = backupArray
    outputArray[:,:,:,1] = backupArray
    outputArray[:,:,:,2] = backupArray

    range1Index = (backupArray>range1[0]) & (backupArray<range1[1])
    range2Index = (backupArray>range2[0]) & (backupArray<range2[1])

    idx = np.logical_and(np.logical_not(range1Index), np.logical_not(range2Index))
    if idx.any():
      outputArray[np.stack((idx,idx,idx),3)] = -1

    # only range 1
    idx = np.logical_and(range1Index, np.logical_not(range2Index))
    if idx.any():
      values = backupArray[idx]
      values = 1 - (values - values.min()) / (float(values.max()) - float(values.min()))
      outputArray[:,:,:,0][idx] = values*1.0
      outputArray[:,:,:,1][idx] = values*0.5
      outputArray[:,:,:,2][idx] = values*0.0

    # intersection
    idx = np.logical_and(range1Index, range2Index)
    if idx.any():
      values = backupArray[idx]
      values = (values - values.min()) / (float(values.max()) - float(values.min()))
      outputArray[:,:,:,0][idx] = 1 - (1-values*1.0) * (1-values*0.0)
      outputArray[:,:,:,1][idx] = 1 - (1-values*0.5) * (1-values*0.5)
      outputArray[:,:,:,2][idx] = 1 - (1-values*0.0) * (1-values*1.0)

    # only range 2
    idx = np.logical_and(np.logical_not(range1Index), range2Index)
    if idx.any():
      values = backupArray[idx]
      values = (values - values.min()) / (float(values.max()) - float(values.min()))
      outputArray[:,:,:,0][idx] = values*0.0
      outputArray[:,:,:,1][idx] = values*0.5
      outputArray[:,:,:,2][idx] = values*1.0

    outputVolume.Modified()
    outputVolume.GetDisplayNode().AutoWindowLevelOff()
    outputVolume.GetDisplayNode().SetWindowLevelLocked(0)
    outputVolume.GetDisplayNode().SetWindowLevelMinMax(0,1)
    outputVolume.GetDisplayNode().SetApplyThreshold(1)
    outputVolume.GetDisplayNode().SetAutoThreshold(slicer.qMRMLVolumeThresholdWidget.Auto)
    outputVolume.GetDisplayNode().SetThreshold(0,1)




#
# AdvancedVolumeDisplayTest
#

class AdvancedVolumeDisplayTest(ScriptedLoadableModuleTest):
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
    self.test_AdvancedVolumeDisplay1()

  def test_AdvancedVolumeDisplay1(self):
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

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('AdvancedVolumeDisplay1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = AdvancedVolumeDisplayLogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
