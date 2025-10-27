def count_duplicate_hashes(file_path):
    """
    Count duplicate hash codes in the link mapping file, excluding entries without valid hash codes.
    
    Args:
        file_path (str): Path to the link mapping file
        
    Returns:
        tuple: (duplicate_count, valid_hash_count, total_entries)
    """
    hash_counts = {}
    valid_hash_entries = 0
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
                
            # Parse the line to extract the hash code
            # Format: UNLINKED ; filename ; hash_code
            parts = line.split(' ; ')
            if len(parts) >= 3:
                hash_code = parts[2].strip()
                
                # Check if hash code is valid (not empty and not just whitespace)
                if hash_code and hash_code != "unknown":
                    valid_hash_entries += 1
                    if hash_code in hash_counts:
                        hash_counts[hash_code] += 1
                    else:
                        hash_counts[hash_code] = 1
    
    # Count duplicates (hashes that appear more than once)
    duplicate_count = sum(1 for count in hash_counts.values() if count > 1)
    
    # Count how many total duplicate instances there are
    duplicate_instances = sum(count - 1 for count in hash_counts.values() if count > 1)
    
    return duplicate_count, duplicate_instances, valid_hash_entries, len(hash_counts)


if __name__ == "__main__":
    file_path = "MERGED14-25/link_mapping.txt"
    
    try:
        duplicate_hashes, duplicate_instances, valid_entries, unique_hashes = count_duplicate_hashes(file_path)
        print(f"Analysis of {file_path}:")
        print(f"  Valid hash entries: {valid_entries}")
        print(f"  Unique hash codes: {unique_hashes}")
        print(f"  Hash codes with duplicates: {duplicate_hashes}")
        print(f"  Duplicate instances (total): {duplicate_instances}")
        
        if duplicate_hashes > 0:
            print(f"\nThere are {duplicate_hashes} hash codes that appear more than once.")
            print(f"This represents {duplicate_instances} duplicate file instances.")
        else:
            print("\nNo duplicate hash codes found.")
            
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"Error processing file: {e}")