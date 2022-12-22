import qt, slicer
import numpy as np
import re
import json
from datetime import datetime
from DICOMLib import DICOMUtils
import pydicom as dicom
import StereotacticPlan2

def setParameterNodeFromDevice(parameterNode, filePath=None, importInFrameSpace=False, DICOMdir=None):

  if filePath is None:
    filePath, computeReferenceToFrame, importACPC, importDICOM, DICOMdir = getOptionsFromDialog(importInFrameSpace)
  else:
    computeReferenceToFrame = True
    importACPC = True
    importDICOM = True if DICOMdir is not None else False

  if filePath is None:
    return

  stereotaxyReport = StereotaxyReport(filePath)
  planningDictionary = stereotaxyReport.getArcSettings()
  
  logic = StereotacticPlan2.StereotacticPlan2Logic()

  wasModified = parameterNode.StartModify()

  if importACPC:
    parameterNode.SetParameter("Frame AC", stereotaxyReport.getCoordinates('AC', 'Headring') + ';XYZ')
    parameterNode.SetParameter("Frame PC", stereotaxyReport.getCoordinates('PC', 'Headring') + ';XYZ')
    parameterNode.SetParameter("Frame MS", stereotaxyReport.getCoordinates('MS', 'Headring') + ';XYZ')
    parameterNode.SetParameter("Reference AC", stereotaxyReport.getCoordinates('AC', 'DICOM') + ';RAS')
    parameterNode.SetParameter("Reference PC", stereotaxyReport.getCoordinates('PC', 'DICOM') + ';RAS')
    parameterNode.SetParameter("Reference MS", stereotaxyReport.getCoordinates('MS', 'DICOM') + ';RAS')
    parameterNode.SetParameter("ReferenceToFrameMode", "ACPC Register")

  if computeReferenceToFrame:
    referenceToFrameNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "Reference To Frame")
    sourceCoordinates = [np.fromstring(stereotaxyReport.getCoordinates(x, 'DICOM'), dtype=float, sep=',') for x in ['AC', 'PC', 'MS']]
    targetCoordinates = [logic.transformCoordsFromXYZToRAS(np.fromstring(stereotaxyReport.getCoordinates(x, 'Headring'), dtype=float, sep=',')) for x in ['AC', 'PC', 'MS']]
    logic.runFiducialRegistration(referenceToFrameNode, sourceCoordinates, targetCoordinates)
    parameterNode.SetNodeReferenceID("ReferenceToFrameTransform", referenceToFrameNode.GetID())

  brainlab_trajectory = {}
  brainlab_trajectory['Name'] = stereotaxyReport.getTrajectoryInformation()['Name']
  brainlab_trajectory['Mode'] = 'Target Mounting Ring Arc'
  if importInFrameSpace:
    brainlab_trajectory['Entry'] = stereotaxyReport.getCoordinates('Entry', 'Headring') + ';XYZ'
    brainlab_trajectory['Target'] = stereotaxyReport.getCoordinates('Target', 'Headring') + ';XYZ'  
  else:
    brainlab_trajectory['Entry'] = stereotaxyReport.getCoordinates('Entry', 'DICOM') + ';RAS'
    brainlab_trajectory['Target'] = stereotaxyReport.getCoordinates('Target', 'DICOM') + ';RAS'
  brainlab_trajectory['Mounting'] = planningDictionary["Mounting"]
  brainlab_trajectory['Arc'] = float(planningDictionary["Arc Angle"])
  brainlab_trajectory['Ring'] = float(planningDictionary["Ring Angle"])
  brainlab_trajectory['Roll'] = 0
  brainlab_trajectory['OutputTransformID'] = ''

  if importDICOM:
    DICOMinfo = stereotaxyReport.getDICOMInformation()
    rawAnatVolumeNode = getImageFromDICOMInformation(DICOMinfo, DICOMdir)
    parameterNode.SetNodeReferenceID("ReferenceVolume", rawAnatVolumeNode.GetID())

  trajectories = json.loads(parameterNode.GetParameter("Trajectories"))
  trajectories.append(brainlab_trajectory)
  parameterNode.SetParameter("Trajectories", json.dumps(trajectories))
  parameterNode.SetParameter("TrajectoryIndex", str(len(trajectories)-1))

  parameterNode.EndModify(wasModified)


def getImageFromDICOMInformation(dcmInfo, dcmDir):
  loadedNodeIDs = []
  with DICOMUtils.TemporaryDICOMDatabase() as database:
    DICOMUtils.importDicom(dcmDir, database)
    series = SlicerDICOMDatabase().getSeriestMatchingDescriptionAndDateTime(dcmInfo['SeriesDescription'], dcmInfo['AcquisitionDateTime'])
    loadedNodeIDs.extend(DICOMUtils.loadSeriesByUID([series]))

  for nodeID in loadedNodeIDs[::-1]:
    volumeNode = slicer.util.getNode(nodeID)
    if re.search('.*' + dcmInfo['SeriesDescription'] + '.*', volumeNode.GetName()):
      return volumeNode

  raise RuntimeError('Unable to find image in DICOM')

class SlicerDICOMDatabase():

  def __init__(self):
      self.db = slicer.dicomDatabase

  def getSeriestMatchingDescriptionAndDateTime(self, descriptionIn, dateTimeIn):
    for patient in self.db.patients():
      for study in self.db.studiesForPatient(patient):
        for series in self.db.seriesForStudy(study):
          try:
            seriesDescription = self.getSeriesAcquisitionInformationFromTag(series, 'SeriesDescription')
            acquisitionDateTime = self.getSeriesAcquisitionInformationFromTag(series, 'AcquisitionDateTime')
            if not acquisitionDateTime:
              acquisitionDate = self.getSeriesAcquisitionInformationFromTag(series, 'AcquisitionDate')
              acquisitionTime = self.getSeriesAcquisitionInformationFromTag(series, 'AcquisitionTime')
              acquisitionDateTime = acquisitionDate + acquisitionTime
            dateTime = self.DICOMDateTimeStringToDateTime(acquisitionDateTime)
          except:
            continue
          descriptionMatch = self.seriesDescriptionMatch(seriesDescription, descriptionIn)
          dateTimeMatch = self.seriesDateTimeMatch(dateTime, dateTimeIn)
          if descriptionMatch and dateTimeMatch:
            return series

  def getSeriesAcquisitionInformationFromTag(self, series, tag):
    fileList = self.db.filesForSeries(series)
    tagStr = str(dicom.tag.Tag(tag))[1:-1].replace(' ','')
    return self.db.fileValue(fileList[0],tagStr)

  @staticmethod
  def DICOMDateTimeStringToDateTime(dateTimeString):
    return datetime.strptime(dateTimeString, '%Y%m%d%H%M%S.%f')

  @staticmethod
  def seriesDescriptionMatch(seriesDescriptionA, seriesDescriptionB):
    return seriesDescriptionA == seriesDescriptionB
  
  @staticmethod
  def seriesDateTimeMatch(seriesDateTimeA, seriesDateTimeB):
    timeDelta = seriesDateTimeA - seriesDateTimeB
    return abs(timeDelta.total_seconds()) < 60 # allow 1 min because of different resolutions

def getOptionsFromDialog(importInFrameSpace):
  dialog = qt.QDialog()
  dialog.setWindowTitle('Brainlab Import Options')

  planningPDFButton = qt.QPushButton('Click to select')
  planningPDFButton.clicked.connect(lambda: planningPDFButton.setText(qt.QFileDialog.getOpenFileName(qt.QWidget(), 'Select Planning PDF', '', '*.pdf')))

  computeReferenceToFrameCheckBox = qt.QCheckBox()
  computeReferenceToFrameCheckBox.setEnabled(False)

  importACPCCheckBox = qt.QCheckBox()
  importACPCCheckBox.connect("toggled(bool)", lambda b: computeReferenceToFrameCheckBox.setEnabled(b))

  DICOMDirButton = qt.QPushButton('Click to select')
  DICOMDirButton.clicked.connect(lambda: DICOMDirButton.setText(qt.QFileDialog.getExistingDirectory(qt.QWidget(), 'Select DICOM directory', '')))
  DICOMDirButton.setEnabled(False)

  importDICOMCheckBox = qt.QCheckBox()
  importDICOMCheckBox.connect("toggled(bool)", lambda b: DICOMDirButton.setEnabled(b))

  buttonBox = qt.QDialogButtonBox(qt.QDialogButtonBox.Ok | qt.QDialogButtonBox.Cancel, qt.Qt.Horizontal, dialog)
  buttonBox.accepted.connect(lambda: dialog.accept())
  buttonBox.rejected.connect(lambda: dialog.reject())

  form = qt.QFormLayout(dialog)
  form.addRow('Planning PDF: ', planningPDFButton)
  if not importInFrameSpace:
    form.addRow('Import ACPC coords: ', importACPCCheckBox)
    form.addRow('Compute reference to frame transform: ', computeReferenceToFrameCheckBox)
    form.addRow('Import reference image: ', importDICOMCheckBox)
    form.addRow('DICOM directory: ', DICOMDirButton)
  form.addRow(buttonBox)

  if dialog.exec() == qt.QDialog.Accepted:
    return  planningPDFButton.text,\
            computeReferenceToFrameCheckBox.checked,\
            importACPCCheckBox.checked,\
            importDICOMCheckBox.checked,\
            DICOMDirButton.text
  else:
    return None, None, None, None, None

class StereotaxyReport():

  def __init__(self, PDFPath):
    try:
      import pdfplumber
    except:
      slicer.util.pip_install('pdfplumber')
      import pdfplumber    
      
    self.pdf = pdfplumber.open(PDFPath)
    self.pdfWidth = float(self.pdf.pages[0].width)
    self.pdfHeight = float(self.pdf.pages[0].height)


  def hasPatientID(self, patientID):
    return patientID == self.getPatientInformation()['Patient ID']

  def hasSide(self, side):
    return side in self.getTrajectoryInformation()['Name']

  def getTrajectoryInformation(self):
    cropRegion = (self.pdfWidth/2, 130, self.pdfWidth, 240)
    tableSettings = {
      "vertical_strategy": "text",
      "horizontal_strategy": "lines",
      "intersection_y_tolerance": 20,    
      "keep_blank_chars": True,
    }
    outList = self.pdf.pages[0].crop(cropRegion).extract_table(tableSettings)
    outDict = {r[0]:r[1] for r in outList}
    return outDict

  def getPatientInformation(self):
    cropRegion = (0, 130, self.pdfWidth/2, 240)
    tableSettings = {
      "vertical_strategy": "text",
      "horizontal_strategy": "lines",
      "intersection_y_tolerance": 20,    
      "keep_blank_chars": True,
    }
    outList = self.pdf.pages[0].crop(cropRegion).extract_table(tableSettings)
    outDict = {r[0]:r[1] for r in outList}
    return outDict

  def getArcSettings(self):
    cropRegion = (0, 419, self.pdfWidth, 480)
    tableSettings = {
      "vertical_strategy": "text",
      "horizontal_strategy": "text",
      "min_words_vertical": 0,
      "keep_blank_chars": True,
    }
    outList = self.pdf.pages[0].crop(cropRegion).extract_table(tableSettings)
    outList = [[outList[0][i], outList[1][i]] for i in range(len(outList[0]))] # Transpose
    outDict = {r[0]:r[1].split(' ')[0] for r in outList} # Remove units
    outDict["Headring Coordinates"] = ",".join([outDict[C] for C in ["X","Y","Z"]]) # Join X Y Z
    return outDict

  def getCoordinates(self, queryPoint, queryCoordinateSystem):
    # define crop bounding box and transform to RAS
    if queryCoordinateSystem == 'Headring':
      if queryPoint in ['Entry', 'Target']:
        PDFPage = 0
        cropBoundingBox = (0, 350 , self.pdfWidth, 395)
      elif queryPoint in ['AC', 'PC', 'MS']:
        PDFPage = 1
        cropBoundingBox = (0, self.pdfHeight * 0.57 , self.pdfWidth/2, self.pdfHeight * 0.85)
    elif queryCoordinateSystem == 'DICOM':
      PDFPage = 1
      cropBoundingBox = (self.pdfWidth/2, self.pdfHeight * 0.57 , self.pdfWidth, self.pdfHeight * 0.85)
    else:
      raise RuntimeError('Invalid queryCoordinateSystem: ' + queryCoordinateSystem)
    # extract text
    PDFText = self.pdf.pages[PDFPage].crop(cropBoundingBox).extract_text()
    # extract coords
    queryPoint = queryPoint + ' Point' if queryPoint in ['AC','PC','MS'] else queryPoint
    m = re.search('(?<=' + queryPoint + ')' + r'\s+[-]?\d+[.]\d+ mm' * 3, PDFText)
    xyz_str = m.group(0).split('mm')
    xyz_flt = [float(x) for x in xyz_str[:-1]]
    # transform
    if queryCoordinateSystem == 'DICOM':
      toRAS = np.array([[ -1,  0,  0,  0],
                        [  0, -1,  0,  0],
                        [  0,  0,  1,  0],
                        [  0,  0,  0,  1]])
      xyz_flt = np.dot(toRAS, np.append(xyz_flt, 1))[:3]
    return ','.join([str(x) for x in xyz_flt])

  def getDICOMInformation(self):
    hStart = self.findHeightContainingText(1, self.pdfHeight * 0.5, "DICOM Coordinates") + 15
    hEnd = self.findHeightContainingText(1, self.pdfHeight * 0.61, "X Y Z") - 5
    cropRegion = (self.pdfWidth/2, hStart , self.pdfWidth, hEnd)
    tableSettings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "lines",
        "min_words_vertical": 1,
        "keep_blank_chars": True,
        "intersection_y_tolerance":15,
        "edge_min_length":15,
        "explicit_horizontal_lines":[hEnd],
        "explicit_vertical_lines":[570]
        }
    outList = self.pdf.pages[1].crop(cropRegion).extract_table(tableSettings)
    outDict = {r[0]:r[1].replace('\n','') for r in outList}
    outDict['SeriesDescription'] = outDict['Image Set']
    outDict['AcquisitionDateTime'] = datetime.strptime(outDict['Scanned'], '%m/%d/%Y, %I:%M %p')
    return outDict

  def findHeightContainingText(self, pageNumber, heightStart, matchText):
    t = None
    maxHeight = heightStart
    while not t or t.find(matchText)==-1:
      maxHeight = maxHeight+1
      t = self.pdf.pages[pageNumber].crop((0, heightStart , self.pdfWidth, maxHeight)).extract_text()
    return maxHeight

