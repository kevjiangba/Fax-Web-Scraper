#-----------------------------------------------------------------------
# HIPAA Fax Web Scraper for Stroll Health Inc.
# Author: Kevin Jiang
# Reference: some code borrowed from http://www.hipaaspace.com/
#-----------------------------------------------------------------------

import urllib.parse
import urllib.request
import numpy as np
import math
from datascience import *
import sys
from xml.dom.minidom import parse, parseString

class HIPAASpaceWebService:

    SECURITY_TOKEN = "" # API Key withheld

    # URL to the HIPAASpace RESTful Web Services endpoint
    uri = "http://hipaaspace.com/api/{0}/{1}"

    # Verifies whether the HIPAA API query returned an error
    def checkError(self, result):
        if (result == ""):
            return "Error: no result was returned for the query"

        xmlDom = parseString(result)
        
        if (xmlDom.documentElement.tagName == "error"):
            return "Error '" + self.data(xmlDom.documentElement, "message") + "': " + self.data(xmlDom.documentElement, "details")
        
        return result

    # used to query the API 
    # Params: 
    # - queryType (String): what to query the HIPAA database, i.e. "NPI"
    # - key (String): value of the query, i.e. "1234567890" as an NPI of a facilitys
    # Returns:
    # - bytes object representing a facility with all its properties
    def queryItem(self, queryType, key):
        params = urllib.parse.urlencode({'q': key, 'rt': 'minxml', 'token': self.SECURITY_TOKEN})
        localUri = self.uri.replace('{0}', queryType).replace('{1}', 'getcode') + '?' + params
        req = urllib.request.Request(localUri)
        response = urllib.request.urlopen(req)
        strResponse = response.read()
        return self.checkError(strResponse)

    # generic function for getting a specific property of a facility, i.e. Organization Name, Fax Number
    # Params:
    # - resultItem (bytes): bytes object returned from queryItem.  Refers to a facility, i.e. Norcal Imaging and all its properties
    # - propertyName (String): gets the value of that property of the queried facility, i.e. "OrgName" for Organization Name
    # Returns:
    # - String representing the value of the query, i.e. "888-888-8888" for a fax number
    def getProperty(self, resultItem, propertyName):
        xmlDom = parseString(resultItem)
        resultItem = xmlDom.documentElement.childNodes[1]
        if resultItem.getElementsByTagName(propertyName):
            return resultItem.getElementsByTagName(propertyName)[0].firstChild.nodeValue
        else:
            #print(resultItem.toxml())  /* for debugging */
            return "None"

    def getFax(self, resultItem):
        faxLookup = self.getProperty(resultItem, "PracticeLocationAddressFaxNumber")
        if faxLookup == "None":
            return -1
        else:
            return int(removeExtra(faxLookup))

    def getOrgName(self, resultItem):
        return self.getProperty(resultItem, "OrgName")

    def getOtherOrgName(self, resultItem):
        return self.getProperty(resultItem, "OtherOrgName")

    def getState(self, resultItem):
        return self.getProperty(resultItem, "PracticeLocationAddressStateName")

# removes dashes and periods from fax numbers
# Params: 
# - string (String): i.e. "888-888-8888"
# Returns:
# - String, i.e. "8888888888"
def removeExtra(string):
    return string[:3] + string[4:7] + string[8:]

# Params:
# - count (int): i.e. 35 bananas out of 70 fruits
# - total (int): i.e. 70 fruits
# Returns:
# - float, i.e. 50.0
def convertToPercentage(count, total):
    return round(float(count)*100.0/float(total), 2)

# calculates string distance between 2 strings (number of edits needed to change s1 to s2), didn't use because ended up manually detecting whether 
# 2 names were the same since it was too hard to specify a cutoff for string distance.  This formula is known as the Leveshtein Distance
# Params: 
# - s1 (String): string1, i.e. "Hello"
# - s2 (String): string2, i.e. "Help"
# Returns:
# - int representing string distance, i.e. 2
def stringDistance(s1, s2):
    s1 = s1.lower()
    s2 = s2.lower()
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

# formats a print nicely with counts and percentages.  Statistic is a string of what you're trying to measure
# Params:
# - statistic (String): statistic being measured, i.e. "facilities with a fax number"
# - count (int): i.e. 35 bananas out of 70 fruits
# - total (int): i.e. 70 fruits
# Returns:
# None, but prints out String with relevant info
def printStatistic(statistic, count, total):
    print("Number of " + statistic + ": " + str(count) + "/" + str(total) + " (" + str(convertToPercentage(count, total)) + "%)")

# initiliaze a HIPAA API object, which is able to query
wsClient = HIPAASpaceWebService()

if len(sys.argv) != 2:
    print("Please specify a csv to be read in (with a space between python script name and csv name)")
else:
    csvToRead = sys.argv[1]

    # read in csv specified as command line argument
    facilities = Table.read_table(csvToRead)

    faxList = [0 for i in range(len(facilities['NPI']))] # 0 for no NPI in facilitiesList, -1 for no fax in HIPAA database
    CAlist = [] # records facilities in CA
    faxMatch = [] # records faxes that matched between spreadsheet and HIPAA website
    faxMatchCA = [] # records faxes that matched between spreadsheet and HIPAA website for facilities in CA
    CAtuples = [] # each element is a tuple containing (Organization Name, Other Organization Name, Spreadsheet Name, whether faxes match)
    nonCAtuples = []

    for index in range(len(facilities['NPI'])):
        NPI = facilities['NPI'][index]
        replaceFax = facilities['Fax'][index]

        # remove dots/dashes in all spreadsheet faxes
        if "." in replaceFax:
            facilities['Fax'][index] = removeExtra(replaceFax) 

        # only consider facilities in spreadsheet with valid NPI (10-digit)
        if len(NPI) == 10: 
            result = wsClient.queryItem("NPI", NPI)

            faxList[index] = wsClient.getFax(result) # retreived from HIPAA site
            sheetName = facilities['Name'][index]
            orgName = wsClient.getOrgName(result)
            otherOrgName = wsClient.getOtherOrgName(result)
            state = wsClient.getState(result)
            isFaxMatch = facilities['Fax'][index] != 'nan' and int(faxList[index]) == int(facilities['Fax'][index])

            #ended up not using string distance
            distance = min(stringDistance(orgName, sheetName)/len(sheetName), stringDistance(otherOrgName, sheetName)/len(sheetName))

            if state == "CA":
                CAlist.append(NPI)

                if isFaxMatch:
                    faxMatchCA.append(NPI)

                CAtuples.append((orgName, otherOrgName, sheetName, isFaxMatch))

            else:
                nonCAtuples.append((orgName, otherOrgName, sheetName, isFaxMatch))

            if isFaxMatch:
                faxMatch.append(NPI)

    # append retreived HIPAA faxes if needed for the future (I didn't use the new column, but can overwrite old csv if needed)
    facilities = facilities.with_column("retreivedFaxes", faxList)

    # used for manually comparing names between HIPAA site and spreadsheet
    # for _tuple in CAtuples: #switch CAtuples with nonCAtuples
        # print("OrgName: " + str(_tuple[0]))
        # print("OtherOrgName: " + str(_tuple[1]))
        # print("Spreadsheet name: " + str(_tuple[2]))
        # print("Faxes Match? " + str(_tuple[3]))
        # print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")

    numValidNPI = np.count_nonzero(faxList)
    numMatchingFaxes = len(faxMatch)
    numCA = len(CAlist)
    numNonCA = numValidNPI - numCA
    numMatchingFaxesCA = len(faxMatchCA)
    numMatchingFaxesNonCA = numMatchingFaxes - numMatchingFaxesCA
    numCloseNameCA = 50 #hand-counted 
    numCloseNameNonCA = 19 #hand-counted
    numNotCloseNameCA = numCA - numCloseNameCA
    numNotCloseNameNonCA = numNonCA - numCloseNameNonCA
    numCloseNameRightFaxCA = 29 #hand-counted
    numCloseNameRightFaxNonCA = 6 #hand-counted
    numCloseNameWrongFaxCA = numCloseNameCA - numCloseNameRightFaxCA
    numCloseNameWrongFaxNonCA = numCloseNameNonCA - numCloseNameRightFaxNonCA

    printStatistic("facilities in spreadsheet with valid NPI", numValidNPI, len(faxList))
    printStatistic("matching faxes", numMatchingFaxes, numValidNPI)
    print("-=-=-=-=-=-=-=-=- CA -=-=-=-=-=-=-=-=-=-=-=")
    printStatistic("facilities", numCA, numValidNPI)
    printStatistic("matching faxes", numMatchingFaxesCA, numCA)
    printStatistic("facilities appearing to have same name", numCloseNameCA, numCA)
    printStatistic("facilities appearing to not have the same name", numNotCloseNameCA, numCA) #redundant
    printStatistic("facilities appearing to have same name with same fax", numCloseNameRightFaxCA, numCloseNameCA)
    printStatistic("facilities appearing to have same name with different fax", numCloseNameWrongFaxCA, numCloseNameCA) #redundant
    print("-=-=-=-=-=-=-=- NOT IN CA -=-=-=-=-=-=-=-=-")
    printStatistic("facilities", numNonCA, numValidNPI)
    printStatistic("matching faxes", numMatchingFaxesNonCA, numNonCA)
    printStatistic("facilities appearing to have same name", numCloseNameNonCA, numNonCA)
    printStatistic("facilities appearing to not have the same name", numNotCloseNameNonCA, numNonCA) #redundant
    printStatistic("facilities appearing to have same name with same fax", numCloseNameRightFaxNonCA, numCloseNameNonCA)
    printStatistic("facilities appearing to have same name with different fax", numCloseNameWrongFaxNonCA, numCloseNameNonCA) #redundant
