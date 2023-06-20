import json
import os
import requests
from bs4 import BeautifulSoup

from constants import TEMP_DIR, UNRESOLVED_DIR

class UnexpectedWebpageFormatError(Exception):
    def __init__(self, reason=None):
        message = '[ERROR] Unexpected webpage format'
        if reason is not None:
            message += f': {reason}'
        super().__init__(message)

if not os.path.isdir(TEMP_DIR):
    os.mkdir(TEMP_DIR)

fdaUrl = 'https://www.fda.gov/medical-devices/precision-medicine/table-pharmacogenetic-associations'
fdaFileName = 'fda_content.html'
fdaFilePath = os.path.join(TEMP_DIR, fdaFileName)
if not os.path.isfile(fdaFilePath):
    with open(fdaFilePath, 'w') as fdaFile:
        fdaUrl 
        fdaFile.write(requests.get(fdaUrl).text)

with open(fdaFilePath, 'r') as fdaFile:
    fdaContent = fdaFile.read()

soup = BeautifulSoup(fdaContent, 'html.parser')

def getSectionLink(soup, id):
    sectionLink = soup.find('a', id=id)
    if sectionLink is None:
        raise UnexpectedWebpageFormatError(f'no link with id {id}')
    return sectionLink

def getTable(soup, id):
    sectionLink = getSectionLink(soup, id)
    table = sectionLink.find_next('table')
    if table is None:
        raise UnexpectedWebpageFormatError(f'no table after link with id {id}')
    return table

def getCpicDrugs():
    cpicUrl = 'https://api.cpicpgx.org/v1/recommendation'
    params = { 'select': 'drug(name)' }
    cpicRecommendations = requests.get(cpicUrl, params=params).json()
    cpicDrugs = set()
    for recommendation in cpicRecommendations:
        cpicDrugs.add(recommendation['drug']['name'])
    return cpicDrugs

cpicDrugs = getCpicDrugs()
fdaAnnotations = []
includedSections = { 'section1': 'Section 1', 'section2': 'Section 2' }
for sectionId, sectionName in includedSections.items():
    sectionTable = getTable(soup, sectionId)
    sectionSourceName = f'Table of Pharmacogenetic Associations ({sectionName})'
    sectionSourceUrl = f"{fdaUrl}#{getSectionLink(soup, sectionId)['name']}"
    for row in sectionTable.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) == 0:
            continue
        if len(cells) != 4:
            raise UnexpectedWebpageFormatError('expecting 4 table cells')
        medication = cells[0].text.lower()
        if medication in cpicDrugs:
            continue
        gene = cells[1].text
        phenotype = cells[2].text
        description = cells[3].text
        # TODO: ID important? (Also for resolve script!)
        # TODO: Multiple genes
        # TODO: Multiple phenotypes
        # TODO: Get RxNorm
        fdaAnnotations.append({
            'id': 1,
            'version': 1,
            'drugid': 'RxNorm:TODO',
            'drug': {
                'name': medication
            },
            'phenotypes': {
                gene: phenotype
            },
            'guideline': {
                'name': sectionSourceName,
                'url': sectionSourceUrl
            },
            'implications': {
                gene: description
            },
            'drugrecommendation': 'Potentially included in implication'
        })

with open(os.path.join(UNRESOLVED_DIR, 'FDA.json'), 'w') as unresolvedFile:
    json.dump(fdaAnnotations, unresolvedFile, indent=4)
