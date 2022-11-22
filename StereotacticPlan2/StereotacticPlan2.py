import logging
import os
import glob
import json

import vtk, qt

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import StereotacticPlanLib.util
from StereotacticPlanLib.Widgets.CustomWidgets import myCoordinatesWidget

#
# StereotacticPlan2
#

class StereotacticPlan2(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "StereotacticPlan2"  # TODO: make this more human readable by adding spaces
        self.parent.categories = ["Netstim"]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Simon Oxenford (Charite Berlin)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#StereotacticPlan2">module documentation</a>.
"""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

        # Additional initialization step after application startup is complete
        # slicer.app.connect("startupCompleted()", registerSampleData)


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

    # StereotacticPlan21
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category='StereotacticPlan2',
        sampleName='StereotacticPlan21',
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, 'StereotacticPlan21.png'),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames='StereotacticPlan21.nrrd',
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums='SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
        # This node name will be used when the data set is loaded
        nodeNames='StereotacticPlan21'
    )

    # StereotacticPlan22
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category='StereotacticPlan2',
        sampleName='StereotacticPlan22',
        thumbnailFileName=os.path.join(iconsPath, 'StereotacticPlan22.png'),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        fileNames='StereotacticPlan22.nrrd',
        checksums='SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
        # This node name will be used when the data set is loaded
        nodeNames='StereotacticPlan22'
    )


#
# StereotacticPlan2Widget
#

class StereotacticPlan2Widget(ScriptedLoadableModuleWidget, VTKObservationMixin):
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
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/StereotacticPlan2.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Custom Widgets
        self.updateTrajectoriesComboBox()
        auxMarkupsNode = self.getOrCreateAuxMarkupsNode()
        auxMarkupsNode.RemoveAllControlPoints()
        self.trajectoryCoordinateWidgets = {}
        for name in ['Entry', 'Target']:
            self.trajectoryCoordinateWidgets[name] =  myCoordinatesWidget(auxMarkupsNode, name)
            self.trajectoryCoordinateWidgets[name].coordinatesChanged.connect(self.updateParameterNodeFromGUI)
            self.ui.trajectoriesCollapsibleButton.layout().addRow(name + ':', self.trajectoryCoordinateWidgets[name])
        self.referenceToFrameCoordinateWidgets = {}
        for name in ['Reference MS', 'Reference PC', 'Reference AC']:
            self.referenceToFrameCoordinateWidgets[name] =  myCoordinatesWidget(auxMarkupsNode, name)
            self.referenceToFrameCoordinateWidgets[name].coordinatesChanged.connect(self.updateParameterNodeFromGUI)
            self.ui.referenceToFrameCollapsibleButton.layout().insertRow(1, name + ':', self.referenceToFrameCoordinateWidgets[name])
        for name in ['Frame MS', 'Frame PC', 'Frame AC']:
            self.referenceToFrameCoordinateWidgets[name] =  myCoordinatesWidget(auxMarkupsNode, name)
            self.referenceToFrameCoordinateWidgets[name].coordinatesChanged.connect(self.updateParameterNodeFromGUI)
            self.referenceToFrameCoordinateWidgets[name].setVisible(False)
            self.ui.referenceToFrameCollapsibleButton.layout().insertRow(5, name + ':', self.referenceToFrameCoordinateWidgets[name])
            self.ui.referenceToFrameCollapsibleButton.layout().labelForField(self.referenceToFrameCoordinateWidgets[name]).setVisible(False)
            self.ui.referenceToFrameModeComboBox.currentTextChanged.connect(lambda t,w=self.referenceToFrameCoordinateWidgets[name]: [w.setVisible(t=='ACPC Register'), self.ui.referenceToFrameCollapsibleButton.layout().labelForField(w).setVisible(t=='ACPC Register')])

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = StereotacticPlan2Logic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
        # (in the selected parameter node).
        self.ui.referenceToFrameTransformNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        # self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        # self.ui.imageThresholdSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
        # self.ui.invertOutputCheckBox.connect("toggled(bool)", self.updateParameterNodeFromGUI)
        # self.ui.invertedOutputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)

        # Buttons
        self.ui.trajectoryComboBox.connect('currentTextChanged(QString)', self.trajectoryChanged)
        self.ui.calculateReferenceToFramePushButton.connect('clicked(bool)', self.onCalculateReferenceToFrame)
        # self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def getOrCreateAuxMarkupsNode(self):
        shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
        for i in range(slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLMarkupsFiducialNode')):
            auxMarkupsNode = slicer.mrmlScene.GetNthNodeByClass(i, 'vtkMRMLMarkupsFiducialNode')
            if 'StereotacticPlan' in shNode.GetItemAttributeNames(shNode.GetItemByDataNode(auxMarkupsNode)):
                return auxMarkupsNode
        auxMarkupsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'SterotacticPlanMarkupsNode')
        shNode.SetItemAttribute(shNode.GetItemByDataNode(auxMarkupsNode), 'StereotacticPlan', '1')
        return auxMarkupsNode

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
        # if not self._parameterNode.GetNodeReference("InputVolume"):
        #     firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        #     if firstVolumeNode:
        #         self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

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

    def trajectoryChanged(self, currentText):
        if currentText == 'Select...':
            self._parameterNode.SetParameter("TrajectoryIndex", "")
            return
        elif currentText == 'Create new trajectory as':
            self.createNewTrajectory()
        elif currentText.startswith('Import from'):
            self.importTrajectoryFrom(currentText.removeprefix('Import from '))
            self.ui.trajectoryComboBox.setCurrentText('Select...')
        elif currentText == 'Delete current trajectory':
            self.deleteCurrentTrajectory()
            self.ui.trajectoryComboBox.setCurrentText('Select...')
        else:
            trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
            trajectoryNames = [trajectory['Name'] for trajectory in trajectories]
            trajectoryIndex = str(trajectoryNames.index(currentText)) if currentText in trajectoryNames else ""
            self._parameterNode.SetParameter("TrajectoryIndex", trajectoryIndex)
        
    def createNewTrajectory(self):
        trajectoryName = qt.QInputDialog.getText(qt.QWidget(), 'New trajectory', 'Name:')
        if not trajectoryName:
            return
        trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
        trajectories.append({k:'0,0,0;RAS' for k in self.trajectoryCoordinateWidgets.keys()})
        trajectories[-1]['Name'] = trajectoryName
        wasModified = self._parameterNode.StartModify() 
        self._parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
        self._parameterNode.SetParameter("TrajectoryIndex", str(len(trajectories)-1))
        self._parameterNode.EndModify(wasModified)

    def deleteCurrentTrajectory(self):
        trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
        trajectoryIndex = self._parameterNode.GetParameter("TrajectoryIndex")
        if trajectories and trajectoryIndex:
            trajectories.pop(int(trajectoryIndex))
        else:
            return
        wasModified = self._parameterNode.StartModify() 
        self._parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
        self._parameterNode.SetParameter("TrajectoryIndex", "")
        self._parameterNode.EndModify(wasModified)

    def importTrajectoryFrom(self, importer):
        print(importer)

    def updateTrajectoriesComboBox(self, trajectoryNames=None):
        trajectoryNames = [] if trajectoryNames is None else trajectoryNames
        importFromOptions = glob.glob(os.path.join(os.path.dirname(__file__), 'StereotacticPlanLib', 'ImportFrom', '*.py'))
        importFromOptions = ['Import from ' + os.path.basename(opt).replace('.py','') for opt in importFromOptions]
        importFromOptions.remove('Import from __init__')
        trajectoryItems = ['Select...'] + trajectoryNames + ['Create new trajectory as'] + importFromOptions + ['Delete current trajectory']
        self.ui.trajectoryComboBox.clear()
        self.ui.trajectoryComboBox.addItems(trajectoryItems)

    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        This method is called whenever parameter node is changed.
        The module GUI is updated to show the current state of the parameter node.
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
        self._updatingGUIFromParameterNode = True

        trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
        trajectoryIndex = self._parameterNode.GetParameter("TrajectoryIndex")

        self.updateTrajectoriesComboBox([trajectory['Name'] for trajectory in trajectories])

        currentTrajectoryAvailable = trajectories and trajectoryIndex

        if currentTrajectoryAvailable:
            currentTrajectory = trajectories[int(trajectoryIndex)]
            self.ui.trajectoryComboBox.setCurrentText(currentTrajectory['Name'])
            self.updateCoordinatesWidgetFromTrajectory(currentTrajectory)
        else:
            self.ui.trajectoryComboBox.setCurrentText('Select...')
            self.ui.referenceToFrameTransformNodeComboBox.setCurrentNode(None)

        for widget in self.trajectoryCoordinateWidgets.values():
            if not currentTrajectoryAvailable:
                widget.reset()
            widget.setEnabled(currentTrajectoryAvailable)

        for name, widget in self.referenceToFrameCoordinateWidgets.items():
            coords, system = self._parameterNode.GetParameter(name).split(';')
            widget.setSystem(system)
            widget.coordinates = coords

        self.ui.calculateReferenceToFramePushButton.setEnabled(self.ui.referenceToFrameTransformNodeComboBox.currentNodeID != '')
        self.ui.referenceToFrameTransformNodeComboBox.setCurrentNode(self._parameterNode.GetNodeReference("ReferenceToFrameTransform"))


        # # Update node selectors and sliders
        # self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
        # self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))
        # self.ui.invertedOutputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolumeInverse"))
        # self.ui.imageThresholdSliderWidget.value = float(self._parameterNode.GetParameter("Threshold"))
        # self.ui.invertOutputCheckBox.checked = (self._parameterNode.GetParameter("Invert") == "true")

        # # Update buttons states and tooltips
        # if self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume"):
        #     self.ui.applyButton.toolTip = "Compute output volume"
        #     self.ui.applyButton.enabled = True
        # else:
        #     self.ui.applyButton.toolTip = "Select input and output volume nodes"
        #     self.ui.applyButton.enabled = False

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

        trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
        trajectoryIndex = self._parameterNode.GetParameter("TrajectoryIndex")

        if trajectories and trajectoryIndex:
            currentTrajectory = trajectories[int(trajectoryIndex)]
            self.updateTrajectoryFromCoordinatesWidget(currentTrajectory)

        for name, widget in self.referenceToFrameCoordinateWidgets.items():
            self._parameterNode.SetParameter(name, '%s;%s' % (widget.coordinates, widget.getSystem()) )

        self._parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
        self._parameterNode.SetNodeReferenceID("ReferenceToFrameTransform", self.ui.referenceToFrameTransformNodeComboBox.currentNodeID)

        # self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
        # self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)
        # self._parameterNode.SetParameter("Threshold", str(self.ui.imageThresholdSliderWidget.value))
        # self._parameterNode.SetParameter("Invert", "true" if self.ui.invertOutputCheckBox.checked else "false")
        # self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.ui.invertedOutputSelector.currentNodeID)


        self._parameterNode.EndModify(wasModified)


    def updateCoordinatesWidgetFromTrajectory(self, trajectory):
        for name, widget in self.trajectoryCoordinateWidgets.items():
            coords, system = trajectory[name].split(';')
            widget.setSystem(system)
            widget.coordinates = coords

    def updateTrajectoryFromCoordinatesWidget(self, trajectory):
        for name, widget in self.trajectoryCoordinateWidgets.items():
             trajectory[name] = '%s;%s' % (widget.coordinates, widget.getSystem())


    def onCalculateReferenceToFrame(self):
        if self.ui.referenceToFrameModeComboBox.currentText == 'ACPC Align':
            self.logic.runACPCAlignment(self.ui.referenceToFrameTransformNodeComboBox.currentNode(),
                                        self.referenceToFrameCoordinateWidgets['Reference AC'].getNumpyCoordinates(system='RAS'),
                                        self.referenceToFrameCoordinateWidgets['Reference PC'].getNumpyCoordinates(system='RAS'),
                                        self.referenceToFrameCoordinateWidgets['Reference MS'].getNumpyCoordinates(system='RAS'))

        elif self.ui.referenceToFrameModeComboBox.currentText == 'ACPC Register':
            sourceCoordinates = [self.referenceToFrameCoordinateWidgets[name].getNumpyCoordinates(system='RAS') for name in ['Reference MS', 'Reference PC', 'Reference AC']]
            targetCoordinates = [self.referenceToFrameCoordinateWidgets[name].getNumpyCoordinates(system='RAS') for name in ['Frame MS', 'Frame PC', 'Frame AC']]
            self.logic.runFiducialRegistration(self.ui.referenceToFrameTransformNodeComboBox.currentNode(),
                                                sourceCoordinates,
                                                targetCoordinates)


    # def onApplyButton(self):
    #     """
    #     Run processing when user clicks "Apply" button.
    #     """
    #     with slicer.util.tryWithErrorDisplay("Failed to compute results.", waitCursor=True):

    #         # Compute output
    #         self.logic.process(self.ui.inputSelector.currentNode(), self.ui.outputSelector.currentNode(),
    #                            self.ui.imageThresholdSliderWidget.value, self.ui.invertOutputCheckBox.checked)

    #         # Compute inverted output (if needed)
    #         if self.ui.invertedOutputSelector.currentNode():
    #             # If additional output volume is selected then result with inverted threshold is written there
    #             self.logic.process(self.ui.inputSelector.currentNode(), self.ui.invertedOutputSelector.currentNode(),
    #                                self.ui.imageThresholdSliderWidget.value, not self.ui.invertOutputCheckBox.checked, showResult=False)


#
# StereotacticPlan2Logic
#

class StereotacticPlan2Logic(ScriptedLoadableModuleLogic):
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
        for name in ["Reference AC", "Reference PC", "Reference MS", "Frame AC", "Frame PC", "Frame MS"]:
            if not parameterNode.GetParameter(name):
                parameterNode.SetParameter(name, "0,0,0;RAS")           
        if not parameterNode.GetParameter("Trajectories"):
            parameterNode.SetParameter("Trajectories", json.dumps([]))
        if not parameterNode.GetParameter("TrajectoryIndex"):
            parameterNode.SetParameter("TrajectoryIndex", "")

    def process(self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True):
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolume or not outputVolume:
            raise ValueError("Input or output volume is invalid")

        import time
        startTime = time.time()
        logging.info('Processing started')

        # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
        cliParams = {
            'InputVolume': inputVolume.GetID(),
            'OutputVolume': outputVolume.GetID(),
            'ThresholdValue': imageThreshold,
            'ThresholdType': 'Above' if invert else 'Below'
        }
        cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
        # We don't need the CLI module node anymore, remove it to not clutter the scene with it
        slicer.mrmlScene.RemoveNode(cliNode)

        stopTime = time.time()
        logging.info(f'Processing completed in {stopTime-startTime:.2f} seconds')

    def runFiducialRegistration(self, outputTransform, sourceCoords, targetCoords):
        auxSourceNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        auxSourceNode.GetDisplayNode().SetVisibility(False)
        for coord in sourceCoords:
            auxSourceNode.AddFiducialFromArray(coord)

        auxTargetNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        auxTargetNode.GetDisplayNode().SetVisibility(False)
        for coord in targetCoords:
            auxTargetNode.AddFiducialFromArray(coord)
            
        parameters = {}
        parameters['fixedLandmarks']  = auxTargetNode.GetID()
        parameters['movingLandmarks'] = auxSourceNode.GetID()
        parameters['saveTransform']   = outputTransform.GetID()
        parameters['transformType']   = 'Rigid'
        slicer.cli.run(slicer.modules.fiducialregistration, None, parameters, wait_for_completion=True, update_display=False)

        slicer.mrmlScene.RemoveNode(auxTargetNode)
        slicer.mrmlScene.RemoveNode(auxSourceNode)


    def runACPCAlignment(self, outputTransform, AC, PC, MS):

        auxLineNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode')
        auxLineNode.GetDisplayNode().SetVisibility(False)
        auxLineNode.AddControlPointWorld(AC, 'AC')
        auxLineNode.AddControlPointWorld(PC, 'PC')

        ACPCMSNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        ACPCMSNode.GetDisplayNode().SetVisibility(False)
        ACPCMSNode.AddFiducialFromArray(AC)
        ACPCMSNode.AddFiducialFromArray(PC)
        ACPCMSNode.AddFiducialFromArray(MS)

        parameters = {}
        parameters['ACPC']  = auxLineNode.GetID()
        parameters['Midline'] = ACPCMSNode.GetID()
        parameters['centerVolume'] = True 
        parameters['OutputTransform'] = outputTransform.GetID()
        slicer.cli.run(slicer.modules.acpctransform, None, parameters, wait_for_completion=True, update_display=False)

        slicer.mrmlScene.RemoveNode(auxLineNode)
        slicer.mrmlScene.RemoveNode(ACPCMSNode)


#
# StereotacticPlan2Test
#

class StereotacticPlan2Test(ScriptedLoadableModuleTest):
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
        self.test_StereotacticPlan21()

    def test_StereotacticPlan21(self):
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
        inputVolume = SampleData.downloadSample('StereotacticPlan21')
        self.delayDisplay('Loaded test data set')

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = StereotacticPlan2Logic()

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
