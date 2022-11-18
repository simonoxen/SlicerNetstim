import slicer
import ctk
import qt
import numpy as np

class myCoordinatesWidget(ctk.ctkCoordinatesWidget):

    def __init__(self, auxMarkupsNode, name):
        super().__init__()

        self._updatingCoordinatesFromMarkups = False
        self._updatingMarkupsFromCoordinates = False
        self._wasXYZ = False

        self.systemComboBox = qt.QComboBox(self)
        self.systemComboBox.addItems(['RAS', 'XYZ'])
        self.systemComboBox.connect('currentTextChanged(QString)', self.onSystemChanged)
        self.layout().addWidget(self.systemComboBox)

        buttonSize = self.systemComboBox.height * 0.75

        viewAction = qt.QAction(self)
        viewAction.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
        viewAction.setCheckable(True)
        viewAction.connect("triggered(bool)", self.onViewClicked)
        self.viewButton = qt.QToolButton(self)
        self.viewButton.setDefaultAction(viewAction)
        self.viewButton.setToolButtonStyle(qt.Qt.ToolButtonIconOnly)
        self.viewButton.setFixedSize(buttonSize, buttonSize)
        self.layout().addWidget(self.viewButton)

        placeAction = qt.QAction(self)
        placeAction.setIcon(qt.QIcon(":/Icons/MarkupsFiducialMouseModePlace.png"))
        placeAction.setCheckable(True)
        placeAction.connect("toggled(bool)", self.onPlaceToggled)
        self.placeButton = qt.QToolButton(self)
        self.placeButton.setDefaultAction(placeAction)
        self.placeButton.setToolButtonStyle(qt.Qt.ToolButtonIconOnly)
        self.placeButton.setFixedSize(buttonSize, buttonSize)
        self.layout().addWidget(self.placeButton)

        self.markupsNode = auxMarkupsNode
        self.markupsNode.AddControlPoint(0, 0, 0, name)
        self.markupsNodeControlPointIndex = self.markupsNode.GetNumberOfControlPoints()-1
        self.markupsNode.SetNthControlPointVisibility(self.markupsNodeControlPointIndex, False)
        self.markupsNode.SetNthControlPointLocked(self.markupsNodeControlPointIndex, True)

        self.markupsNode.AddObserver(self.markupsNode.PointModifiedEvent, self.updateCoordinatesFromMarkupsNode)
        self.markupsNode.AddObserver(self.markupsNode.PointPositionDefinedEvent, lambda c,e,pa=placeAction: pa.setChecked(False))

        self.coordinatesChanged.connect(self.updateMarkupsNodeFromCoordinates)

    def reset(self):
        self.setSystem('RAS')
        self.coordinates = '0,0,0'

    def setSystem(self, system):
        self.systemComboBox.currentText = system
    
    def getSystem(self):
        return self.systemComboBox.currentText

    def updateCoordinatesFromMarkupsNode(self, caller, event):
        if self._updatingMarkupsFromCoordinates:
            return
        coords = np.zeros(3)
        self.markupsNode.GetNthControlPointPosition(self.markupsNodeControlPointIndex, coords)
        if self.systemComboBox.currentText == 'XYZ':
            coords = self.transformCoordsFromRASToXYZ(coords)
        self.setNumpyCoordinates(coords)

    def updateMarkupsNodeFromCoordinates(self):
        if self._updatingCoordinatesFromMarkups:
            return
        self._updatingMarkupsFromCoordinates = True
        coords = self.getNumpyCoordinates()
        if self.systemComboBox.currentText == 'XYZ':
            coords = self.transformCoordsFromXYZToRAS(coords)
        self.markupsNode.SetNthControlPointPosition(self.markupsNodeControlPointIndex, coords)
        self._updatingMarkupsFromCoordinates = False

    def onSystemChanged(self, system):
        if system == 'RAS':
            coords =  self.transformCoordsFromXYZToRAS(self.getNumpyCoordinates())
        elif system == 'XYZ':
            coords = self.transformCoordsFromRASToXYZ(self.getNumpyCoordinates())
        self.setNumpyCoordinates(coords)

    def getNumpyCoordinates(self, system=None):
        coords = np.fromstring(self.coordinates, dtype=float, sep=',')
        if (system is None) or (system == self.getSystem()):
            return coords
        elif system == 'RAS':
            return self.transformCoordsFromXYZToRAS(coords)
        elif system == 'XYZ':
            return self.transformCoordsFromRASToXYZ(coords)
        else:
            raise RuntimeError('Unknown system: ' + system)

    def setNumpyCoordinates(self, coords):
        self.coordinates = ','.join([str(x) for x in coords])

    def transformCoordsFromXYZToRAS(self, coords):
        return  np.dot(self.getFrameXYZToRASTransform(), np.append(coords, 1))[:3]

    def transformCoordsFromRASToXYZ(self, coords):
        return np.dot(np.linalg.inv(self.getFrameXYZToRASTransform()), np.append(coords, 1))[:3]

    def getFrameXYZToRASTransform(self):
        # Headring coordinates to Slicer world (matching center)
        frameToRAS = np.array([[ -1,  0,  0,  100],
                                [  0,  1,  0, -100],
                                [  0,  0, -1,  100],
                                [  0,  0,  0,    1]])
        return frameToRAS                       

    def onViewClicked(self, active):
        self.markupsNode.SetNthControlPointVisibility(self.markupsNodeControlPointIndex, active)
        if active:
            markupsLogic = slicer.modules.markups.logic()
            markupsLogic.JumpSlicesToNthPointInMarkup(self.markupsNode.GetID(), self.markupsNodeControlPointIndex, True)

    def onPlaceToggled(self, active):
        if active:
            self._wasXYZ = self.systemComboBox.currentText == 'XYZ'
            self.systemComboBox.currentText = 'RAS'
            self._updatingCoordinatesFromMarkups = True
            self.markupsNode.SetNthControlPointLocked(self.markupsNodeControlPointIndex, False)
            self.markupsNode.ResetNthControlPointPosition(self.markupsNodeControlPointIndex)
            interactionNode = slicer.app.applicationLogic().GetInteractionNode()
            selectionNode = slicer.app.applicationLogic().GetSelectionNode()
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(self.markupsNode.GetID())
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        else:
            self.markupsNode.SetNthControlPointLocked(self.markupsNodeControlPointIndex, True)
            self._updatingCoordinatesFromMarkups = False
            self.systemComboBox.currentText = 'XYZ' if self._wasXYZ else 'RAS'

