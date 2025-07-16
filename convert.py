import json
import os

import pandas as pd


def find_json_files(directory='.'):
    """Find all JSON files in the directory and its subdirectories."""
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files


def json_to_dataframe(json_file):
    """
    Convert a JSON file to a pandas DataFrame with params expanded.
    Each paramName becomes its own column.
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create a list to hold the expanded records
    expanded_records = []

    # Process each product
    for product in data:
        # Create a base record with product details
        base_record = {
            'product_id': product.get('product_id', ''),
            'product_name': product.get('product_name', '')
        }

        # Extract params array
        params = product.get('params', [])

        # Create a dictionary for param values
        param_dict = {}
        for param in params:
            param_name = param.get('paramName', '')
            param_value = param.get('param', '')
            if param_name:
                param_dict[param_name] = param_value

        # Combine base record with param dict
        full_record = {**base_record, **param_dict}
        expanded_records.append(full_record)

    # Convert to DataFrame
    df = pd.DataFrame(expanded_records)

    return df


def create_excel_file(df, json_filename, output_dir='tmp'):
    """Create an Excel file with the same base name as the JSON file."""
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the base filename without extension
    base_name = os.path.splitext(os.path.basename(json_filename))[0]

    # Create output filename
    excel_filename = os.path.join(output_dir, f"{base_name}.xlsx")

    # Create Excel writer
    with pd.ExcelWriter(excel_filename, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)

        # Create pivot table if there are enough columns
        if len(df.columns) > 2:  # More than just product_id and product_name
            # Select columns for pivot
            value_columns = [col for col in df.columns if col not in ['product_id', 'product_name']]

            if value_columns:
                # Create pivot DataFrame
                try:
                    pivot_df = pd.pivot_table(
                        df,
                        index='product_name',
                        values=value_columns,
                        aggfunc='first'  # Since we're just showing the values
                    )
                    pivot_df.to_excel(writer, sheet_name='Pivot Table')
                except Exception as e:
                    print(f"  Warning: Could not create pivot table: {str(e)}")

    return excel_filename


def main():
    print("Finding JSON files...")
    json_files = find_json_files("data")

    if not json_files:
        print("No JSON files found in the repository.")
        return

    print(f"Found {len(json_files)} JSON files.")

    processed_files = []
    for json_file in json_files:
        try:
            print(f"Processing {json_file}...")
            df = json_to_dataframe(json_file)
            print(f"  Converted to DataFrame with shape {df.shape}")

            # Create Excel file
            excel_file = create_excel_file(df, json_file)
            processed_files.append(excel_file)
            print(f"  Created Excel file: {excel_file}")

        except Exception as e:
            print(f"  Error processing {json_file}: {str(e)}")

    if processed_files:
        print(f"\nSuccessfully created {len(processed_files)} Excel files in the 'tmp' directory:")
        for file in processed_files:
            print(f"  - {file}")
    else:
        print("No Excel files were created.")


if __name__ == "__main__":
    main()
