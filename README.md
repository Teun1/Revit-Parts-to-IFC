# Revit-Parts-to-IFC
https://github.com/Autodesk/revit-ifc/issues/120#issuecomment-529487926

I did some testing on exporting Parts to IFC and had multiple problems with the properties.
A Part:
    1 - has a Common Property Value but it is not related to the Host:
        IsExternal.
    2 - has Common Properties but no value - so also not related to the Host:
        Fire Rating,
        Load Bearing.
    3 - doesn't have the following Properties but the Host has:
        Type Name,
        Uniformat Classification,
        Reference (original Family and Type in Revit),
        Thickness (Revit knows if the geometry is changed).
    4 - has it's own Parameters based on beiing a Part (this makes sense):
        Name,
        Type.
    5 - has a different IFC entity from the host? > only mapping by Category?

So I build a Dynamo Python script to get information from the original and write it back to the parts.

I would love to get some feedback about the IfcName and IfcDescription:

    IfcName = Material name - Thickness : Layer Function
    ( in this way I still get my Thickness in the IFC )
    IfcDescription = (Linked Part - ) (Changed Part - ) Original = original Type
    ( in this way I can trace some exceptions in Revit or IFC)

But perhaps there are also some improvements in the Python script.
Or perhaps some thoughts on adding more information from the original to the Parts.

https://creativecommons.org/licenses/by-nc-sa/3.0/deed.nl - http://www.internetrechten.nl/disclaimer/
