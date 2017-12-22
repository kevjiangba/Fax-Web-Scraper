# Fax-Web-Scraper
Python web scraper to query fax numbers from www.HIPAA.com.  The tool searches through the HIPAASpace API to determine if it is a reliable source for data on healthcare providers, medical organizations, and payers.  This individual project was assigned to me during my time at Stroll Health Inc. 

## How it works
The script takes in a CSV file, which has manually entered data on select healthcare facilities' fax numbers, names, and NPIs (National Provider Identifier) that we assume to be correct, and compares its contents with data received from the HIPAASpace server.

For each facility with a valid NPI in the CSV file, I query the HIPAASpace database with that NPI and retrieve a name and fax number for that facility.  I compare that information with the information listed on the CSV file and use Leveshtein string matching to determine how similar the facility names are and if the fax numbers match.  Since we take the CSV data as correct, we accepted the HIPPASpace data if its similarity to our CSV data passed a certain threshold.  

