import slicer
import ctk
import qt
import numpy as np

class myCoordinatesWidget(ctk.ctkCoordinatesWidget):

    def __init__(self):
        super().__init__()

        self.markupsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        self.markupsNode.GetDisplayNode().SetTextScale(0)
        self.markupsNode.GetDisplayNode().SetVisibility(0)
        self.markupsNode.AddControlPoint(0,0,0,'')

        self.coordinatesChanged.connect(self.onCoordinatesChanged)

        systemComboBox = qt.QComboBox(self)
        systemComboBox.addItems(['RAS', 'XYZ'])
        systemComboBox.connect('currentTextChanged(QString)', self.onSystemChanged)
        self.layout().addWidget(systemComboBox)

        viewAction = qt.QAction(self)
        viewAction.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
        viewAction.setCheckable(True)
        viewAction.connect("triggered(bool)", self.onViewClicked)
        viewButton = qt.QToolButton(self)
        viewButton.setDefaultAction(viewAction)
        viewButton.setToolButtonStyle(qt.Qt.ToolButtonIconOnly)
        viewButton.setFixedHeight(systemComboBox.height)
        self.layout().addWidget(viewButton)

        placeAction = qt.QAction(self)
        placeAction.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
        placeAction.setCheckable(True)
        placeAction.connect("triggered(bool)", self.onPlaceClicked)
        placeButton = qt.QToolButton(self)
        placeButton.setDefaultAction(placeAction)
        placeButton.setToolButtonStyle(qt.Qt.ToolButtonIconOnly)
        placeButton.setFixedHeight(systemComboBox.height)
        self.layout().addWidget(placeButton)

    def onCoordinatesChanged(self):
        self.markupsNode.SetNthControlPointPositionFromArray(0, self.getNumpyCoordinates())

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
        self.markupsNode.GetDisplayNode().SetVisibility(active)
        if active:
            markupsLogic = slicer.modules.markups.logic()
            markupsLogic.JumpSlicesToNthPointInMarkup(self.markupsNode.GetID(), 0, True)

    def onPlaceClicked(self, active):
        if active:
            interactionNode = slicer.app.applicationLogic().GetInteractionNode()
            selectionNode = slicer.app.applicationLogic().GetSelectionNode()
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(self.markupsNode.GetID())
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
