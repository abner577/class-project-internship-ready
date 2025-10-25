from data.load_data import load_water_data
from data.clean_data import clean_zscore
from utils.db_connection import get_collection

def main():
    csv_path = "data/2021-dec16.csv"  

    print("Loading dataset...")
    df = load_water_data(csv_path)
    print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

    print("Cleaning data (z-score)...")
    cleaned_df, stats = clean_zscore(df)
    print(f"Stats: {stats}")

    print("Inserting cleaned data into mongomock...")
    coll = get_collection()
    coll.delete_many({})
    coll.insert_many(cleaned_df.to_dict("records"))
    print(f"Inserted {coll.count_documents({})} records.")

    # Verify one example document
    example = coll.find_one({})
    print("Example record:", example)

    # Optionally save cleaned CSV
    cleaned_df.to_csv("data/cleaned_output.csv", index=False)
    print("Saved cleaned CSV to data/cleaned_output.csv")

if __name__ == "__main__":
    main()