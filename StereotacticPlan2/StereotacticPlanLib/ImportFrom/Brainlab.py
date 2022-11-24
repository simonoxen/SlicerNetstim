import qt, slicer
import numpy as np
import re

def setParameterNodeFromDevice(parameterNode, filePath=None):
  filePath = qt.QFileDialog.getOpenFileName(qt.QWidget(), 'Select Planning PDF', '', '*.pdf') if filePath is None else filePath
  if filePath == '':
    return
  # get planning
  stereotaxyReport = StereotaxyReport(filePath)
  planningDictionary = stereotaxyReport.getArcSettings()
  # "Reference AC", "Reference PC", "Reference MS", "Frame AC", "Frame PC", "Frame MS"
  parameterNode.SetParameter("Frame AC", ','.join([str(x) for x in stereotaxyReport.getCoordinates('AC', 'Headring')]) + ';XYZ')
  parameterNode.SetParameter("Frame PC", ','.join([str(x) for x in stereotaxyReport.getCoordinates('PC', 'Headring')]) + ';XYZ')
  parameterNode.SetParameter("Frame MS", ','.join([str(x) for x in stereotaxyReport.getCoordinates('MS', 'Headring')]) + ';XYZ')
  parameterNode.SetParameter("Reference AC", ','.join([str(x) for x in stereotaxyReport.getCoordinates('AC', 'DICOM')]) + ';RAS')
  parameterNode.SetParameter("Reference PC", ','.join([str(x) for x in stereotaxyReport.getCoordinates('PC', 'DICOM')]) + ';RAS')
  parameterNode.SetParameter("Reference MS", ','.join([str(x) for x in stereotaxyReport.getCoordinates('MS', 'DICOM')]) + ';RAS')
  # # frame fiducials
  # frameFidNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','FrameFid')
  # frameFidNode.AddFiducialFromArray(stereotaxyReport.getCoordinates('AC', 'Headring'), 'frameAC')
  # frameFidNode.AddFiducialFromArray(stereotaxyReport.getCoordinates('PC', 'Headring'), 'framePC')
  # frameFidNode.AddFiducialFromArray(stereotaxyReport.getCoordinates('MS', 'Headring'), 'frameMS')
  # # anat fiducials
  # referenceFidNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','ReferenceFid')
  # referenceFidNode.AddFiducialFromArray(stereotaxyReport.getCoordinates('AC', 'DICOM'), 'anatAC')
  # referenceFidNode.AddFiducialFromArray(stereotaxyReport.getCoordinates('PC', 'DICOM'), 'anatPC')
  # referenceFidNode.AddFiducialFromArray(stereotaxyReport.getCoordinates('MS', 'DICOM'), 'anatMS')
  # # set values
  # wasModified = parameterNode.StartModify()
  # parameterNode.SetParameter("ArcAngle", planningDictionary["Arc Angle"])
  # parameterNode.SetParameter("RingAngle", planningDictionary["Ring Angle"])
  # parameterNode.SetParameter("FrameTargetCoordinates", planningDictionary["Headring Coordinates"])
  # parameterNode.SetParameter("Mounting", planningDictionary["Mounting"])
  # parameterNode.SetNodeReferenceID("ReferenceACPCMSMarkups", referenceFidNode.GetID())
  # parameterNode.SetNodeReferenceID("FrameACPCMSMarkups", frameFidNode.GetID())
  # parameterNode.SetParameter("ApplyXYZToRAS", "1")
  # parameterNode.EndModify(wasModified)
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
      cropBoundingBox = (0, self.pdfHeight * 0.57 , self.pdfWidth/2, self.pdfHeight * 0.85)     
    elif queryCoordinateSystem == 'DICOM':
      cropBoundingBox = (self.pdfWidth/2, self.pdfHeight * 0.57 , self.pdfWidth, self.pdfHeight * 0.85)
    else:
      raise RuntimeError('Invalid queryCoordinateSystem: ' + queryCoordinateSystem)
    # extract text
    PDFText = self.pdf.pages[1].crop(cropBoundingBox).extract_text()
    # extract coords
    m = re.search('(?<=' + queryPoint + ' Point)' + r' [-]?\d+[.]\d+ mm' * 3, PDFText)
    xyz_str = m.group(0).split('mm')
    xyz_flt = [float(x) for x in xyz_str[:-1]]
    # transform
    if queryCoordinateSystem == 'DICOM':
      toRAS = np.array([[ -1,  0,  0,  0],
                        [  0, -1,  0,  0],
                        [  0,  0,  1,  0],
                        [  0,  0,  0,  1]])
      xyz_flt = np.dot(toRAS, np.append(xyz_flt, 1))[:3]
    return xyz_flt

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

