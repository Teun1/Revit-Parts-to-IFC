# // HEADER ==================================================

import clr
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
clr.AddReference('RevitAPI')
import Autodesk
from Autodesk.Revit.DB import *

from Autodesk.Revit.DB.BuiltInCategory import *

import sys
pyt_path = r'C:\Program Files (x86)\IronPython 2.7\Lib'
sys.path.append(pyt_path)

doc = DocumentManager.Instance.CurrentDBDocument

# // script Header =========================================

lstTMP = [] 		# just a temporary list that can be used with a reporting purpose
lstOUT = [] 		# the reporting output List
setTMP = set()		# a set to determine if a Parameter of the Part has been set before
setType = set()		# a set to determine if a System Family has been checked for Layers
setLayer = {0:0}	# a dictionary with Layer names
strComments = ''	# a string to add a comment to the Part > needed for visual filtering / finding failures etc
lstCount = []		# a counter for changed items

# // ==========================================================
# // Functions ================================================

def defParameters(item, itemHost, obParamHost, strParam = None):
	if strParam == None:
		strParam = obParamHost.Definition.Name
	if not isinstance(strParam,str):
		strValue = strParam[1]
		strParam = strParam[0]
	else:
		strValue = None
	if item.LookupParameter(strParam) and strParam not in setTMP:
		if strValue == None:
			strST = obParamHost.StorageType
			if strST == StorageType.String: 
				strValue = obParamHost.AsString()
			elif strST == StorageType.ElementId: 
				strValue = obParamHost.AsElementId()
			elif strST == StorageType.Double:
			#	ProjectUnits = obParamHost.DisplayUnitType	 # not needed here in this script
			#	strValue = UnitUtils.ConvertFromInternalUnits(obParamHost.AsDouble(),ProjectUnits)
				strValue = obParamHost.AsDouble()
			else: 
				strValue = obParamHost.AsInteger()
			if strValue is None: 
				strValue = ''		
		try:
			if item.LookupParameter(strParam).IsReadOnly == False:	# parameter must be changable
				item.LookupParameter(strParam).Set(strValue)	# or check first if a change is needed
			lstTMP.append([strParam,strValue])
			setTMP.add(strParam)
		except:
			lstOUT(['failure',item,strParam,strValue])

def defLayers(obType, item, obLink = None):
	if obType.Id not in setType:
		setType.add(obType.Id)
		if item.get_Parameter(BuiltInParameter.DPART_LAYER_WIDTH):
			lstLayers = obType.GetCompoundStructure().GetLayers()
			for obLayer in obType.GetCompoundStructure().GetLayers():
				strDict = obType.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
				if obLink != None:
					obMaterial = obLink.GetLinkDocument().GetElement(obLayer.MaterialId)
				else:
					obMaterial = doc.GetElement(obLayer.MaterialId)
				strDict = strDict + ':' + str(obMaterial.Name)		# sometimes <ByCategory> in the IFC > change it in the model ! 
				# strDict = strDict + '-' + str(obLayer.Width) # perhaps in future
				setLayer[strDict] = obLayer.Function
				# dig deeper in the Materials?: AppearanceAddetId / StructuralAssetId / ThermalAssetId 
				#	/ ALL_MODEL_MANUFACTURER / ALL_MODEL_MODEL / UNIFORMAT_CODE etc
		else:
			strDict = obType.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
			setLayer[strDict] = 'UnNone'
		obLink = None

# // ==========================================================
# // Script ===================================================

collector = FilteredElementCollector(doc)
lstFilter = ElementCategoryFilter(OST_Parts)
lstCollector = collector.WherePasses(lstFilter).WhereElementIsNotElementType()

TransactionManager.Instance.EnsureInTransaction(doc) 

for item in lstCollector:
#	try:
		# lstOUT.append(lstTMP)		# complete report of all the changes - only use if neccesary
		strComments = ''		# reset the comments
		lstTMP = []			# reset the temp list 
		setTMP.clear()			# reset the changed parameter list for this part
		itemOriginal = item		# save the item that is beeing checked to find the original Host
		while True:
			obSourceElementId = item.PartMaker.GetSourceElementIds()[0]
			# why a list ? I can only use 1 so I take the first one of the list - most of the times oke - otherwise change manual
			# otherwise here should be the check for the 'right' host to reuse its parameters
			itemHost = doc.GetElement(obSourceElementId.HostElementId)
			if not itemHost:	# then it must be inside a link
				strComments = strComments + 'Linked Part - '
				obLink = doc.GetElement(obSourceElementId.LinkInstanceId)
				itemHost = obLink.GetLinkDocument().GetElement(obSourceElementId.LinkedElementId)
				obType = obLink.GetLinkDocument().GetElement(itemHost.GetTypeId())
				defLayers(obType, item, obLink)
				break
			if item.Category.Id != itemHost.Category.Id:
				obType = doc.GetElement(itemHost.get_Parameter(BuiltInParameter.SYMBOL_ID_PARAM).AsElementId())
				defLayers(obType, item)
				break
			else:
				if not 'Changed Part' in strComments: 
					strComments = strComments + 'Changed Part - '
			item = itemHost		# the looping part to find the original
		item = itemOriginal		# reset the looping part to the revit item that needs to be changed
		
		if itemHost:
			if obType:
				lstTMP.append([item,itemHost,obType])

				# the order in this script determines the output values to the Part Parameters
				#	> IFC overide parameters before native Revit parameters
				#	> first Instance then Type

				# Report to the 'Comments' or IfcDescription Instance Parameter ==============================
				strComments = strComments + ' Original = ' + obType.get_Parameter(BuiltInParameter.SYMBOL_FAMILY_AND_TYPE_NAMES_PARAM).AsString()
				if item.LookupParameter('IfcDescription'):
					obParam = item.LookupParameter('IfcDescription')
				else:
					obParam = item.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
				obParam.Set(strComments)
				setTMP.add('IfcDescription')

				# Instance IFC Parameters ====================================================================
				for obParam in itemHost.Parameters:
					if str(obParam.Definition.ParameterGroup) == 'PG_IFC':
						defParameters(item, itemHost, obParam)

				# Type IFC Parameters ========================================================================
				for obParam in obType.Parameters:
					if str(obParam.Definition.ParameterGroup) == 'PG_IFC':
						defParameters(item, itemHost, obParam)

				# Instance specific Parameters ===============================================================
				if itemHost.LookupParameter('IsExternal'):
					obParam = itemHost.LookupParameter('IsExternal')
					defParameters(item, itemHost, obParam, 'IsExternal')
				if itemHost.LookupParameter('Fire Rating'):
					obParam = itemHost.LookupParameter('Fire Rating')
					defParameters(item, itemHost, obParam, 'FireRating')
				if itemHost.LookupParameter('Structural'):
					obParam = itemHost.LookupParameter('Structural')
					defParameters(item, itemHost, obParam, 'LoadBearing')

				# Instance Part Parameters ===================================================================
				if item.get_Parameter(BuiltInParameter.DPART_SHAPE_MODIFIED).AsInteger() == 0: 	# ONLY if the part has not changed shape
					if item.LookupParameter('MaterialThickness') and item.get_Parameter(BuiltInParameter.DPART_LAYER_WIDTH): # we need both
						obParam = item.get_Parameter(BuiltInParameter.DPART_LAYER_WIDTH)
						defParameters(item, item, obParam, 'MaterialThickness')		# ! is NOT beeing exported to the IFC

				# Type specific Parameters ===================================================================
				if obType.LookupParameter('Fire Rating'):
					obParam = obType.LookupParameter('Fire Rating')
					defParameters(item, itemHost, obParam, 'FireRating')
				if obType.LookupParameter('Function'):
					obParam = obType.LookupParameter('Function')
					if obParam.AsInteger() == 1 or obParam.AsInteger() == 2 or obParam.AsInteger() == 3:
						strValue = 1												# Exterior, Foundation, Retaining are IsExternal
					else:
						strValue = 0												# Interior, Soffit, Core-Shaft are not IsExternal
					defParameters(item, itemHost, obParam, ['IsExternal',strValue])
				if obType.LookupParameter('IsExternal'):
					obParam = obType.LookupParameter('IsExternal')
					defParameters(item, itemHost, obParam, 'IsExternal')
				if obType.LookupParameter('Assembly Code'):
					obParam = obType.LookupParameter('Assembly Code')
					defParameters(item, itemHost, obParam, 'Assembly Code')
				if obType.LookupParameter('Assembly Description'):
					obParam = obType.LookupParameter('Assembly Description')
					defParameters(item, itemHost, obParam, 'Assembly Description')

				# Category specific Parameters ==============================================================
				if itemHost.Category.Id == ElementId(BuiltInCategory.OST_Roofs):
					strValue = True													# a Roof is 'always' External but lacks a Parameter
					defParameters(item, itemHost, None, ['IsExternal', strValue])

				# The exception of course ===================================================================
				if item.LookupParameter('IfcName'):
					strValue = obType.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
					strValue2 = item.get_Parameter(BuiltInParameter.DPART_MATERIAL_ID_PARAM).AsValueString()
					if item.get_Parameter(BuiltInParameter.DPART_LAYER_WIDTH):		# add the layer thickness to the name
						obParam = item.get_Parameter(BuiltInParameter.DPART_LAYER_WIDTH)
						ProjectUnits = obParam.DisplayUnitType
						strValue3 = ' - ' + str(UnitUtils.ConvertFromInternalUnits(obParam.AsDouble(),ProjectUnits))
					else:
						strValue3 = ''
					if setLayer.get(strValue + ':' + strValue2) is not None:		# add the layer function to the name
						strValue2 = strValue2 + strValue3 + ':' + str(setLayer.get(strValue + ':' + strValue2))
					strValue = strValue2 + ': ' + str(item.Id)						# Id of the Part
					defParameters(item, itemHost, obParam, ['IfcName',strValue])
				if item.LookupParameter('Reference'):
					obParam = item.LookupParameter('Reference')
					defParameters(item, itemHost, obParam, ['Reference',strValue2])
					
				lstCount.append(len(setTMP))
					
		if len(lstTMP)<2:
			lstOUT.append(["hmmm, not so smooth as it should",item,itemHost,obType])
#	except:
#		lstOUT.append(item)	

if len(lstOUT)<1:
	lstOUT.append("You did it ... smooth ;-)")

TransactionManager.Instance.TransactionTaskDone()

OUT = lstOUT, [
str(sum(lstCount)) + ' changed Parameters', 
str(len(lstCount)) + ' changed (hidden nested) Parts', 
str(len(setType)) + ' different original Types']
