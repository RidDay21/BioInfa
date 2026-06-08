#!/usr/bin/env bash
# =============================================================================
# parse_flagstat.sh — extracts % mapped reads from samtools flagstat output
#
# Usage:
#   bash parse_flagstat.sh <flagstat_file>
#
# Output:
#   Prints the mapped percentage as a plain number, e.g.: 99.83
#
# Example flagstat line that is parsed:
#   1097662 + 0 mapped (99.83% : N/A)
# =============================================================================

FLAGSTAT_FILE="${1:?Usage: parse_flagstat.sh <flagstat_file>}"

if [[ ! -f "$FLAGSTAT_FILE" ]]; then
    echo "ERROR: File not found: $FLAGSTAT_FILE" >&2
    exit 1
fi

# Extract the percentage from the "mapped" line
# Line format:  <N> + <N> mapped (<PCT>% : N/A)
PCT=$(grep -m1 " mapped (" "$FLAGSTAT_FILE" \
      | grep -oP '\(\K[0-9]+\.[0-9]+(?=%)' )

# If no decimal point (e.g. "100%"), try integer match
if [[ -z "$PCT" ]]; then
    PCT=$(grep -m1 " mapped (" "$FLAGSTAT_FILE" \
          | grep -oP '\(\K[0-9]+(?=%)' )
fi

if [[ -z "$PCT" ]]; then
    echo "ERROR: Could not parse mapped percentage from $FLAGSTAT_FILE" >&2
    exit 1
fi

echo "$PCT"
