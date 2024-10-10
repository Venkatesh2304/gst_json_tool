import datetime
import os
import pandas as pd
import json
import hsn_validator 

def build_b2b_invoices(df):
    df["Invoice date"] = pd.to_datetime(df["Invoice date"])  # Ensure date is in correct format

    # Group by GSTIN/UIN of Recipient (ctin)
    grouped_by_ctin = df.groupby('GSTIN/UIN of Recipient')

    b2b_invoices = []

    # Loop through each GSTIN (ctin)
    for ctin, group_by_ctin in grouped_by_ctin:
        invoices = []

        # Now, group by Invoice Number within each ctin group
        grouped_by_invoice = group_by_ctin.groupby('Invoice Number')

        # Loop through each invoice within the ctin group
        for inum, group_by_invoice in grouped_by_invoice:
            invoice_items = []

            for _, row in group_by_invoice.iterrows():
                # Extract the required details from the row
                serial_number = len(invoice_items) + 1  # Increment serial number for each item
                tax_rate = row['Rate']  # Convert to native float
                txval = row['Taxable Value']  # Convert to native float
                camt = txval * (tax_rate / 2) / 100  # CGST split
                samt = txval * (tax_rate / 2) / 100  # SGST split

                # Create the item entry
                item = {
                    "num": serial_number,
                    "itm_det": {
                        "txval": round(txval, 2),
                        "rt": round(tax_rate, 1),
                        "iamt": 0,  # Assuming 0 for IGST
                        "camt": round(camt, 2),  # CGST
                        "samt": round(samt, 2),  # SGST
                        "csamt": round(row.get('Cess Amount', 0), 2)  # Cess amount, default to 0
                    }
                }
                invoice_items.append(item)

            # Build the invoice details
            invoice = {
                "inum": str(inum),  # Invoice number
                "val": round(float(group_by_invoice.iloc[0]['Invoice Value']), 2),  # Invoice value
                "idt": group_by_invoice.iloc[0]['Invoice date'].strftime('%Y-%m-%d'),
                "pos": str(group_by_invoice.iloc[0]['Place Of Supply']),
                "rchrg": group_by_invoice.iloc[0]['Reverse Charge'],
                "inv_typ":"R",
                "itms": invoice_items
            }

            invoices.append(invoice)

        # Build the final structure for each GSTIN (ctin)
        ctin_entry = {
            "ctin": str(ctin),
            "inv": invoices  # List of invoices for this GSTIN
        }

        b2b_invoices.append(ctin_entry)

    # Convert the entire B2B invoices list to JSON
    return {"b2b" : b2b_invoices}

def build_cdnr_invoices(df):
    df["Note Date"] = pd.to_datetime(df["Note Date"])  # Ensure the date is in the correct format

    # Group by GSTIN/UIN of Recipient (ctin)
    grouped_by_ctin = df.groupby('GSTIN/UIN of Recipient')

    cdnr_invoices = []

    # Loop through each GSTIN (ctin)
    for ctin, group_by_ctin in grouped_by_ctin:
        notes = []

        # Now, group by Note Number within each ctin group
        grouped_by_note = group_by_ctin.groupby('Note Number')

        # Loop through each note within the ctin group
        for note_num, group_by_note in grouped_by_note:
            note_items = []

            for _, row in group_by_note.iterrows():
                # Extract the required details from the row
                serial_number = len(note_items) + 1  # Increment serial number for each item
                tax_rate = row['Rate']  # Tax rate
                txval = row['Taxable Value']  # Taxable value
                camt = txval * (tax_rate / 2) / 100  # CGST split
                samt = txval * (tax_rate / 2) / 100  # SGST split

                # Create the item entry
                item = {
                    "num": serial_number,
                    "itm_det": {
                        "txval": round(txval, 2),
                        "rt": round(tax_rate, 1),
                        "iamt": 0,  # Assuming IGST is 0
                        "camt": round(camt, 2),  # CGST
                        "samt": round(samt, 2),  # SGST
                        "csamt": round(row.get('Cess Amount', 0), 2)  # Cess amount, default to 0
                    }
                }
                note_items.append(item)

            # Build the note details
            note = {
                "nt_num": str(note_num),  # Note number
                "ntty": "C",  # Note type is assumed to be "Credit Note" (adjust accordingly)
                "val": round(float(group_by_note.iloc[0]['Note Value']), 2),  # Note value
                "nt_dt": group_by_note.iloc[0]['Note Date'].strftime('%Y-%m-%d'),
                "pos": str(group_by_note.iloc[0]['Place Of Supply']),  # Place of supply
                "rchrg": group_by_note.iloc[0]['Reverse Charge'],  # Reverse charge
                "inv_typ": "R",  # Assuming invoice type is "Regular"
                "itms": note_items  # The list of items within this note
            }

            notes.append(note)

        # Build the final structure for each GSTIN (ctin)
        ctin_entry = {
            "ctin": str(ctin),
            "nt": notes  # List of notes for this GSTIN
        }

        cdnr_invoices.append(ctin_entry)

    # Convert the entire CDNR invoices list to JSON
    return  {"cdnr" : cdnr_invoices}

def build_b2cs_invoices(df):
    # Ensure any necessary columns are in correct format
    df["Taxable Value"] = df["Taxable Value"].astype(float)
    df = df.groupby(["Rate","Type"]).aggregate({"Taxable Value" : "sum","Cess Amount" : "sum"}).reset_index()

    b2cs_invoices = []

    # Loop through each row in the dataframe
    for _, row in df.iterrows():
        tax_rate = row['Rate']
        txval = row['Taxable Value']
        camt = txval * (tax_rate / 2) / 100  # CGST split
        samt = txval * (tax_rate / 2) / 100  # SGST split

        # Build the b2cs invoice structure for each row
        b2cs_entry = {
            "txval": round(txval, 2),
            "rt": round(tax_rate, 1),
            "iamt": 0,  # Assuming IGST is 0
            "camt": round(camt, 2),  # CGST
            "samt": round(samt, 2),  # SGST
            "csamt": round(row.get('Cess Amount', 0), 2),  # Cess amount, default to 0
            "sply_ty": "INTRA", # if row['Place Of Supply'] in ["INTRA", "33-Tamil Nadu"] else "INTER",  # Assuming '33' is INTRA
            "typ": row['Type'],  # Type of supply, e.g., "OE" (assumed based on example)
            "pos": "33", #str(row['Place Of Supply'])  # Place of supply
        }

        # Append each entry to the final list
        b2cs_invoices.append(b2cs_entry)

    # Convert the entire B2CS invoices list to JSON
    return  {"b2cs" : b2cs_invoices}

def build_hsn_data(df):
    hsn_data = []
    grouped_hsn = df.groupby('HSN').agg({
        'UQC': 'first',  # Unit Quantity Code remains the same
        'Total Quantity': 'sum',  # Sum of all quantities for the same HSN
        'Taxable Value': 'sum',  # Sum of taxable values
        'Rate': 'first',  # Assume same tax rate for all items with the same HSN
        'Cess Amount': 'sum',  # Sum of cess amounts
        'Integrated Tax Amount': 'sum',  # Sum of IGST
        'Central Tax Amount': 'sum',  # Sum of CGST
        'State/UT Tax Amount': 'sum'  # Sum of SGST
    }).reset_index()

    # Loop through each row in the dataframe
    for index, row in grouped_hsn.iterrows():
        serial_number = index + 1  # Serial number starts from 1
        hsn = str(row['HSN']).split(".")[0]
        uqc = row['UQC']
        qty = row['Total Quantity']
        txval = row['Taxable Value']
        rt = row['Rate']

        # Calculate tax components
        camt = txval * (rt / 2) / 100  # CGST split
        samt = txval * (rt / 2) / 100  # SGST split

        # Build the HSN entry structure
        hsn_entry = {
            "num": serial_number,
            "hsn_sc": hsn,
            "uqc": uqc, #warning : is uqc - nos (but its showing others)
            "qty": qty,
            "txval": round(txval, 2),
            "rt": round(rt, 1),
            "iamt": 0,  # Assuming IGST is 0 for now
            "camt": round(camt, 2),  # CGST
            "samt": round(samt, 2),  # SGST
            "csamt": round(row.get('Cess Amount', 0), 2)  # Cess amount, default to 0
        }

        hsn_data.append(hsn_entry)

    # Convert the entire HSN data list to JSON
    return { "hsn" : {"data":hsn_data } }

def build_docs_data(df):
    # Initialize document structure
    doc_data = []

    # Define mappings for document numbers based on Nature of Document
    doc_type_mapping = {
        "Invoices for outward supply": 1,
        "Credit Note": 5
    }

    # Group the data by Nature of Document
    grouped_docs = df.groupby('Nature of Document')

    # Loop through each document type
    for doc_type, group in grouped_docs:
        # Get the document number based on the document type
        doc_num = doc_type_mapping.get(doc_type, 0)

        docs = []

        # Loop through each row in the group for the current document type
        for index, row in group.reset_index().iterrows():
            serial_number = index + 1  # Serial number starts from 1
            from_sr = row['Sr. No. From'] if pd.notnull(row['Sr. No. From']) else None
            to_sr = row['Sr. No. To'] if pd.notnull(row['Sr. No. To']) else None
            totnum = row['Total Number']
            cancel = row['Cancelled']
            net_issue = totnum - cancel

            # Build the document details for the current row
            doc_entry = {
                "num": serial_number,
                "to": str(to_sr).split(".")[0] if to_sr else "",
                "from": str(from_sr).split(".")[0] if from_sr else "",
                "totnum": totnum,
                "cancel": cancel,
                "net_issue": net_issue
            }

            docs.append(doc_entry)

        # Build the doc_det entry for the current document type
        doc_det_entry = {
            "doc_num": doc_num,
            "doc_typ": doc_type,
            "docs": docs
        }

        doc_data.append(doc_det_entry)

    # Convert the entire document data list to JSON
    return { "docs" : doc_data }


os.makedirs("data",exist_ok=True)
os.makedirs("json",exist_ok=True)

month = int(input("Enter Month : ").strip())
year = int(input("Enter Month : ").strip())
period = datetime.date(year,month,1).strftime("%b%Y").upper()
file_path = f"data/GSTR1_{period}.xlsx"

print(f"Reading {file_path}")
if not os.path.exists(file_path) : 
    print("ERROR: File doesnt exists")
    input("Press any key to exit : ")
    exit(1)

hsn_validator.main(file_path)

sheets = [("b2b,sez,de",build_b2b_invoices),("b2cs",build_b2cs_invoices),("cdnr",build_cdnr_invoices),
          ("docs",build_docs_data)]

data = {}
for sheet,fn in sheets : 
    data |= fn( pd.read_excel(file_path, sheet_name=sheet , skiprows=3) )

data |= build_hsn_data(pd.read_excel("itemSummary.xlsx",dtype = {"HSN" : "str"}))

with open(f'json/{period}.json', 'w+') as json_file:
    json_file.write(json.dumps(data,indent=4))

print("JSON has been created successfully!")
