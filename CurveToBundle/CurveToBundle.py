import logging
import os
import json

import vtk
import qt
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import numpy as np

#
# CurveToBundle
#

class CurveToBundle(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "CurveToBundle"  # TODO: make this more human readable by adding spaces
        self.parent.categories = ["Netstim"]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Simon Oxenford (Charite Berlin)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = ""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = ""


#
# CurveToBundleWidget
#

class CurveToBundleWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
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
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/CurveToBundle.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Waypoints slider widget
        from CurveToBundleLib.Widgets.multiHandleSlider import MultiHandleSliderWidget
        self.ui.waypointsValueWidget = MultiHandleSliderWidget()
        waypointsLayout = qt.QVBoxLayout(self.ui.waypointsFrame)
        waypointsLayout.addWidget(self.ui.waypointsValueWidget)

        self.ui.copyPositionsFromCurveToolButton.setIcon(qt.QIcon(":/Icons/Small/SlicerCheckForUpdates.png"))

        # Spread settings
        spreadSettingsMenu = qt.QMenu(self.ui.spreadSettingsToolButton)
        
        self.ui.maxSpreadSpinBox = qt.QSpinBox()
        self.ui.maxSpreadSpinBox.minimum = 1
        self.ui.maxSpreadSpinBox.maximum = 100
        self.ui.maxSpreadSpinBox.value = 10
        maxSpreadMenu = spreadSettingsMenu.addMenu("Max spread")
        action = qt.QWidgetAction(maxSpreadMenu)
        action.setDefaultWidget(self.ui.maxSpreadSpinBox)
        maxSpreadMenu.addAction(action)

        spreadInterpolationMenu = spreadSettingsMenu.addMenu("Interpolation")
        self.ui.spreadInterpolationActionsGroup = qt.QActionGroup(spreadInterpolationMenu)
        self.ui.spreadInterpolationActionsGroup.setExclusive(True)
        for kind in ['linear', 'cubic']:
            action = qt.QAction(kind, spreadInterpolationMenu)
            action.setCheckable(True)
            self.ui.spreadInterpolationActionsGroup.addAction(action)
        action.setChecked(True)
        spreadInterpolationMenu.addActions(self.ui.spreadInterpolationActionsGroup.actions())
        
        self.ui.spreadExtrapolateAction = qt.QAction("Extrapolate", spreadSettingsMenu)
        self.ui.spreadExtrapolateAction.setCheckable(True)
        self.ui.spreadExtrapolateAction.setChecked(True)
        spreadSettingsMenu.addAction(self.ui.spreadExtrapolateAction)

        self.ui.spreadSettingsToolButton.setMenu(spreadSettingsMenu)
        self.ui.spreadSettingsToolButton.setIcon(qt.QIcon(":/Icons/Small/SlicerConfigure.png"))

        # Fibers settings
        fibersSettingsMenu = qt.QMenu(self.ui.fibersSettingsToolButton)

        fibersSampleTypeMenu = fibersSettingsMenu.addMenu("Random type")
        self.ui.fibersSampleTypeActionsGroup = qt.QActionGroup(fibersSampleTypeMenu)
        self.ui.fibersSampleTypeActionsGroup.setExclusive(True)
        for kind in ['uniform', 'normal']:
            action = qt.QAction(kind, fibersSampleTypeMenu)
            action.setCheckable(True)
            self.ui.fibersSampleTypeActionsGroup.addAction(action)
        action.setChecked(True)
        fibersSampleTypeMenu.addActions(self.ui.fibersSampleTypeActionsGroup.actions())

        self.ui.fibersSettingsToolButton.setMenu(fibersSettingsMenu)
        self.ui.fibersSettingsToolButton.setIcon(qt.QIcon(":/Icons/Small/SlicerConfigure.png"))


        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = CurveToBundleLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
        # (in the selected parameter node).
        self.ui.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        self.ui.numberOfFibersSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
        self.ui.waypointSpreadSlider.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
        self.ui.maxSpreadSpinBox.connect("valueChanged(int)", self.updateParameterNodeFromGUI)
        self.ui.copyPositionsFromCurveToolButton.connect("clicked(bool)", self.onCopyPositionsFromCurve)
        self.ui.spreadInterpolationActionsGroup.connect("triggered(QAction*)", self.updateParameterNodeFromGUI)
        self.ui.spreadExtrapolateAction.connect("toggled(bool)", self.updateParameterNodeFromGUI)
        self.ui.fibersSampleTypeActionsGroup.connect("triggered(QAction*)", self.updateParameterNodeFromGUI)

        # Buttons
        self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)

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
        if not self._parameterNode.GetNodeReference("InputCurve"):
            firstCurveNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLMarkupsCurveNode")
            if firstCurveNode:
                self._parameterNode.SetNodeReferenceID("InputCurve", firstCurveNode.GetID())

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
        if self._parameterNode is not None and self.hasObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode):
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

        self.ui.waypointsValueWidget.setParameterNode(self._parameterNode)

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
        self.ui.waypointSpreadSlider.maximum = int(self._parameterNode.GetParameter("MaxSpread"))
        self.ui.maxSpreadSpinBox.value = int(self._parameterNode.GetParameter("MaxSpread"))
        self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputCurve"))
        self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputBundle"))
        self.ui.numberOfFibersSliderWidget.value = float(self._parameterNode.GetParameter("NumberOfFibers"))
        next(filter(lambda action: action.text == self._parameterNode.GetParameter("SpreadInterpolation"), self.ui.spreadInterpolationActionsGroup.actions())).setChecked(True)
        next(filter(lambda action: action.text == self._parameterNode.GetParameter("FibersSampleType"), self.ui.fibersSampleTypeActionsGroup.actions())).setChecked(True)
        self.ui.spreadExtrapolateAction.setChecked(self._parameterNode.GetParameter("SpreadExtrapolate") == "True")

        waypointIndex = int(self._parameterNode.GetParameter("WaypointIndex"))
        if waypointIndex >= 0:
            self.ui.waypointSpreadSlider.setEnabled(True)
            waypoints = json.loads(self._parameterNode.GetParameter("Waypoints"))
            self.ui.waypointSpreadSlider.setValue(float(waypoints[waypointIndex]['spread']))
        else:
            self.ui.waypointSpreadSlider.setEnabled(False)

        # Update buttons states and tooltips
        if self._parameterNode.GetNodeReference("InputCurve") and self._parameterNode.GetNodeReference("OutputBundle"):
            self.ui.applyButton.toolTip = "Compute output bundle"
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = "Select input and output nodes"
            self.ui.applyButton.enabled = False

        if not hasattr(slicer,'vtkMRMLFiberBundleNode'):
            self.ui.outputSelector.enabled = False
            self.ui.outputSelector.toolTip = "This module requires the SlicerDMRI extension"

        # All the GUI updates are done
        self._updatingGUIFromParameterNode = False

        if self.ui.autoApplyCheckBox.checked:
            self.onApplyButton()

    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """
        This method is called when the user makes any change in the GUI.
        The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

        self._parameterNode.SetParameter("MaxSpread", str(self.ui.maxSpreadSpinBox.value))
        self._parameterNode.SetNodeReferenceID("InputCurve", self.ui.inputSelector.currentNodeID)
        self._parameterNode.SetNodeReferenceID("OutputBundle", self.ui.outputSelector.currentNodeID)
        self._parameterNode.SetParameter("NumberOfFibers", str(self.ui.numberOfFibersSliderWidget.value))
        self._parameterNode.SetParameter("SpreadInterpolation", [action.text for action in self.ui.spreadInterpolationActionsGroup.actions() if action.isChecked()][0])
        self._parameterNode.SetParameter("FibersSampleType", [action.text for action in self.ui.fibersSampleTypeActionsGroup.actions() if action.isChecked()][0])
        self._parameterNode.SetParameter("SpreadExtrapolate", str(bool(self.ui.spreadExtrapolateAction.isChecked())))

        index = int(self._parameterNode.GetParameter("WaypointIndex"))
        if index >= 0:
            waypoints = json.loads(self._parameterNode.GetParameter("Waypoints"))
            waypoints[index]['spread'] = self.ui.waypointSpreadSlider.value
            self._parameterNode.SetParameter("Waypoints", json.dumps(waypoints))
        
        self._parameterNode.EndModify(wasModified)

    def onCopyPositionsFromCurve(self):
        curve = self.ui.inputSelector.currentNode()
        if not curve:
            return
        waypoints = []
        curveLength = curve.GetCurveLengthWorld()
        spread = self.ui.maxSpreadSpinBox.value / 2.0
        if curve.GetNumberOfControlPoints() == 1:
            waypoints.append({"position":50, "spread":spread})
        else:
            for i in range(curve.GetNumberOfControlPoints()):
                absVal = curve.GetCurveLengthBetweenStartEndPointsWorld(curve.GetCurvePointIndexFromControlPointIndex(0), curve.GetCurvePointIndexFromControlPointIndex(i))
                waypoints.append({"position":absVal/curveLength*100, "spread":spread})
        self._parameterNode.SetParameter("Waypoints", json.dumps(waypoints))

    def onApplyButton(self):
        """
        Run processing when user clicks "Apply" button.
        """
        with slicer.util.tryWithErrorDisplay("Failed to compute results.", waitCursor=True):

            waypoints = json.loads(self._parameterNode.GetParameter("Waypoints"))
            spreadValues = [item['spread'] for item in waypoints]
            spreadPositions = [item['position'] for item in waypoints]
            spreadInterpolation = [action.text for action in self.ui.spreadInterpolationActionsGroup.actions() if action.isChecked()][0]
            spreadExtrapolate = self.ui.spreadExtrapolateAction.isChecked()

            fibersSampleType = [action.text for action in self.ui.fibersSampleTypeActionsGroup.actions() if action.isChecked()][0]

            # Compute output
            self.logic.process(self.ui.inputSelector.currentNode(), 
                               self.ui.outputSelector.currentNode(),
                               int(self.ui.numberOfFibersSliderWidget.value),
                               fibersSampleType,
                               spreadValues,
                               spreadPositions,
                               spreadInterpolation,
                               spreadExtrapolate)



#
# CurveToBundleLogic
#

class CurveToBundleLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)
        if slicer.util.settingsValue('Developer/DeveloperMode', False, converter=slicer.util.toBool):
            import CurveToBundleLib
            import importlib
            import glob
            curveToBundlePath = os.path.split(__file__)[0]
            G = glob.glob(os.path.join(curveToBundlePath, 'CurveToBundleLib','**','*.py'))
            for g in G:
                relativePath = os.path.relpath(g, curveToBundlePath) # relative path
                relativePath = os.path.splitext(relativePath)[0] # get rid of .py
                moduleParts = relativePath.split(os.path.sep) # separate
                importlib.import_module('.'.join(moduleParts)) # import module
                module = CurveToBundleLib
                for i in range(1,len(moduleParts)): # iterate over parts in order to load subpkgs
                    module = getattr(module, moduleParts[i])
                    importlib.reload(module) # reload
    
    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.
        """
        if not parameterNode.GetParameter("NumberOfFibers"):
            parameterNode.SetParameter("NumberOfFibers", "100")
        if not parameterNode.GetParameter("Waypoints"):
            parameterNode.SetParameter("Waypoints", json.dumps([{"position":0,"spread":5},{"position":100,"spread":5}]))
        if not parameterNode.GetParameter("WaypointIndex"):
            parameterNode.SetParameter("WaypointIndex", "-1")
        if not parameterNode.GetParameter("MaxSpread"):
            parameterNode.SetParameter("MaxSpread", "10")
        if not parameterNode.GetParameter("SpreadInterpolation"):
            parameterNode.SetParameter("SpreadInterpolation", "cubic")
        if not parameterNode.GetParameter("SpreadExtrapolate"):
            parameterNode.SetParameter("SpreadExtrapolate", "True")
        if not parameterNode.GetParameter("FibersSampleType"):
            parameterNode.SetParameter("FibersSampleType", "uniform")

    def getInterpolatedSpreads(self, spreadValues, spreadPositions, spreadInterpolation, spreadExtrapolate, numberOfPoints):
        if len(spreadValues) == 1:
            return np.ones(numberOfPoints) * spreadValues[0]

        spreadInterpolation = 'linear' if len(spreadValues) <= 3 else spreadInterpolation

        fillValue = 'extrapolate' if spreadExtrapolate else (spreadValues[np.argmin(spreadPositions)], spreadValues[np.argmax(spreadPositions)])

        from scipy.interpolate import interp1d
        interpFunction = interp1d(spreadPositions, 
                               spreadValues,
                               kind = spreadInterpolation,
                               bounds_error = False,
                               fill_value = fillValue,
                               assume_sorted = False)

        return interpFunction(np.linspace(0, 100, numberOfPoints))

    def process(self, inputCurve, outputBundle, numberOfFibers, fibersSampleType, spreadValues, spreadPositions, spreadInterpolation, spreadExtrapolate):
        if not inputCurve or not outputBundle:
            raise ValueError("Input or output volume is invalid")
        
        resampleDistance = 1

        resampledCurve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
        resampledCurve.Copy(inputCurve)
        resampledCurve.ResampleCurveWorld(resampleDistance)

        numberOfPoints = resampledCurve.GetNumberOfControlPoints()

        spreads = self.getInterpolatedSpreads(spreadValues, spreadPositions, spreadInterpolation, spreadExtrapolate, numberOfPoints)
        
        curvePoints = np.array([resampledCurve.GetNthControlPointPosition(i) for i in range(numberOfPoints)])
        outPoints = vtk.vtkPoints()
        outLines = vtk.vtkCellArray()
        id = 0
        for _ in range(numberOfFibers):
            if fibersSampleType == 'uniform':
                randomTranslate = np.random.rand(3) * 2 - 1
            elif fibersSampleType == 'normal':
                randomTranslate = np.random.randn(3)
            displacements = np.tile(randomTranslate, (numberOfPoints,1)) * spreads[:,np.newaxis]
            transformedPoints = curvePoints + displacements          
            line = vtk.vtkPolyLine()
            for i in range(numberOfPoints):
                outPoints.InsertNextPoint(transformedPoints[i])
                line.GetPointIds().InsertNextId(id)
                id += 1
            outLines.InsertNextCell(line)
        
        slicer.mrmlScene.RemoveNode(resampledCurve)

        pd = vtk.vtkPolyData()
        pd.SetPoints(outPoints)
        pd.SetLines(outLines)

        outputBundle.SetAndObservePolyData(pd)
        outputBundle.CreateDefaultDisplayNodes()
        outputBundle.GetDisplayNode().SetColorModeToPointFiberOrientation()


#
# CurveToBundleTest
#

class CurveToBundleTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_CurveToBundle1()

    def test_CurveToBundle1(self):
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
        inputVolume = SampleData.downloadSample('CurveToBundle1')
        self.delayDisplay('Loaded test data set')

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = CurveToBundleLogic()

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
