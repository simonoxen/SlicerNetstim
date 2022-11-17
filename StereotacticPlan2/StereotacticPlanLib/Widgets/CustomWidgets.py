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

        viewAction = qt.QAction(self)
        viewAction.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
        viewAction.setCheckable(True)
        viewAction.connect("triggered(bool)", self.onViewClicked)
        viewButton = qt.QToolButton(self)
        viewButton.setDefaultAction(viewAction)
        viewButton.setToolButtonStyle(qt.Qt.ToolButtonIconOnly)
        viewButton.setFixedHeight(self.systemComboBox.height)
        self.layout().addWidget(viewButton)

        placeAction = qt.QAction(self)
        placeAction.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
        placeAction.setCheckable(True)
        placeAction.connect("toggled(bool)", self.onPlaceToggled)
        placeButton = qt.QToolButton(self)
        placeButton.setDefaultAction(placeAction)
        placeButton.setToolButtonStyle(qt.Qt.ToolButtonIconOnly)
        placeButton.setFixedHeight(self.systemComboBox.height)
        self.layout().addWidget(placeButton)

        self.markupsNode = auxMarkupsNode
        self.markupsNode.AddControlPoint(0, 0, 0, name)
        self.markupsNode.AddObserver(self.markupsNode.PointModifiedEvent, self.updateCoordinatesFromMarkupsNode)
        self.markupsNode.AddObserver(self.markupsNode.PointPositionDefinedEvent, lambda c,e,pa=placeAction: pa.setChecked(False))

        self.markupsNodeControlPointIndex = self.markupsNode.GetNumberOfControlPoints()-1
        self.markupsNode.SetNthControlPointVisibility(self.markupsNodeControlPointIndex, False)
        self.markupsNode.SetNthControlPointLocked(self.markupsNodeControlPointIndex, True)

        self.coordinatesChanged.connect(self.updateMarkupsNodeFromCoordinates)


    def updateCoordinatesFromMarkupsNode(self, caller, event):
        if self._updatingMarkupsFromCoordinates:
            return
        pos = np.zeros(3)
        self.markupsNode.GetNthControlPointPosition(self.markupsNodeControlPointIndex, pos)
        self.setNumpyCoordinates(pos)

    def updateMarkupsNodeFromCoordinates(self):
        if self._updatingCoordinatesFromMarkups:
            return
        self._updatingMarkupsFromCoordinates = True
        coords = self.getNumpyCoordinates()
        if self.systemComboBox.currentText == 'XYZ':
            coords = np.dot(self.getFrameXYZToRASTransform(), np.append(coords, 1))[:3]
        self.markupsNode.SetNthControlPointPositionFromArray(0, coords)
        self._updatingMarkupsFromCoordinates = False

    def onSystemChanged(self, system):
        if system == 'RAS':
            coords =  np.dot(self.getFrameXYZToRASTransform(), np.append(self.getNumpyCoordinates(), 1))[:3]
        elif system == 'XYZ':
            coords = np.dot(np.linalg.inv(self.getFrameXYZToRASTransform()), np.append(self.getNumpyCoordinates(), 1))[:3]
        self.setNumpyCoordinates(coords)

    def getNumpyCoordinates(self):
        return np.fromstring(self.coordinates, dtype=float, sep=',')

    def setNumpyCoordinates(self, coords):
        self.coordinates = ','.join([str(x) for x in coords])

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
