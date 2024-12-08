#!/bin/bash

# Header
echo "Date,Description,Amount,Type,Category,Balance"

# Generate 100 transactions
START_DATE="2024-01-01"
BALANCE=10000.00

# Common merchants
MERCHANTS=(
    "TRADER_JOES" 
    "AMAZON" 
    "SPOTIFY" 
    "NETFLIX" 
    "SHELL_GAS" 
    "STARBUCKS" 
    "TARGET" 
    "WHOLE_FOODS"
    "UBER" 
    "LYFT"
)

# Common transaction types
TYPES=("debit" "credit" "transfer" "withdrawal" "deposit")

# Categories
CATEGORIES=(
    "Groceries" 
    "Entertainment" 
    "Transportation" 
    "Dining" 
    "Utilities" 
    "Shopping"
)

mkdir -p data

for i in {1..100}; do
    # Generate random date within 2024
    DAYS_TO_ADD=$((RANDOM % 365))
    TRANS_DATE=$(date -v+"$DAYS_TO_ADD"d -j -f "%Y-%m-%d" "$START_DATE" "+%Y-%m-%d" 2>/dev/null || 
                 date -d "$START_DATE + $DAYS_TO_ADD days" "+%Y-%m-%d")
    
    # Random merchant
    MERCHANT=${MERCHANTS[$((RANDOM % ${#MERCHANTS[@]}))]}
    
    # Random amount (between -200 and 500)
    AMOUNT=$(printf "%.2f" $(echo "scale=2; (($RANDOM % 70000) - 20000) / 100" | bc))
    
    # Transaction type
    TYPE=${TYPES[$((RANDOM % ${#TYPES[@]}))]}
    
    # Category
    CATEGORY=${CATEGORIES[$((RANDOM % ${#CATEGORIES[@]}))]}
    
    # Update balance
    BALANCE=$(printf "%.2f" $(echo "scale=2; $BALANCE + $AMOUNT" | bc))
    
    echo "$TRANS_DATE,$MERCHANT,$AMOUNT,$TYPE,$CATEGORY,$BALANCE"
done | sort -t, -k1 |tee data/transactions.csv
