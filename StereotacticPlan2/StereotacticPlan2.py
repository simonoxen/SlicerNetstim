import logging
import os
import glob
import json
import numpy as np
import vtk, qt

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import StereotacticPlanLib.util
from StereotacticPlanLib.Widgets.CustomWidgets import CustomCoordinatesWidget, TransformableCoordinatesWidget

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
        auxFolderID = self.getOrCreateAuxFolderID()
        
        self.trajectoryCoordinateWidgets = {}
        for name in ['Entry', 'Target']:
            self.trajectoryCoordinateWidgets[name] =  TransformableCoordinatesWidget(auxFolderID, name, self.setTransformableWidgetsState)
            self.trajectoryCoordinateWidgets[name].coordinatesChanged.connect(self.updateParameterNodeFromGUI)
            self.trajectoryCoordinateWidgets[name].coordinatesChanged.connect(self.updateOutputTrajectoryTransform)
            self.ui.trajectoriesCollapsibleButton.layout().insertRow(2,name + ':', self.trajectoryCoordinateWidgets[name])
        for widget in [self.trajectoryCoordinateWidgets['Entry'], self.ui.rollAngleSliderWidget]:
            widget.setVisible(False)
            self.ui.trajectoriesCollapsibleButton.layout().labelForField(widget).setVisible(False)
            self.ui.trajectoryModeComboBox.currentTextChanged.connect(lambda t,w=widget,target_t='Target Entry Roll': [w.setVisible(t==target_t), self.ui.trajectoriesCollapsibleButton.layout().labelForField(w).setVisible(t==target_t)])
        for widget in [self.ui.ringAngleSliderWidget, self.ui.arcAngleSliderWidget, self.ui.mountingComboBox]:
            self.ui.trajectoryModeComboBox.currentTextChanged.connect(lambda t,w=widget,target_t='Target Mounting Ring Arc': [w.setVisible(t==target_t), self.ui.trajectoriesCollapsibleButton.layout().labelForField(w).setVisible(t==target_t)])
        
        self.referenceToFrameCoordinateWidgets = {}
        for name in ['Reference MS', 'Reference PC', 'Reference AC']:
            self.referenceToFrameCoordinateWidgets[name] =  TransformableCoordinatesWidget(auxFolderID, name, self.setTransformableWidgetsState)
            self.referenceToFrameCoordinateWidgets[name].coordinatesChanged.connect(self.updateParameterNodeFromGUI)
            self.ui.referenceToFrameCollapsibleButton.layout().insertRow(1, name + ':', self.referenceToFrameCoordinateWidgets[name])
        for name in ['Frame MS', 'Frame PC', 'Frame AC']:
            self.referenceToFrameCoordinateWidgets[name] =  CustomCoordinatesWidget(auxFolderID, name)
            self.referenceToFrameCoordinateWidgets[name].coordinatesChanged.connect(self.updateParameterNodeFromGUI)
            self.referenceToFrameCoordinateWidgets[name].setVisible(False)
            self.ui.referenceToFrameCollapsibleButton.layout().insertRow(5, name + ':', self.referenceToFrameCoordinateWidgets[name])
            self.ui.referenceToFrameCollapsibleButton.layout().labelForField(self.referenceToFrameCoordinateWidgets[name]).setVisible(False)
            self.ui.referenceToFrameModeComboBox.currentTextChanged.connect(lambda t,w=self.referenceToFrameCoordinateWidgets[name]: [w.setVisible(t=='ACPC Register'), self.ui.referenceToFrameCollapsibleButton.layout().labelForField(w).setVisible(t=='ACPC Register')])

        buttonSize = self.trajectoryCoordinateWidgets['Entry'].transformButton.height
        transformReferenceVolumeAction = qt.QAction()
        transformReferenceVolumeAction.setIcon(qt.QIcon(":/Icons/Transforms.png"))
        transformReferenceVolumeAction.setCheckable(True)
        self.transformReferenceVolumeButton = qt.QToolButton()
        self.transformReferenceVolumeButton.setDefaultAction(transformReferenceVolumeAction)
        self.transformReferenceVolumeButton.setToolButtonStyle(qt.Qt.ToolButtonIconOnly)
        self.transformReferenceVolumeButton.setFixedSize(buttonSize, buttonSize)
        self.transformReferenceVolumeButton.toggled.connect(self.updateParameterNodeFromGUI)
        self.transformReferenceVolumeButton.toggled.connect(self.setTransformableWidgetsState)
        self.ui.referenceVolumeLayout.addWidget(self.transformReferenceVolumeButton)

        viewTrajectoryAction = qt.QAction()
        viewTrajectoryAction.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
        viewTrajectoryAction.setCheckable(True)
        self.ui.viewTrajectoryToolButton.setDefaultAction(viewTrajectoryAction)
        self.ui.viewTrajectoryToolButton.setFixedSize(buttonSize, buttonSize)
        self.ui.viewTrajectoryToolButton.connect("toggled(bool)", self.onViewTrajectoryToggled)

        resliceDriverAction = qt.QAction()
        resliceDriverAction.setIcon(qt.QIcon(qt.QPixmap(self.resourcePath('Icons/VolumeResliceDriver.png'))))
        resliceDriverAction.setCheckable(True)
        self.ui.resliceDriverToolButton.setDefaultAction(resliceDriverAction)
        self.ui.resliceDriverToolButton.connect("toggled(bool)", self.setDefaultResliceDriver)
        self.ui.resliceDriverToolButton.setFixedSize(buttonSize, buttonSize)

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
        self.ui.trajectoryTransformNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", lambda n,w=self.ui.resliceDriverToolButton: self.setDefaultResliceDriver(w.checked))
        self.ui.trajectoryTransformNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updatePreviewLineTransform)
        self.ui.trajectoryTransformNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        self.ui.referenceToFrameTransformNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        self.ui.referenceVolumeNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        self.ui.trajectoryModeComboBox.connect("currentTextChanged(QString)",  self.updateParameterNodeFromGUI)
        self.ui.arcAngleSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
        self.ui.ringAngleSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
        self.ui.rollAngleSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
        self.ui.mountingComboBox.currentIndexChanged.connect(self.updateParameterNodeFromGUI)

        # Buttons
        self.ui.trajectoryComboBox.connect('currentTextChanged(QString)', self.trajectoryChanged)
        self.ui.calculateReferenceToFramePushButton.connect('clicked(bool)', self.onCalculateReferenceToFrame)
        self.ui.calculateTrajectoryPushButton.connect('clicked(bool)', self.onCalculateTrajectory)

        # Auto Update
        self.ui.arcAngleSliderWidget.connect("valueChanged(double)", self.updateOutputTrajectoryTransform)
        self.ui.ringAngleSliderWidget.connect("valueChanged(double)", self.updateOutputTrajectoryTransform)
        self.ui.rollAngleSliderWidget.connect("valueChanged(double)", self.updateOutputTrajectoryTransform)
        self.ui.mountingComboBox.currentIndexChanged.connect(self.updateOutputTrajectoryTransform)
        self.ui.trajectoryModeComboBox.connect("currentTextChanged(QString)",  self.updateOutputTrajectoryTransform)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def getOrCreateAuxFolderID(self):
        shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
        for i in range(slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLFolderDisplayNode')):
            auxFolderID = shNode.GetItemByDataNode(slicer.mrmlScene.GetNthNodeByClass(i, 'vtkMRMLFolderDisplayNode'))
            if 'StereotacticPlan' in shNode.GetItemAttributeNames(auxFolderID):
                shNode.RemoveItemChildren(auxFolderID)
                return auxFolderID
        auxFolderID = shNode.CreateFolderItem(shNode.GetSceneItemID(), 'SterotacticPlanMarkupsNodes')
        displayNode = slicer.vtkMRMLFolderDisplayNode()
        displayNode.SetName(shNode.GetItemName(auxFolderID))
        displayNode.SetHideFromEditors(0)
        displayNode.SetAttribute('SubjectHierarchy.Folder', "1")
        shNode.GetScene().AddNode(displayNode)
        shNode.SetItemDataNode(auxFolderID, displayNode)
        shNode.ItemModified(auxFolderID)
        shNode.SetItemAttribute(auxFolderID, 'StereotacticPlan', '1')
        return auxFolderID

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
            self._parameterNode.SetParameter("TrajectoryIndex", "-1")
            return
        elif currentText == 'Create new trajectory as':
            self.createNewTrajectory()
        elif currentText.startswith('Import from'):
            self.importTrajectoryFrom(currentText.removeprefix('Import from '))
            self.updateGUIFromParameterNode() # update if modified or not
        elif currentText == 'Delete current trajectory':
            self.deleteCurrentTrajectory()
            self.ui.trajectoryComboBox.setCurrentText('Select...')
        else:
            trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
            trajectoryNames = [trajectory['Name'] for trajectory in trajectories]
            trajectoryIndex = str(trajectoryNames.index(currentText)) if currentText in trajectoryNames else "-1"
            self._parameterNode.SetParameter("TrajectoryIndex", trajectoryIndex)
        
    def createNewTrajectory(self):
        trajectoryName = qt.QInputDialog.getText(qt.QWidget(), 'New trajectory', 'Name:')
        if not trajectoryName:
            return
        trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
        trajectory = {}
        trajectory['Entry'] = '0,0,0;RAS'
        trajectory['Target'] = '0,0,0;RAS'
        trajectory['Mounting'] = 'lateral-right'
        trajectory['Ring'] = 90
        trajectory['Arc'] = 90
        trajectory['Roll'] = 0
        trajectory['Mode'] = 'Target Mounting Ring Arc'
        trajectory['OutputTransformID'] = ''
        trajectory['Name'] = trajectoryName
        trajectories.append(trajectory)
        wasModified = self._parameterNode.StartModify() 
        self._parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
        self._parameterNode.SetParameter("TrajectoryIndex", str(len(trajectories)-1))
        self._parameterNode.EndModify(wasModified)

    def deleteCurrentTrajectory(self):
        trajectories = json.loads(self._parameterNode.GetParameter("Trajectories"))
        trajectoryIndex = int(self._parameterNode.GetParameter("TrajectoryIndex"))
        if trajectories and (trajectoryIndex>=0):
            trajectories.pop(trajectoryIndex)
        else:
            return
        wasModified = self._parameterNode.StartModify() 
        self._parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
        self._parameterNode.SetParameter("TrajectoryIndex", "-1")
        self._parameterNode.EndModify(wasModified)

    def importTrajectoryFrom(self, importer):
        # Get importer module
        import StereotacticPlanLib.ImportFrom
        import importlib
        importlib.import_module('.'.join(['StereotacticPlanLib', 'ImportFrom', importer]))
        importerModule = getattr(StereotacticPlanLib.ImportFrom, importer)
        # Modify all properties in a single batch
        wasModified = self._parameterNode.StartModify()  
        importerModule.setParameterNodeFromDevice(self._parameterNode, filePath=None, importInFrameSpace=self.transformReferenceVolumeButton.checked)
        self._parameterNode.EndModify(wasModified)

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
        trajectoryIndex = int(self._parameterNode.GetParameter("TrajectoryIndex"))

        self.updateTrajectoriesComboBox([trajectory['Name'] for trajectory in trajectories])

        currentTrajectoryAvailable = trajectories and (trajectoryIndex>=0)

        self.ui.trajectoryModeComboBox.setEnabled(currentTrajectoryAvailable)
        self.ui.mountingComboBox.setEnabled(currentTrajectoryAvailable)
        self.ui.ringAngleSliderWidget.setEnabled(currentTrajectoryAvailable)
        self.ui.arcAngleSliderWidget.setEnabled(currentTrajectoryAvailable)
        self.ui.rollAngleSliderWidget.setEnabled(currentTrajectoryAvailable)
        self.ui.trajectoryTransformNodeComboBox.setEnabled(currentTrajectoryAvailable)

        if currentTrajectoryAvailable:
            currentTrajectory = trajectories[trajectoryIndex]
            self.ui.trajectoryComboBox.setCurrentText(currentTrajectory['Name'])
            self.ui.trajectoryModeComboBox.setCurrentText(currentTrajectory['Mode'])
            self.ui.mountingComboBox.setCurrentText(currentTrajectory['Mounting'])
            self.ui.ringAngleSliderWidget.value = currentTrajectory['Ring']
            self.ui.arcAngleSliderWidget.value = currentTrajectory['Arc']
            self.ui.rollAngleSliderWidget.value = currentTrajectory['Roll']
            transformNode = slicer.util.getNode(currentTrajectory['OutputTransformID']) if currentTrajectory['OutputTransformID'] else None
            self.ui.trajectoryTransformNodeComboBox.setCurrentNode(transformNode)
            self.updateCoordinatesWidgetFromTrajectory(currentTrajectory)
        else:
            self.ui.trajectoryComboBox.setCurrentText('Select...')
            self.ui.referenceToFrameTransformNodeComboBox.setCurrentNode(None)

        for widget in self.trajectoryCoordinateWidgets.values():
            widget.setTransformNodeID(self._parameterNode.GetNodeReferenceID("ReferenceToFrameTransform"))
            if not currentTrajectoryAvailable:
                widget.reset()
            widget.setEnabled(currentTrajectoryAvailable)

        for name, widget in self.referenceToFrameCoordinateWidgets.items():
            if isinstance(widget, TransformableCoordinatesWidget):
                widget.setTransformNodeID(self._parameterNode.GetNodeReferenceID("ReferenceToFrameTransform"))
            coords, system = self._parameterNode.GetParameter(name).split(';')
            widget.setSystem(system)
            widget.coordinates = coords

        self.ui.viewTrajectoryToolButton.setEnabled(self.ui.trajectoryTransformNodeComboBox.currentNodeID != '')
        self.ui.resliceDriverToolButton.setEnabled(self.ui.trajectoryTransformNodeComboBox.currentNodeID != '')
        self.ui.calculateTrajectoryPushButton.setEnabled(self.ui.trajectoryTransformNodeComboBox.currentNodeID != '')
        self.ui.calculateReferenceToFramePushButton.setEnabled(self.ui.referenceToFrameTransformNodeComboBox.currentNodeID != '')

        self.ui.referenceToFrameTransformNodeComboBox.setCurrentNode(self._parameterNode.GetNodeReference("ReferenceToFrameTransform"))
        self.ui.referenceVolumeNodeComboBox.setCurrentNode(self._parameterNode.GetNodeReference("ReferenceVolume"))

        self.transformReferenceVolumeButton.setEnabled(self._parameterNode.GetNodeReference("ReferenceToFrameTransform") and self._parameterNode.GetNodeReference("ReferenceVolume"))
        self.transformReferenceVolumeButton.setChecked(self._parameterNode.GetNodeReference("ReferenceVolume") and self._parameterNode.GetNodeReference("ReferenceVolume").GetTransformNodeID() is not None)

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
        trajectoryIndex = int(self._parameterNode.GetParameter("TrajectoryIndex"))

        if trajectories and (trajectoryIndex>=0):
            currentTrajectory = trajectories[trajectoryIndex]
            currentTrajectory['Mode'] = self.ui.trajectoryModeComboBox.currentText
            currentTrajectory['Mounting'] = self.ui.mountingComboBox.currentText
            currentTrajectory['Ring'] = self.ui.ringAngleSliderWidget.value
            currentTrajectory['Arc'] = self.ui.arcAngleSliderWidget.value
            currentTrajectory['Roll'] = self.ui.rollAngleSliderWidget.value
            currentTrajectory['OutputTransformID'] = self.ui.trajectoryTransformNodeComboBox.currentNodeID
            self.updateTrajectoryFromCoordinatesWidget(currentTrajectory)

        for name, widget in self.referenceToFrameCoordinateWidgets.items():
            self._parameterNode.SetParameter(name, '%s;%s' % (widget.coordinates, widget.getSystem()) )

        self._parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
        self._parameterNode.SetNodeReferenceID("ReferenceToFrameTransform", self.ui.referenceToFrameTransformNodeComboBox.currentNodeID)
        self._parameterNode.SetNodeReferenceID("ReferenceVolume", self.ui.referenceVolumeNodeComboBox.currentNodeID)

        if self.ui.referenceVolumeNodeComboBox.currentNodeID != "":
            slicer.util.getNode(self.ui.referenceVolumeNodeComboBox.currentNodeID).SetAndObserveTransformNodeID(self.ui.referenceToFrameTransformNodeComboBox.currentNodeID if self.transformReferenceVolumeButton.checked else None)

        self._parameterNode.EndModify(wasModified)


    def updateCoordinatesWidgetFromTrajectory(self, trajectory):
        for name, widget in self.trajectoryCoordinateWidgets.items():
            coords, system = trajectory[name].split(';')
            widget.setSystem(system)
            widget.coordinates = coords

    def updateTrajectoryFromCoordinatesWidget(self, trajectory):
        for name, widget in self.trajectoryCoordinateWidgets.items():
             trajectory[name] = '%s;%s' % (widget.coordinates, widget.getSystem())

    def setTransformableWidgetsState(self, state):           
        for widget in self.trajectoryCoordinateWidgets.values():
            widget.transformButton.setChecked(state)
        for widget in self.referenceToFrameCoordinateWidgets.values():
            if isinstance(widget, TransformableCoordinatesWidget):
                widget.transformButton.setChecked(state)
        self.transformReferenceVolumeButton.setChecked(state)

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

    def updateOutputTrajectoryTransform(self):
        if self.ui.autoUpdateTrajectoryCheckBox.checked and self.ui.trajectoryTransformNodeComboBox.currentNode():
            self.onCalculateTrajectory()

    def onCalculateTrajectory(self):
        try:
            if self.ui.trajectoryModeComboBox.currentText == 'Target Mounting Ring Arc':
                self.logic.computeTrajectoryFromTargetMountingRingArc(self.ui.trajectoryTransformNodeComboBox.currentNode(),
                                self.trajectoryCoordinateWidgets['Target'].getNumpyCoordinates(system='RAS'),
                                self.ui.mountingComboBox.currentText,
                                self.ui.ringAngleSliderWidget.value,
                                self.ui.arcAngleSliderWidget.value)
            else:
                self.logic.computeTrajectoryFromTargetEntryRoll(self.ui.trajectoryTransformNodeComboBox.currentNode(),
                                self.trajectoryCoordinateWidgets['Target'].getNumpyCoordinates(system='RAS'),
                                self.trajectoryCoordinateWidgets['Entry'].getNumpyCoordinates(system='RAS'),
                                self.ui.rollAngleSliderWidget.value)
        except Exception as e:
            slicer.util.errorDisplay("Failed to compute transform: "+str(e))
            import traceback
            traceback.print_exc()


    def onViewTrajectoryToggled(self, state):
        if state:
            # add node and default points
            markupsLineNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode')
            self._parameterNode.SetNodeReferenceID("PreviewLine", markupsLineNode.GetID())
            markupsLineNode.AddControlPointWorld(vtk.vtkVector3d(0,0,0), 'Target')
            markupsLineNode.AddControlPointWorld(vtk.vtkVector3d(0,0,80), '2')
            self.updatePreviewLineTransform(self.ui.trajectoryTransformNodeComboBox.currentNode())
        elif self._parameterNode.GetNodeReferenceID("PreviewLine"):
            # remove node
            slicer.mrmlScene.RemoveNode(self._parameterNode.GetNodeReference("PreviewLine"))

    def updatePreviewLineTransform(self, node):
        if self._parameterNode.GetNodeReferenceID("PreviewLine"):
            self._parameterNode.GetNodeReference("PreviewLine").SetAndObserveTransformNodeID(node.GetID() if node else None)

    def setDefaultResliceDriver(self, state):
        if state:
            # Get Reslice Driver Logic
            try:    
                logic = slicer.modules.volumereslicedriver.logic()
            except:
                qt.QMessageBox.warning(qt.QWidget(),'','Reslice Driver Module not Found')
                return
            transformNodeID = self.ui.trajectoryTransformNodeComboBox.currentNodeID
            # Settings
            redSettings    = {'node':slicer.util.getNode('vtkMRMLSliceNodeRed'),    'mode':6, 'angle':90 , 'flip':True}
            yellowSettings = {'node':slicer.util.getNode('vtkMRMLSliceNodeYellow'), 'mode':5, 'angle':180, 'flip':False}
            greenSettings  = {'node':slicer.util.getNode('vtkMRMLSliceNodeGreen'),  'mode':4, 'angle':180, 'flip':False}
            # Set
            for settings in [redSettings, yellowSettings, greenSettings]:
                logic.SetDriverForSlice(    transformNodeID,    settings['node'])
                logic.SetModeForSlice(      settings['mode'],   settings['node'])
                logic.SetRotationForSlice(  settings['angle'],  settings['node'])
                logic.SetFlipForSlice(      settings['flip'],   settings['node'])
        else:
            sliceNodes = slicer.util.getNodesByClass("vtkMRMLSliceNode")
            for sliceNode in sliceNodes:
                if sliceNode.GetName() == 'Red':
                    sliceNode.SetOrientationToAxial()
                elif sliceNode.GetName() == 'Green':
                    sliceNode.SetOrientationToCoronal()
                elif sliceNode.GetName() == 'Yellow':
                    sliceNode.SetOrientationToSagittal()

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
            parameterNode.SetParameter("TrajectoryIndex", "-1")
        if not parameterNode.GetParameter("TransformableWidgetsChecked"):
            parameterNode.SetParameter("TransformableWidgetsChecked", "0")


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

    def computeTrajectoryFromTargetMountingRingArc(self, outputTransform, frameTargetCoordinates, mounting, ringAngle, arcAngle):
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

    def computeTrajectoryFromTargetEntryRoll(self, outputTransform, frameTargetCoordinates, frameEntryCoordinates, rollAngle):

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
        self.test_BrainlabImport()
    
    def test_BrainlabImport(self):
        import StereotacticPlanLib.ImportFrom.Brainlab as bl
        logic = StereotacticPlan2Logic()
        parameterNode = logic.getParameterNode()
        reportFilePath = "C:\\Users\\simon\\Desktop\\test\\StereotaxyReport.pdf"
        bl.setParameterNodeFromDevice(parameterNode, reportFilePath)
        volumeFilePath = "C:\\Users\\simon\\Desktop\\test\\anat_t1.nii"
        volumeNode = slicer.util.loadVolume(volumeFilePath)
        parameterNode.SetNodeReferenceID("ReferenceVolume", volumeNode.GetID())

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
