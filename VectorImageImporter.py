from __main__ import vtk, qt, ctk, slicer
import vtk.util.numpy_support

#
# VectorImageImporter
#

class VectorImageImporter:
  def __init__(self, parent):
    parent.title = "VectorImageImporter"
    parent.categories = ["Vector Image Tools"]
    parent.contributors = ["Andrey Fedorov"]
    parent.helpText = """
    Support of VectorImageContainer initialization
    """
    # VectorImageExplorer registers the MRML node type this module is using
    parent.dependencies = ['VectorImageExplorer']
    parent.acknowledgementText = """
    This file was originally developed by Andrey Fedorov, SPL
    """
    self.parent = parent

#
# qVectorImageImporterWidget
#

class VectorImageImporterWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()
    
  def setup(self):
    # Instantiate and connect widgets ...
    
    # Collapsible button
    dummyCollapsibleButton = ctk.ctkCollapsibleButton()
    dummyCollapsibleButton.text = "Basic settings"
    self.layout.addWidget(dummyCollapsibleButton)
    dummyFormLayout = qt.QFormLayout(dummyCollapsibleButton)

    # add input directory selector
    label = qt.QLabel('Input directory:')
    self.__fDialog = ctk.ctkDirectoryButton()
    self.__fDialog.caption = 'Input DICOM directory'
    dummyFormLayout.addRow(label, self.__fDialog)

    label = qt.QLabel('Output node:')
    self.__vcSelector = slicer.qMRMLNodeComboBox()
    self.__vcSelector.nodeTypes = ['vtkMRMLVectorImageContainerNode']
    self.__vcSelector.setMRMLScene(slicer.mrmlScene)
    self.__vcSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    self.__vcSelector.addEnabled = 1
    dummyFormLayout.addRow(label, self.__vcSelector)

    label = qt.QLabel('Input data type:')
    self.__modeSelector = qt.QComboBox()
    self.__modeSelector.connect('currentIndexChanged(int)', self.onProcessingModeChanged)
    dummyFormLayout.addRow(label, self.__modeSelector)

    # Collapsible button
    dummyCollapsibleButton = ctk.ctkCollapsibleButton()
    dummyCollapsibleButton.text = "Advanced settings"
    dummyCollapsibleButton.collapsed = 1
    self.layout.addWidget(dummyCollapsibleButton)
    dummyFormLayout = qt.QFormLayout(dummyCollapsibleButton)
    self.__advancedFrame = dummyCollapsibleButton
 
    # label name and values
    label = qt.QLabel('DICOM tag:')
    label.toolTip = 'DICOM tag used to separate individual volumes in the series'
    self.__dicomTag = qt.QLineEdit()
    self.__dicomTag.text = ""
    self.__dicomTag.enabled = 0
    dummyFormLayout.addRow(label, self.__dicomTag)

    label = qt.QLabel('Units of vector elements:')
    self.__veLabel = qt.QLineEdit()
    self.__veLabel.enabled = 0
    dummyFormLayout.addRow(label, self.__veLabel)

    label = qt.QLabel('Initial value:')
    self.__veInitial = qt.QDoubleSpinBox()
    self.__veInitial.value = 0
    self.__veInitial.enabled = 0
    dummyFormLayout.addRow(label, self.__veInitial)

    label = qt.QLabel('Step:')
    self.__veStep = qt.QDoubleSpinBox()
    self.__veStep.value = 1
    self.__veStep.enabled = 0
    dummyFormLayout.addRow(label, self.__veStep)

    importButton = qt.QPushButton("Import")
    importButton.toolTip = "Import the contents of the DICOM directory as a VectorImageContainer"
    self.layout.addWidget(importButton)
    self.populateProcessingModes()
    importButton.connect('clicked(bool)', self.onImportButtonClicked)

    self.__status = qt.QLabel('Status: Idle')
    self.layout.addWidget(self.__status)

    
    # Add vertical spacer
    self.layout.addStretch(1)
    
  def populateProcessingModes(self):
    self.__modeSelector.addItem('DICOM 4D DCE MRI (GE)')
    self.__modeSelector.addItem('List of 3D frames')
    self.__modeSelector.currentIndex = 0
    '''
    self.__modeSelector.addItem('DICOM Multi-TE MRI (GE)')
    self.__modeSelector.addItem('DICOM Multi-FA MRI (GE)')
    self.__modeSelector.addItem('DICOM Multi-TR MRI (GE)')
    '''

  def onProcessingModeChanged(self, idx):
    if idx == 0:
      self.__advancedFrame.enabled = 0
      self.__dicomTag.text = "0018|1060"
      self.__veLabel.text = "ms"
      self.__veInitial.value = -1
      self.__veStep.value = -1
    if idx == 1:
      self.__advancedFrame.enabled = 1

    '''
    if idx == 1:
      return ["0018|0081", "sec"]
    if idx == 2:
      return "0018|1314"
    if idx == 3:
      return "0018|0080"
    '''
    

  def onMRMLSceneChanged(self, mrmlScene):
    self.__vcSelector.setMRMLScene(slicer.mrmlScene)
    return
 
  def onImportButtonClicked(self):
    # check if the output container exists
    vcNode = self.__vcSelector.currentNode()
    if vcNode == None:
      self.__status.text = 'Status: Select output container!'
      return

    # get logic
    logic = slicer.modules.vectorimageexplorer.logic()

    # create a clean temporary directory
    tmpDir = slicer.app.settings().value('Modules/TemporaryDirectory')
    if not os.path.exists(tmpDir):
      os.mkdir(tmpDir)
    tmpDir = tmpDir+'/MultiVolumeImporter'
    if not os.path.exists(tmpDir):
      os.mkdir(tmpDir)
    volumeLabels = vtk.vtkDoubleArray()
    nFrames = logic.ProcessDICOMSeries(self.__fDialog.directory, tmpDir, self.__dicomTag.text, volumeLabels)

    self.__status.text = 'Series processed OK, '+str(nFrames)+' volumes identified'

    print 'Location of files:',tmpDir

    frameList = []
    volumesLogic = slicer.modules.volumes.logic()
    fileNames = os.listdir(tmpDir)
    fileNames.sort()
    
    # read the first frame to get the extent for DWI node
    fullName = tmpDir+'/'+fileNames[0]
    frame = volumesLogic.AddArchetypeVolume(fullName, 'Frame 0', 0)
    #os.unlink(fullName)
    frameImage = frame.GetImageData()
    frameExtent = frameImage.GetExtent()
    frameSize = frameExtent[1]*frameExtent[3]*frameExtent[5]

    nFrames = len(fileNames)
    dwiImage = vtk.vtkImageData()
    dwiImage.SetExtent(frameExtent)
    dwiImage.SetNumberOfScalarComponents(nFrames)

    dwiImage.AllocateScalars()
    dwiImageArray = vtk.util.numpy_support.vtk_to_numpy(dwiImage.GetPointData().GetScalars())

    # create and initialize a blank DWI node
    bValues = vtk.vtkDoubleArray()
    bValues.Allocate(nFrames)
    bValues.SetNumberOfComponents(1)
    bValues.SetNumberOfTuples(nFrames)
    gradients = vtk.vtkDoubleArray()
    gradients.Allocate(nFrames*3)
    gradients.SetNumberOfComponents(3)
    gradients.SetNumberOfTuples(nFrames)
    print 'Sorted list of file names: ',fileNames

    bValuesArray = vtk.util.numpy_support.vtk_to_numpy(bValues)
    gradientsArray = vtk.util.numpy_support.vtk_to_numpy(gradients)
    bValuesArray[:] = 0
    gradientsArray[:] = 1
    
    dwiNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLDiffusionWeightedVolumeNode')
    dwiNode.SetScene(slicer.mrmlScene)
    dwiNode.SetBValues(bValues)
    dwiNode.SetDiffusionGradients(gradients)
    
    mat = vtk.vtkMatrix4x4()
    frame.GetRASToIJKMatrix(mat)
    dwiNode.SetRASToIJKMatrix(mat)
    frame.GetIJKToRASMatrix(mat)
    dwiNode.SetIJKToRASMatrix(mat)

    self.annihilateScalarNode(frame)

    for frameId in range(0,nFrames):
      fullName = tmpDir+'/'+fileNames[frameId]
      print 'Processing frame ',frameId,': ',fullName
      frame = volumesLogic.AddArchetypeVolume(fullName, 'Frame'+str(frameId), 0)
      frameImage = frame.GetImageData()
      frameImageArray = vtk.util.numpy_support.vtk_to_numpy(frameImage.GetPointData().GetScalars())
      dwiImageArray.T[frameId] = frameImageArray
      self.annihilateScalarNode(frame)
      os.unlink(fullName)

    dwiDisplayNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLDiffusionWeightedVolumeDisplayNode')
    dwiDisplayNode.SetScene(slicer.mrmlScene)
    slicer.mrmlScene.AddNode(dwiDisplayNode)
    dwiDisplayNode.SetDefaultColorMap()

    dwiNode.SetAndObserveDisplayNodeID(dwiDisplayNode.GetID())
    dwiNode.SetAndObserveImageData(dwiImage)
    slicer.mrmlScene.AddNode(dwiNode)
    print 'DWI node added to the scene'


    vcNode.SetDWVNodeID(dwiNode.GetID())
    vcNode.SetVectorLabelArray(volumeLabels)
    vcNode.SetVectorLabelName(self.__veLabel.text)
    print 'VC node setup!'


  # leave no trace of the temporary nodes
  def annihilateScalarNode(self, node):
    dn = node.GetDisplayNode()
    sn = node.GetStorageNode()
    node.SetAndObserveDisplayNodeID(None)
    node.SetAndObserveStorageNodeID(None)
    slicer.mrmlScene.RemoveNode(dn)
    slicer.mrmlScene.RemoveNode(sn)
    slicer.mrmlScene.RemoveNode(node)

