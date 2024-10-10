# file_path = '~/Documents/GSTR1 SEP2024.xlsx'
import pandas as pd
import os

def load_correction_file(correction_file):
    """Loads the correction excel file if it exists, otherwise returns None."""
    if os.path.exists(correction_file):
        print("Correction file found, loading...")
        corrections_df = pd.read_excel(correction_file,dtype = "str")
        corrections_dict = dict(zip(corrections_df['Description'], corrections_df['HSN']))
        return corrections_dict
    return None

def validate_hsn_codes(item_summary_df, hsn_sac_df):
    """Validates HSN codes against the HSN_SAC dataframe and returns invalid entries."""
    invalid_hsn_rows = []
    # Convert HSN to strings and check if they are 4, 6, or 8 digits long
    for index, row in item_summary_df.iterrows():
        hsn_code = str(row['HSN'])
        
        # Check length
        if len(hsn_code) not in [4, 6, 8]:
            invalid_hsn_rows.append((index, hsn_code))
        else:
            # Check if HSN code exists in the HSN_SAC file
            if not hsn_sac_df['HSN Code'].astype(str).str.contains(hsn_code).any():
                invalid_hsn_rows.append((index, hsn_code))
    
    return invalid_hsn_rows

def generate_correction_file(invalid_hsn_rows, item_summary_df, correction_file):
    """Generates an excel file with invalid HSN codes for the user to correct."""
    print(f"Generating correction file: {correction_file}")
    correction_df = [] 

    for index, hsn in invalid_hsn_rows:
        row = item_summary_df.loc[index]
        correction_df.append({
            'old_hsn': hsn,
            'Description': row['Description'],
            'HSN': ""  # This is where the user will input the correct HSN code
        })
    
    correction_df = pd.DataFrame(correction_df,columns=['old_hsn', 'Description', 'HSN'])
    correction_df.to_excel(correction_file, index=False)
    print(f"Correction file created: {correction_file}")

def update_hsn_codes(item_summary_df, corrections_dict):
    """Updates the HSN codes in the item_summary dataframe using the corrections dict."""
    for index, row in item_summary_df.iterrows():
        description = row['Description']
        if description in corrections_dict:
            corrected_hsn = corrections_dict[description]
            if corrected_hsn and corrected_hsn != "nan" :
                item_summary_df.at[index, 'HSN'] = str(corrected_hsn)

def main(file_path):
    item_summary_file = file_path
    hsn_sac_file = 'HSN_SAC.xlsx'
    correction_file = 'correction_hsn.xlsx'
    if os.path.exists("itemSummary.xlsx") : os.remove("itemSummary.xlsx")
    if os.path.exists(correction_file) : os.remove(correction_file)

    # Load the item summary and HSN SAC data
    item_summary_df = pd.read_excel(item_summary_file,sheet_name="itemSummary",skiprows=3,dtype={"HSN":"str"})
    hsn_sac_df = pd.read_excel(hsn_sac_file,sheet_name="HSN",dtype={"HSN Code":"str"})

    while True:
        # Step 1: Check for an existing correction file
        print()
        corrections_dict = load_correction_file(correction_file)
        if corrections_dict:
            update_hsn_codes(item_summary_df, corrections_dict)
        
        # Step 2: Validate the HSN codes in the item summary
        invalid_hsn_rows = validate_hsn_codes(item_summary_df, hsn_sac_df)

        if not invalid_hsn_rows:
            print("All HSN codes are valid!")
            item_summary_df.to_excel("itemSummary.xlsx",index=False)
            break

        # Step 3: Generate correction file if invalid HSN codes are found
        generate_correction_file(invalid_hsn_rows, item_summary_df, correction_file)

        # Step 4: Prompt the user to correct the file and continue
        user_input = input("Please correct the HSN codes in the generated file. \nSave and close the correction file \nPress any key when done: ").strip().lower()

if __name__ == "__main__":
    main()
