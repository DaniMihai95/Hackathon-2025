import pandas as pd
import json


file_paths = {
    "prodgroup": "./existing_data/hackaton_prodgroup.csv",
    "products": "./existing_data/hackaton_products.csv",
    "specs_raw": "./existing_data/hackaton_specs_raw.csv",
    "specs": "./existing_data/hackaton_specs.csv"
}


def extract_product_data(sku_or_name, file_paths, is_sku: bool = False):
    """
    Extracts all related product data given a SKU or product name (or lists of them).
    """

    # --- Load CSV files ---
    df_prodgroup = pd.read_csv(file_paths["prodgroup"], delimiter=";")
    df_products = pd.read_csv(file_paths["products"], delimiter=";")
    df_specs_raw = pd.read_csv(file_paths["specs_raw"], delimiter=";")
    df_specs = pd.read_csv(file_paths["specs"], delimiter=";")

    # --- Convert all 'sku' columns to string to avoid merge type conflicts ---
    for df in [df_products, df_prodgroup, df_specs_raw, df_specs]:
        if "sku" in df.columns:
            df["sku"] = df["sku"].astype(str).str.strip()

    # --- Convert single string input to list for uniform handling ---
    if isinstance(sku_or_name, str):
        sku_or_name = [sku_or_name]

    # --- Filter products by SKU or product name ---
    if is_sku:
        filtered_products = df_products[df_products["sku"].isin(sku_or_name)]
    else:
        filtered_products = df_products[df_products["productName"].isin(sku_or_name)]

    # If no matches, return an empty DataFrame
    if filtered_products.empty:
        return pd.DataFrame(columns=[
            "sku", "productName", "brandId", "brandName", "mainGroup", "mainGroupName",
            "subGroup", "subGroupName", "mainSpec", "spec", "value", "trailer"
        ])

    # --- Merge product data with prodgroup info ---
    merged_data = filtered_products.merge(
        df_prodgroup,
        on=["brandId", "mainGroup", "subGroup"],
        how="left"
    )

    # --- Merge with specs_raw ---
    merged_data = merged_data.merge(
        df_specs_raw,
        on="sku",  # <-- Now both sides are string
        how="left"
    )

    # --- Merge with specs (for trailer) ---
    merged_data = merged_data.merge(
        df_specs[["sku", "spec", "value", "trailer"]],
        on=["sku", "spec", "value"],
        how="left"
    )

    # Optional: Reorder columns for readability
    desired_order = [
        "sku", "productName", "brandId", "brandName", "mainGroup", "mainGroupName",
        "subGroup", "subGroupName", "mainSpec", "spec", "value", "trailer"
    ]
    final_cols = [col for col in desired_order if col in merged_data.columns]
    merged_data = merged_data[final_cols]

    return merged_data

def jsonify_product_data(df):
    """
    Converts the product DataFrame to a JSON string (list of row-objects),
    suitable for DB insertion or JSON file storage.
    """
    return df.to_json(orient="records", indent=2)


def nest_specs_by_sku(df):
    """
    Given the DataFrame that has multiple rows per product (one per spec),
    group them so that each product is a single dictionary with a nested 'specs' list.

    Returns a list of dictionaries, one per product.
    """

    # Columns that are product-level (these won't repeat once we nest specs)
    product_level_cols = [
        "sku", "productName", "brandId", "brandName",
        "mainGroup", "mainGroupName", "subGroup", "subGroupName"
    ]

    # Columns that describe each spec
    spec_level_cols = ["mainSpec", "spec", "value", "trailer"]

    # Group by the product-level columns
    grouped = df.groupby(product_level_cols, dropna=False)

    result = []
    for group_keys, group_df in grouped:
        # group_keys is a tuple of values for the columns in product_level_cols
        # Build a dict for the product-level info
        product_dict = dict(zip(product_level_cols, group_keys))

        # Build a list of specs for this product
        specs_list = []
        for _, row in group_df.iterrows():
            spec_dict = {col: row[col] for col in spec_level_cols if col in row}
            specs_list.append(spec_dict)

        # Attach the list of specs to the product dict
        product_dict["specs"] = specs_list

        result.append(product_dict)

    return result

def convert_numpy_types_to_python(data):
    """
    Recursively convert NumPy types (e.g., np.int64, np.float32)
    to native Python int, float, etc., so json.dumps works.
    """
    import numpy as np

    if isinstance(data, dict):
        # Convert each value in the dict
        return {k: convert_numpy_types_to_python(v) for k, v in data.items()}

    elif isinstance(data, list):
        # Convert each item in the list
        return [convert_numpy_types_to_python(item) for item in data]

    elif isinstance(data, np.integer):
        return int(data)

    elif isinstance(data, np.floating):
        return float(data)

    elif isinstance(data, np.bool_):
        return bool(data)

    elif data is np.nan:
        # Convert NaN to None
        return None

    else:
        return data


def jsonify_nested_products(nested_products):
    """
    Convert the nested list of product dictionaries into a JSON string.
    Ensures that NumPy types are converted to native Python types first.
    """
    import json

    # Convert NumPy dtypes recursively
    clean_data = convert_numpy_types_to_python(nested_products)
    return json.dumps(clean_data, indent=2)



if __name__ == "__main__":

    # # Search by SKU
    # extracted_df_sku = extract_product_data("1110528", file_paths, is_sku=True)
    # print("Extract by SKU:")
    # print(extracted_df_sku)

    # Search by productName
    extracted_df_name = extract_product_data("Gigabyte EAGLE GeForce RTX 4060 Ti OC ICE NVIDIA 8 GB GDDR6", file_paths, is_sku=False)
    print("\nExtract by productName:")
    # print(jsonify_product_data(extracted_df_name))

    # 2) Convert it to a nested structure: one product dict, plus a list of all its specs
    nested = nest_specs_by_sku(extracted_df_name)

    # 3) Convert that nested structure to JSON
    json_string = jsonify_nested_products(nested)

    # print(json_string)
    data = json.loads(json_string)

    from pprint import pprint
    pprint(data[0])
