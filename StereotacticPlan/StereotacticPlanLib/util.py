import slicer, vtk, qt
import numpy as np
import re
from datetime import datetime


def setDefaultResliceDriver(transformNode):
  # Get Reslice Driver Logic
  try:    
    logic = slicer.modules.volumereslicedriver.logic()
  except:
    qt.QMessageBox.warning(qt.QWidget(),'','Reslice Driver Module not Found')
    return
  # Settings
  redSettings    = {'node':slicer.util.getNode('vtkMRMLSliceNodeRed'),    'mode':6, 'angle':90 , 'flip':True}
  yellowSettings = {'node':slicer.util.getNode('vtkMRMLSliceNodeYellow'), 'mode':5, 'angle':180, 'flip':False}
  greenSettings  = {'node':slicer.util.getNode('vtkMRMLSliceNodeGreen'),  'mode':4, 'angle':180, 'flip':False}
  # Set
  for settings in [redSettings, yellowSettings, greenSettings]:
    logic.SetDriverForSlice(    transformNode,      settings['node'])
    logic.SetModeForSlice(      settings['mode'],   settings['node'])
    logic.SetRotationForSlice(  settings['angle'],  settings['node'])
    logic.SetFlipForSlice(      settings['flip'],   settings['node'])
