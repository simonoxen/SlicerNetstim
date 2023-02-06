import os
from abc import ABC
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#
# NetstimPreferences
#

class NetstimPreferences(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NetstimPreferences Plugin"
    self.parent.categories = [""]
    self.parent.dependencies = [] 
    self.parent.contributors = ["Simon Oxenford (Charite Berlin)"]
    self.parent.helpText = ""
    self.parent.hidden = True

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", setUpSettingsPanel)
    slicer.app.connect("startupCompleted()", lambda: NodeObserver())

#
# Node Observer
#
COREG_NODES_NEEDED = 2
NORM_NODES_NEEDED = 2
class NodeObserver(VTKObservationMixin):
  def __init__(self):
    super().__init__()
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)
    self.coreg_nodes_count = 0
    self.norm_nodes_count = 0
  
  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, node):
    nodeName = node.GetName()
    if nodeName.startswith('leaddbs:'):
      task = nodeName.split(':')[1]
      if task == 'coreg':
        self.coreg_nodes_count = self.coreg_nodes_count + 1
        if self.coreg_nodes_count == COREG_NODES_NEEDED:
          self.setUpCoregScene()
      elif task == 'norm':
        self.norm_nodes_count = self.norm_nodes_count + 1
        if self.norm_nodes_count == NORM_NODES_NEEDED:
          self.setUpNormScene()
  
  def setUpCoregScene(self):
    preopNode = slicer.util.getNode('leaddbs:coreg:preop')
    postopNode = slicer.util.getNode('leaddbs:coreg:postop')
    qt.QTimer.singleShot(100, lambda b=preopNode, f=postopNode: slicer.util.setSliceViewerLayers(background=b.GetID(), foreground=f.GetID(), foregroundOpacity=0.5))
    self.coreg_nodes_count = 0

  def setUpNormScene(self):
    templateNode = slicer.util.getNode('leaddbs:norm:template')
    postopNode = slicer.util.getNode('leaddbs:norm:postop')
    qt.QTimer.singleShot(100, lambda b=templateNode, f=postopNode: slicer.util.setSliceViewerLayers(background=b.GetID(), foreground=f.GetID(), foregroundOpacity=0.5))
    self.norm_nodes_count = 0

#
# Settings Panel
#

def setUpSettingsPanel():
  if not slicer.app.commandOptions().noMainWindow:
    settingsPanel = NetstimPreferencesSettingsPanel()
    slicer.app.settingsDialog().addPanel("Lead-DBS", settingsPanel)

class NetstimPreferencesSettingsPanel(ctk.ctkSettingsPanel):
  def __init__(self):
    ctk.ctkSettingsPanel.__init__(self)
    self.ui = NetstimPreferencesSettingsUI(self)


class NetstimPreferencesSettingsUI:
  def __init__(self, parent):
      layout = qt.QFormLayout(parent)

      self.leadDBSPathButton = ctk.ctkDirectoryButton()
      self.leadDBSPathButton.directory = LeadDBSPath().getValue()
      self.leadDBSPathButton.setToolTip("Lead-DBS install directory")
      self.leadDBSPathButton.directoryChanged.connect(self.onLeadDBSPathChanged)
      layout.addRow("Lead-DBS Path: ", self.leadDBSPathButton)

      self.useSmoothAtlasCheckBox = qt.QCheckBox()
      self.useSmoothAtlasCheckBox.checked = UseSmoothAtlas().getValue()
      self.useSmoothAtlasCheckBox.setToolTip("When checked, smoothed version will be used when loading atlases.")
      self.useSmoothAtlasCheckBox.connect("toggled(bool)", self.onUseSmoothAtlasCheckBoxToggled)
      layout.addRow("Use smooth atlases: ", self.useSmoothAtlasCheckBox)

  def onLeadDBSPathChanged(self):
    newDir = self.leadDBSPathButton.directory
    LeadDBSPath().setValue(newDir)
    if not os.path.isfile(os.path.join(newDir,"lead.m")):
      qt.QMessageBox().warning(qt.QWidget(), "Error", "Invalid leaddbs path. Select leaddbs root install directory")

  def onUseSmoothAtlasCheckBoxToggled(self, checked):
    UseSmoothAtlas().setValue(checked)


class NetstimPreference(ABC):
  def __init__(self):
      self.rootKey = "NetstimPreferences/"
  
  def setValue(self, value):
    slicer.app.settings().setValue(self.rootKey + self.key, value)
  
  def getValue(self):
    return slicer.util.settingsValue(self.rootKey + self.key, self.default, converter=self.converter)

class LeadDBSPath(NetstimPreference):
  def __init__(self):
      super().__init__()
      self.key = "leadDBSPath"
      self.default = ""
      self.converter = str

class UseSmoothAtlas(NetstimPreference):
  def __init__(self):
      super().__init__()
      self.key = "useSmoothAtlas"
      self.default = True
      self.converter = slicer.util.toBool