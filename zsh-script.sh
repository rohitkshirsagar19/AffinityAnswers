#!/bin/bash

# Script to extract Scheme Name and Asset Value from AMFI NAV data

# and save as JSON file

# Define file paths

URL="https://www.amfiindia.com/spages/NAVAll.txt"

OUTPUT_FILE="amfi_nav_data.json"

TMP_FILE="amfi_nav_data_raw.txt"

echo "Downloading AMFI NAV data..."

curl -s "$URL" > "$TMP_FILE"

if [ $? -ne 0 ]; then

echo "Error downloading data. Please check your internet connection."

exit 1

fi

# Check if file was properly downloaded

if [ ! -s "$TMP_FILE" ]; then

echo "Error: Downloaded file is empty. Please check URL and try again."

exit 1

fi

echo "Sample of downloaded data:"

head -5 "$TMP_FILE"

echo "Extracting Scheme Name and Asset Value..."

# Start JSON array

echo "[" > "$OUTPUT_FILE"

# Create a temporary file for the JSON content

TMP_JSON="temp_json_content.txt"

> "$TMP_JSON"

# Process the file with a more robust approach

awk '

BEGIN {

 FS = ";";

 count = 0;

}

{

 # Skip header lines and process lines with data

 if (NF >= 2) {

 # Try to find a numeric field (NAV)

 for (i = 1; i <= NF; i++) {

 if ($i ~ /^[0-9]+(\.[0-9]+)?$/) {

 # Found a potential NAV value

 # The scheme name is usually the field before NAV

 if (i > 1) {

 scheme_name = $(i-1);

 nav = $i;

 gsub(/^[ \t]+|[ \t]+$/, "", scheme_name); # Trim whitespace

 gsub(/"/, "\\\"", scheme_name); # Escape double quotes

 # Print as JSON object

 if (count > 0) {

 print "," >> "temp_json_content.txt";

 }

 print " {" >> "temp_json_content.txt";

 print " \"scheme_name\": \"" scheme_name "\"," >> "temp_json_content.txt";

 print " \"nav\": " nav >> "temp_json_content.txt";

 print " }" >> "temp_json_content.txt";

 count++;

 break;

 }

 }

 }

 }

}

END {

 print "Found " count " entries.";

}' "$TMP_FILE"

# Check if any data was extracted

if [ -s "$TMP_JSON" ]; then

# Append the JSON content to the output file

cat "$TMP_JSON" >> "$OUTPUT_FILE"

else

echo "Warning: No valid data found in the downloaded file."

fi

# End JSON array

echo -e "\n]" >> "$OUTPUT_FILE"

# Count the number of entries extracted

entry_count=$(grep -c "scheme_name" "$OUTPUT_FILE")

echo "Extraction complete! $entry_count entries saved to $OUTPUT_FILE"

echo "First few entries:"

head -20 "$OUTPUT_FILE" | tail -6

echo "..."

echo "Cleaning up temporary files..."

rm "$TMP_FILE" "$TMP_JSON" 2>/dev/null

echo "Done!"
